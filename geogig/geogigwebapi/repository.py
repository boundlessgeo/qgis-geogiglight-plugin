# -*- coding: utf-8 -*-

"""
***************************************************************************
    repository.py
    ---------------------
    Date                 : March 2016
    Copyright            : (C) 2016 Boundless, http://boundlessgeo.com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import re
import requests
from commit import Commit
from diff import Diffentry
from commitish import Commitish
import os
from geogig.tools.utils import userFolder, resourceFile
import json
from geogig.geogigwebapi.commit import NULL_ID
from datetime import datetime
import time
from geogig.gui.executor import execute
import shutil
from qgis.core import *
import sqlite3
from PyQt4.QtCore import pyqtSignal, QEventLoop, Qt, QTimer, QObject
from PyQt4.QtGui import QApplication
from PyQt4.Qt import QCursor
from geogig.tools.layertracking import isRepoLayer
import xml.etree.ElementTree as ET
from geogig.tools.layers import formatSource, namesFromLayer

class GeoGigException(Exception):
    pass

class MergeConflictsException(GeoGigException):
    pass

def _resolveref(ref):
    '''
    Tries to resolve the pased object into a string representing a commit reference
    (a SHA-1, branch name, or something like HEAD~1)
    This should be called by all commands using references, so they can accept both
    strings and Commitish objects indistinctly
    '''
    if ref is None:
        return None
    if isinstance(ref, Commitish):
        return ref.ref
    elif isinstance(ref, basestring):
        return ref
    else:
        return str(ref)

SHA_MATCHER = re.compile(r"\b([a-f0-9]{40})\b")

def _ensurelist(o):
    if isinstance(o, list):
        return o
    else:
        return [o]

class Repository(object):

    MASTER = 'master'
    HEAD = 'HEAD'
    WORK_HEAD = 'WORK_HEAD'
    STAGE_HEAD = 'STAGE_HEAD'

    def __init__(self, url, group="", title = ""):
        self.url = url
        self.rootUrl = url.split("/repos")[0] + "/"
        self.title = title
        self.group = group

    def __apicall(self, command, payload = {}, transaction = False):
        if transaction:
            r = requests.get(self.url + "beginTransaction", params = {"output_format":"json"})
            r.raise_for_status()
            transactionId = r.json()["response"]["Transaction"]["ID"]
            payload["output_format"] = "json"
            payload["transactionId"] = transactionId
            r = requests.get(self.url + command, params = payload)
            r.raise_for_status()
            resp = json.loads(r.text.replace(r"\/", "/"))["response"]
            r = requests.get(self.url + "endTransaction", params = {"transactionId":transactionId})
            r.raise_for_status()
            return resp
        else:
            payload["output_format"] = "json"
            r = requests.get(self.url + command, params = payload)
            r.raise_for_status()
            j = json.loads(r.text.replace(r"\/", "/"))
            return j["response"]

    def _apicall(self, command, payload = {}, transaction = False):
        return execute(lambda: self.__apicall(command, payload, transaction))


    def branches(self):
        resp = self._apicall("branch", {"list":True})
        return [b["name"] for b in _ensurelist(resp["Local"]["Branch"])]

    def createbranch(self, ref, branch):
        self._apicall("branch", {"branchName":branch, "source": ref})

    def deletebranch(self, branch):
        raise NotImplementedError()

    def tags(self):
        return {}
        resp = self._apicall("tag", {"list":True})
        tags = [b["name"] for b in _ensurelist(resp["Tag"])]
        tags = {t: self.revparse(t) for t in tags}
        return tags

    def diff(self, oldRefSpec, newRefSpec, pathFilter = None):
        payload = {"oldRefSpec": oldRefSpec, "newRefSpec": newRefSpec}
        if pathFilter is not None:
            payload["pathFilter"]= pathFilter
        changes = []
        payload["page"] = 0
        while True:
            resp = self._apicall("diff", payload)
            if "diff" in resp:
                for d in _ensurelist(resp["diff"]):
                    changes.append(Diffentry(self, oldRefSpec, newRefSpec,
                                                d["newPath"], d["changeType"]))
                payload["page"] += 1
            else:
                break

        return changes

    def featurediff(self, oldTreeish, newTreeish, path, allAttrs = True):
        payload = {"oldTreeish": _resolveref(oldTreeish), "newTreeish": _resolveref(newTreeish),
                   "path": path, "all": allAttrs}
        resp = self._apicall("FeatureDiff", payload)
        return _ensurelist(resp["diff"])

    def feature(self, path, ref):
        payload = {"oldTreeish": _resolveref(ref), "newTreeish": _resolveref(ref), "path": path, "all": True}
        resp = self._apicall("FeatureDiff", payload)
        featurediff = _ensurelist(resp["diff"])
        return {f["attributename"]: f.get("oldvalue", None) for f in featurediff}

    def log(self, until = None, path = None, limit = None):
        payload = {"path": path} if path is not None else {}
        if until is not None:
            payload["until"]= _resolveref(until)
        if limit is not None:
            payload["limit"] = limit
        payload["countChanges"] = True
        commits = []
        payload["page"] = 0
        while True:
            resp = self._apicall("log", payload)
            if "commit" in resp:
                for c in _ensurelist(resp["commit"]):
                    parentslist = _ensurelist(c["parents"])
                    if parentslist == [""]:
                        parents = [NULL_ID]
                    else:
                        parents = [p["id"] for p in _ensurelist(c["parents"])]
                    committerdate = datetime.fromtimestamp((c["committer"]["timestamp"] - c["committer"]["timeZoneOffset"]) /1e3)
                    authordate = datetime.fromtimestamp((c["author"]["timestamp"] - c["author"]["timeZoneOffset"]) / 1e3)
                    commits.append(Commit(self, c["id"], c["tree"],
                             parents, c["message"],
                             c["author"]["name"], authordate,
                             c["committer"]["name"], committerdate,
                             c["adds"], c["removes"], c["modifies"]))
                payload["page"] += 1
            else:
                break

        return commits

    def lastupdated(self):
        try:
            return self.log(limit = 1)[0].committerdate
        except IndexError:
            return ""


    def trees(self, commit=None):
        commit = commit or self.HEAD
        #TODO use commit
        resp = self._apicall("ls-tree", {"onlyTrees":True})
        if isinstance(resp["node"], dict):
            trees = [resp["node"]]
        else:
            trees = resp["node"]
        return [t["path"] for t in trees]

    def removetree(self, path):
        self._apicall("remove", {"path":path, "recursive":"true"}, True)


    def revparse(self, rev):
        '''Returns the SHA-1 of a given element, represented as a string'''
        if SHA_MATCHER.match(rev) is not None:
            return rev
        else:
            return self._apicall("refparse", {"name": rev})["Ref"]["objectId"]

    def _preparelayerdownload(self, layername, bbox = None, ref = None):
        ref = _resolveref(ref) or self.HEAD
        params = {"root": ref, "format": "gpkg", "table": layername,
                  "path": layername, "interchange":True}
        if bbox is not None:
            trans = QgsCoordinateTransform(QgsCoordinateReferenceSystem(bbox[1]),
                                            QgsCoordinateReferenceSystem("EPSG:4326"))
            bbox4326 = trans.transform(bbox[0])
            sbbox = ",".join([bbox4326.xMinimum(), bbox4326.xMaximum(),
                             bbox4326.yMinimum(), bbox4326.yMaximum(), "EPSG:4326"])
            params["bbox"] = sbbox
        url  = self.url + "export.json"
        r = requests.get(url, params=params)
        r.raise_for_status()
        return r.json()["task"]["id"]

    def _downloadlayer(self, taskid, filename, layername):
        url  = self.rootUrl + "tasks/%s/download" % str(taskid)
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(filename, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

        con = sqlite3.connect(filename)
        cursor = con.cursor()
        cursor.execute("DELETE FROM %s_audit;" % layername)
        cursor.close()
        con.commit()

    def checkoutlayer(self, filename, layername, bbox = None, ref = None):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        taskid = self._preparelayerdownload(layername, bbox, ref)
        checker = TaskChecker(self.rootUrl, taskid)
        loop = QEventLoop()
        checker.taskIsFinished.connect(loop.exit, Qt.QueuedConnection)
        checker.start()
        loop.exec_(flags = QEventLoop.ExcludeUserInputEvents)
        self._downloadlayer(taskid, filename, layername)
        QApplication.restoreOverrideCursor()


    def importgeopkg(self, layer, message, authorName, authorEmail):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        filename, layername = namesFromLayer(layer)
        r = requests.get(self.url + "beginTransaction", params = {"output_format":"json"})
        r.raise_for_status()
        transactionId = r.json()["response"]["Transaction"]["ID"]
        payload = {"authorEmail": authorEmail, "authorName": authorName,
                   "message": message, 'destPath':layername, "format": "gpkg",
                   "transactionId": transactionId}
        if isRepoLayer(layer):
            payload["interchange=true"]
        files = {'fileUpload': open(filename, 'rb')}
        r = requests.post(self.url + "import.json", params = payload, files=files)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        taskId = root.find("task").find("id").text
        checker = TaskChecker(self.rootUrl, taskId)
        loop = QEventLoop()
        checker.taskIsFinished.connect(loop.exit, Qt.QueuedConnection)
        checker.start()
        loop.exec_(flags = QEventLoop.ExcludeUserInputEvents)
        if not checker.ok:
            if "conflicts" in checker.errorMessage.lower():
                raise MergeConflictsException()
            else:
                raise GeoGigException("Cannot import layer: %s" % checker.errorMessage)
        r = requests.get(self.url + "endTransaction", params = {"transactionId":transactionId})
        r.raise_for_status()
        QApplication.restoreOverrideCursor()



    def fullDescription(self):
        def _prepareDescription():
            try:
                c = self.log(limit = 1)[0]
                epoch = time.mktime(c.committerdate.timetuple())
                offset = datetime.fromtimestamp (epoch) - datetime.utcfromtimestamp (epoch)
                d = c.committerdate + offset
                lastDate = d.strftime("%b %d, %Y %I:%M%p")
                author = c.authorname
                lastVersion = "%s (%s by %s)" % (c.message.splitlines()[0], lastDate, author)
            except:
                lastVersion = ""
            with open(resourceFile("descriptiontemplate_edit.html")) as f:
                s = "".join(f.readlines())
            s = s.replace("[TITLE]", self.title)
            s = s.replace("[URL]", self.url)
            s = s.replace("[LAST_VERSION]", lastVersion)
            layers = "<dl>%s</dl>" % "".join(["<dd>%s <a href='checkout:%s'>[Add to QGIS]</a></dd>" % (tree,tree) for tree in self.trees()])
            s = s.replace("[LAYERS]", layers)
            s = s.replace("[LAYERNAMES]", ",".join(self.trees()))
            return s
        return(execute(_prepareDescription))

    def delete(self):
        self._apicall("delete")

class TaskChecker(QObject):
    taskIsFinished = pyqtSignal()
    def __init__(self, url, taskid):
        QObject.__init__(self)
        self.taskid = taskid
        self.url = url + "tasks/%s.json" % str(self.taskid)
    def start(self):
        self.checkTask()
    def checkTask(self):
        r = requests.get(self.url, stream=True)
        r.raise_for_status()
        ret = r.json()
        if ret["task"]["status"] == "FINISHED":
            self.ok = True
            self.taskIsFinished.emit()
        elif ret["task"]["status"] == "FAILED":
            self.ok = False
            self.errorMessage = ret["task"]["error"]["message"]
            self.taskIsFinished.emit()
        else:
            QTimer.singleShot(500, self.checkTask)

repos = {}

def addRepo(repo):
    global repos
    repos.append(repo)
    saveRepos()

def removeRepo(repo):
    global repos
    repos.remove(repo)
    saveRepos()

def saveRepos():
    filename = os.path.join(userFolder(), "repositories")
    towrite=[{"url": r.url, "group":r.group, "title": r.title} for r in repos]
    with open(filename, "w") as f:
        f.write(json.dumps(towrite))

def readRepos():
    global repos
    filename = os.path.join(userFolder(), "repositories")
    if os.path.exists(filename):
        repoDescs = json.load(open(filename))
    repos = [Repository(r["url"], r["group"], r["title"]) for r in repoDescs]

readRepos()


def repositoriesFromUrl(url, title):
    if not url.endswith("/"):
        url = url + "/"
    r = requests.get(url + "repos")
    r.raise_for_status()

    root = ET.fromstring(r.text)

    repos = []
    for country in root.findall('repo'):
        name = country.find('name').text
        repos.append(Repository(url + "repos/%s/" % name, title, name))

    return repos
