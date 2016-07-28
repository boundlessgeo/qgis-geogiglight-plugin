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
from diff import Diffentry, ConflictDiff
from commitish import Commitish
import os
from geogig.tools.utils import userFolder, resourceFile
import json
from geogig.geogigwebapi.commit import NULL_ID
from datetime import datetime
import time
import sqlite3
from geogig.gui.executor import execute
import shutil
from qgis.core import *
from PyQt4.QtCore import pyqtSignal, QEventLoop, Qt, QTimer, QObject, QPyNullVariant
from PyQt4.QtGui import QApplication
from PyQt4.Qt import QCursor
from geogig import config
from geogig.tools.layertracking import isRepoLayer
import xml.etree.ElementTree as ET
from geogig.tools.layers import formatSource, namesFromLayer
from requests.exceptions import HTTPError, ConnectionError
from geogig.config import GENERAL, LOG_SERVER_CALLS, getConfigValue


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

    def __eq__(self, o):
        try:
            return o.url == self.url
        except:
            return False

    def __ne__(self, o):
        return not self.__eq__(o)

    def __log(self, url, response, params, operation = "GET"):
        if getConfigValue(GENERAL, LOG_SERVER_CALLS):
            msg = "%s: %s\nPARAMS: %s\nRESPONSE: %s" % (operation, url, params, response)
            QgsMessageLog.logMessage(msg, 'GeoGig', QgsMessageLog.INFO)

    def __apicall(self, command, payload={}, transaction=False):
        try:
            if transaction:
                url = self.url + "beginTransaction"
                params = {"output_format":"json"}
                r = requests.get(url, params=params)
                r.raise_for_status()
                self.__log(url, r.json(), params)
                transactionId = r.json()["response"]["Transaction"]["ID"]
                payload["output_format"] = "json"
                payload["transactionId"] = transactionId
                url = self.url + command
                r = requests.get(url, params=payload)
                r.raise_for_status()
                resp = json.loads(r.text.replace(r"\/", "/"))["response"]
                self.__log(url, resp, payload)
                params = {"transactionId":transactionId, "output_format":"json"}
                r = requests.get(self.url + "endTransaction", params = params)
                r.raise_for_status()
                self.__log(url, r.json(), params)
                return resp
            else:
                payload["output_format"] = "json"
                url = self.url + command
                r = requests.get(url, params=payload)
                r.raise_for_status()
                j = json.loads(r.text.replace(r"\/", "/"))
                self.__log(url, r.json(), payload)
                return j["response"]
        except ConnectionError, e:
            msg = "<b>Network connection error</b><br><tt>%s</tt>" % e
            QgsMessageLog.logMessage(msg, "GeoGig", level=QgsMessageLog.CRITICAL)
            raise GeoGigException(msg)

    def _apicall(self, command, payload = {}, transaction = False):
        return execute(lambda: self.__apicall(command, payload, transaction))

    def branches(self):
        resp = self._apicall("branch", {"list":True})
        return [b["name"] for b in _ensurelist(resp["Local"]["Branch"])]

    def createbranch(self, ref, branch):
        self._apicall("branch", {"branchName":branch, "source": ref})

    def deletebranch(self, branch):
        self._apicall("updateref", {"name": branch, "delete": True})

    def tags(self):
        r = self._apicall("tag", {})
        if "Tag" in r:
            tags = {t["name"]: t["commitid"] for t in _ensurelist(r["Tag"])}
        else:
            tags = {}
        return tags

    def createtag(self, ref, tag):
        r = requests.post(self.url + "tag", params = {"commit":ref, "name": tag, "message": tag}, json = {})
        r.raise_for_status()

    def deletetag(self, tag):
        self._apicall("updateref", {"name": tag, "delete": True})

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
                    path = d["newPath"] or d["path"]
                    changes.append(Diffentry(self, oldRefSpec, newRefSpec,
                                                path, d["changeType"]))
                payload["page"] += 1
            else:
                break
        return changes

    def _downloadfile(self, taskid, filename):
        url  = self.rootUrl + "tasks/%s/download" % str(taskid)
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(filename, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

    def exportdiff(self, layername, oldRef, newRef, filename):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        params = {"oldRef": oldRef, "newRef": newRef, "format": "gpkg"}
        url  = self.url + "export-diff.json"
        r = requests.get(url, params=params)
        r.raise_for_status()
        taskid = r.json()["task"]["id"]
        checker = TaskChecker(self.rootUrl, taskid)
        loop = QEventLoop()
        checker.taskIsFinished.connect(loop.exit, Qt.QueuedConnection)
        checker.start()
        loop.exec_(flags = QEventLoop.ExcludeUserInputEvents)
        self._downloadfile(taskid, filename)
        QApplication.restoreOverrideCursor()

    def featurediff(self, oldTreeish, newTreeish, path, allAttrs = True):
        payload = {"oldTreeish": _resolveref(oldTreeish), "newTreeish": _resolveref(newTreeish),
                   "path": path, "all": allAttrs}
        resp = self._apicall("featurediff", payload)
        return _ensurelist(resp["diff"])

    def feature(self, path, ref):
        payload = {"oldTreeish": _resolveref(ref), "newTreeish": _resolveref(ref), "path": path, "all": True}
        resp = self._apicall("featurediff", payload)
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
            try:
                resp = self._apicall("log", payload)
            except HTTPError, e:
                #TODO more accurate error treatment
                return []
            if "commit" in resp:
                for c in _ensurelist(resp["commit"]):
                    commits.append(self._parseCommit(c))
                payload["page"] += 1
            else:
                break

        return commits

    def _parseCommit(self, c):
        parentslist = _ensurelist(c["parents"])
        if parentslist == [""]:
            parents = [NULL_ID]
        else:
            parents = [p for p in _ensurelist(c["parents"]["id"])]
        committerdate = datetime.fromtimestamp((c["committer"]["timestamp"] - c["committer"]["timeZoneOffset"]) /1e3)
        authordate = datetime.fromtimestamp((c["author"]["timestamp"] - c["author"]["timeZoneOffset"]) / 1e3)
        return Commit(self, c["id"], c["tree"],
                 parents, c["message"],
                 c["author"]["name"], authordate,
                 c["committer"]["name"], committerdate,
                 c.get("adds", 0), c.get("removes", 0), c.get("modifies", 0))

    def lastupdated(self):
        try:
            return self.log(limit = 1)[0].committerdate
        except IndexError:
            return None


    def blame(self, path):
        resp = self._apicall("blame", {"path":path})
        attrs = resp["Blame"]["Attribute"]
        blame = {}
        for a in attrs:
            blame[a["name"]] = (a["value"], self._parseCommit(a["commit"]))

        return blame

    def trees(self, commit=None):
        commit = commit or self.HEAD
        #TODO use commit
        resp = self._apicall("ls-tree", {"onlyTrees":True, "path": commit})
        if "node" not in resp.keys():
            return []
        if isinstance(resp["node"], dict):
            trees = [resp["node"]]
        else:
            trees = resp["node"]
        return [t["path"] for t in trees]

    def removetree(self, path, user, email):
        r = requests.get(self.url + "beginTransaction", params = {"output_format":"json"})
        r.raise_for_status()
        transactionId = r.json()["response"]["Transaction"]["ID"]
        self.__log(r.url, r.json(), params = {"output_format":"json"})
        payload = {"path":path, "recursive":"true", "output_format": "json",
                   "transactionId": transactionId}
        r = requests.get(self.url + "remove", params=payload)
        r.raise_for_status()
        self.__log(r.url, r.json(), payload)
        self.commitAndCloseTransaction(user, email, "removed layer %s" % path, transactionId)


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


    def checkoutlayer(self, filename, layername, bbox = None, ref = None):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        taskid = self._preparelayerdownload(layername, bbox, ref)
        checker = TaskChecker(self.rootUrl, taskid)
        loop = QEventLoop()
        checker.taskIsFinished.connect(loop.exit, Qt.QueuedConnection)
        checker.start()
        loop.exec_(flags = QEventLoop.ExcludeUserInputEvents)
        self._downloadfile(taskid, filename)
        QApplication.restoreOverrideCursor()


    def importgeopkg(self, layer, branch, message, authorName, authorEmail, interchange):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        filename, layername = namesFromLayer(layer)
        r = requests.get(self.url + "beginTransaction", params = {"output_format":"json"})
        r.raise_for_status()
        transactionId = r.json()["response"]["Transaction"]["ID"]
        payload = {"authorEmail": authorEmail, "authorName": authorName,
                   "message": message, 'destPath':layername, "format": "gpkg",
                   "transactionId": transactionId, "root": branch}
        if interchange:
            payload["interchange"]= True
        files = {'fileUpload': open(filename, 'rb')}
        r = requests.post(self.url + "import.json", params = payload, files = files)
        self.__log(r.url, r.text, payload, "POST")
        r.raise_for_status()
        root = ET.fromstring(r.text)
        taskId = root.find("id").text
        checker = TaskChecker(self.rootUrl, taskId)
        loop = QEventLoop()
        checker.taskIsFinished.connect(loop.exit, Qt.QueuedConnection)
        checker.start()
        loop.exec_(flags = QEventLoop.ExcludeUserInputEvents)
        QApplication.restoreOverrideCursor()
        if not checker.ok and "error" in checker.response["task"]:
            errorMessage = checker.response["task"]["error"]["message"]
            raise GeoGigException("Cannot import layer: %s" % errorMessage)
        if interchange:
            try:
                nconflicts = checker.response["task"]["result"]["Merge"]["conflicts"]
            except KeyError:
                nconflicts = 0
            if nconflicts:
                mergeCommitId = self.HEAD
                importCommitId = checker.response["task"]["result"]["import"]["importCommit"]["id"]
                ancestor = checker.response["task"]["result"]["Merge"]["ancestor"]
                remote = checker.response["task"]["result"]["Merge"]["ours"]
                featureIds = checker.response["task"]["result"]["import"]["NewFeatures"]["type"].get("ids", [])
                con = sqlite3.connect(filename)
                cursor = con.cursor()
                geomField = cursor.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name='%s';" % layername).fetchone()[0]

                def _local(fid):
                    cursor.execute("SELECT gpkg_fid FROM %s_fids WHERE geogig_fid='%s';" % (layername, fid))
                    gpkgfid = int(cursor.fetchone()[0])
                    request = QgsFeatureRequest()
                    request.setFilterFid(gpkgfid)
                    try:
                        feature = layer.getFeatures(request).next()
                    except:
                        return None
                    def _ensureNone(v):
                        if isinstance(v, QPyNullVariant):
                            return None
                        else:
                            return v
                    local = {f.name():_ensureNone(feature[f.name()]) for f in layer.pendingFields()}
                    try:
                        local[geomField] = feature.geometry().exportToWkt()
                    except:
                        local[geomField] = None
                    return local

                conflicts = []
                conflictsResponse = _ensurelist(checker.response["task"]["result"]["Merge"]["Feature"])
                for c in conflictsResponse:
                    if c["change"] == "CONFLICT":
                        remoteFeatureId = c["ourvalue"]
                        localFeatureId = c["theirvalue"]
                        localFeature = _local(c["id"].split("/")[-1])
                        conflicts.append(ConflictDiff(self, c["id"], ancestor, remote, importCommitId, localFeature,
                                              localFeatureId, remoteFeatureId, transactionId))
                cursor.close()
                con.close()
            else:
                self.closeTransaction(transactionId)
                mergeCommitId = checker.response["task"]["result"]["newCommit"]["id"]
                importCommitId = checker.response["task"]["result"]["importCommit"]["id"]
                featureIds = _ensurelist(checker.response["task"]["result"]["NewFeatures"]["type"].get("id", []))
                conflicts = []
            featureIds = [(f["@provided"], f["@assigned"]) for f in featureIds]
            return mergeCommitId, importCommitId, conflicts, featureIds
        else:
            self.closeTransaction(transactionId)

    def resolveConflictWithFeature(self, path, feature, ours, theirs, transactionId):
        merges = {k:{"value": v} for k,v in feature.iteritems()}
        payload = {"path": path, "ours": ours, "theirs": theirs,
                   "merges": merges}
        r = requests.post(self.url + "repo/mergefeature", json = payload)
        self.__log(r.url, r.text, payload, "POST")
        r.raise_for_status()
        fid = r.text
        self.resolveConflictWithFeatureId(path, fid, transactionId)

    def resolveConflictWithFeatureId(self, path, fid, transactionId):
        payload = {"path": path, "objectid": fid,
                   "transactionId": transactionId}
        r = requests.get(self.url + "resolveconflict", params = payload)
        self.__log(r.url, r.text, payload)
        r.raise_for_status()

    def commitAndCloseTransaction(self, user, email, message, transactionId):
        params = {"all": True, "message": message, "transactionId": transactionId,
                  "authorName": user, "authorEmail": email}
        r = requests.get(self.url + "commit", params = params)
        self.__log(r.url, r.text, params)
        r.raise_for_status()
        self.closeTransaction(transactionId)

    def closeTransaction(self, transactionId):
        r = requests.get(self.url + "endTransaction", params = {"transactionId": transactionId})
        self.__log(r.url, r.text, {"transactionId": transactionId})
        r.raise_for_status()

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
        r = self._apicall("delete")
        params = {"token": r["token"]}
        r = requests.delete(self.url, params = params)
        r.raise_for_status()

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
        self.response = r.json()
        if self.response["task"]["status"] == "FINISHED":
            self.ok = True
            self.taskIsFinished.emit()
        elif self.response["task"]["status"] == "FAILED":
            self.ok = False
            self.taskIsFinished.emit()
        else:
            QTimer.singleShot(500, self.checkTask)

repos = []
repoEndpoints = {}
availableRepoEndpoints = {}

def addRepo(repo):
    global repos
    repos.append(repo)

def removeRepo(repo):
    global repos
    for r in repos:
        if repo.url == r.url:
            repos.remove(r)
            break

def addRepoEndpoint(url, title):
    global repoEndpoints
    global repos
    repoEndpoints[title] = url
    saveRepoEndpoints()
    _repos = execute(lambda: repositoriesFromUrl(url, title))
    repos.extend(_repos)
    availableRepoEndpoints[title] = url
    return _repos

def removeRepoEndpoint(title):
    global repoEndpoints
    global repos
    url = repoEndpoints[title]
    for repo in repos[::-1]:
        if url in repo.rootUrl:
            repos.remove(repo)

    del repoEndpoints[title]
    if title in availableRepoEndpoints:
        del availableRepoEndpoints[title]
    saveRepoEndpoints()

def saveRepoEndpoints():
    filename = os.path.join(userFolder(), "repositories")
    towrite=[{"url": url, "title": title} for title,url in repoEndpoints.iteritems()]
    with open(filename, "w") as f:
        f.write(json.dumps(towrite))


def repositoriesFromUrl(url, title):
    if not url.endswith("/"):
        url = url + "/"

    r = requests.get(url + "repos")
    r.raise_for_status()


    root = ET.fromstring(r.text)

    repos = []
    for node in root.findall('repo'):
        name = node.find('name').text
        repos.append(Repository(url + "repos/%s/" % name, title, name))

    return repos

def createRepoAtUrl(url, group, name):
    if not url.endswith("/"):
        url = url + "/"
    r = requests.put(url + "repos/%s/init" % name)
    r.raise_for_status()
    return Repository(url + "repos/%s/" % name, group, name)


def readRepos():
    global repos
    global repoEndpoints
    global availableRepoEndpoints
    repos = []
    repoEndpoints = {}
    availableRepoEndpoints = {}
    filename = os.path.join(userFolder(), "repositories")
    if os.path.exists(filename):
        repoDescs = json.load(open(filename))
        for r in repoDescs:
            repoEndpoints[r["title"]] = r["url"]
            try:
                _repos = execute(lambda: repositoriesFromUrl(r["url"], r["title"]))
                repos.extend(_repos)
                availableRepoEndpoints[r["title"]] = r["url"]
            except:
                pass


readRepos()
