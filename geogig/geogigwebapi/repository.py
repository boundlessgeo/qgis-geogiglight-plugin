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
from __future__ import print_function
from builtins import str
from builtins import object

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import re
import json
import time
import sqlite3
from datetime import datetime
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict

import requests
from requests.exceptions import HTTPError, ConnectionError
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from qgis.PyQt.QtCore import pyqtSignal, Qt, QTimer, QObject, QEventLoop
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import QApplication

from qgis.core import QgsMessageLog, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsFeatureRequest, NULL
from qgis.utils import iface

from geogig import config
from geogig.config import LOG_SERVER_CALLS

from geogig.geogigwebapi.commit import NULL_ID, Commit
from geogig.geogigwebapi.commitish import Commitish
from geogig.geogigwebapi.diff import Diffentry, ConflictDiff

from qgiscommons2.gui import execute

from geogig.tools.layers import formatSource, namesFromLayer
from geogig.tools.utils import userFolder, resourceFile
from geogig.tools.layertracking import isRepoLayer, getTrackingInfoForGeogigLayer

from qgiscommons2.settings import pluginSetting
from qgiscommons2.files import tempFilenameInTempFolder

class GeoGigException(Exception):
    pass


class MergeConflictsException(GeoGigException):
    pass


class CannotPushException(GeoGigException):
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
    elif isinstance(ref, str):
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
        if pluginSetting(LOG_SERVER_CALLS):
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
        except ConnectionError as e:
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
            if "diff" in resp and resp["diff"]:
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
            total = r.headers.get('content-length')
            if total is None:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
            else:
                dl = 0
                total = float(total)
                for data in r.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    done = int(100 * dl / total)
                    iface.mainWindow().statusBar().showMessage("Transferring geopkg from GeoGig server [{}%]".format(done))

        iface.mainWindow().statusBar().showMessage("")

    def exportdiff(self, oldRef, newRef, filename):
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
            except HTTPError as e:
                #TODO more accurate error treatment
                return []
            if "commit" in resp and resp["commit"]:
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
        committerdate = datetime.fromtimestamp(c["committer"]["timestamp"] / 1e3)
        authordate = datetime.fromtimestamp(c["author"]["timestamp"] / 1e3)
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
        if "node" not in list(resp.keys()):
            return []
        if isinstance(resp["node"], dict):
            trees = [resp["node"]]
        else:
            trees = resp["node"]
        return [t["path"] for t in trees]

    def _checkoutbranch(self, branch, transactionId):
        payload = {"branch": branch,"transactionId": transactionId}
        r = requests.get(self.url + "checkout", params = payload)
        self.__log(r.url, r.text, payload)
        r.raise_for_status()

    def removetree(self, path, user, email, branch = None):
        r = requests.get(self.url + "beginTransaction", params = {"output_format":"json"})
        r.raise_for_status()
        transactionId = r.json()["response"]["Transaction"]["ID"]
        self.__log(r.url, r.json(), params = {"output_format":"json"})
        if branch:
            self._checkoutbranch(branch, transactionId)
        payload = {"path":path, "recursive":"true", "output_format": "json",
                   "transactionId": transactionId}
        r = requests.get(self.url + "remove", params=payload)
        r.raise_for_status()
        self.__log(r.url, r.json(), payload)

        params = {"all": True, "message": "removed layer %s" % path,
                  "transactionId": transactionId,
                  "authorName": user, "authorEmail": email}
        r = requests.get(self.url + "commit", params = params)
        self.__log(r.url, r.text, params)
        r.raise_for_status()
        if branch:
            self._checkoutbranch("refs/heads/master", transactionId)
        self.closeTransaction(transactionId)

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
        iface.mainWindow().statusBar().showMessage("Creating geopkg on GeoGig server...")
        taskid = self._preparelayerdownload(layername, bbox, ref)
        checker = TaskChecker(self.rootUrl, taskid)
        loop = QEventLoop()
        checker.taskIsFinished.connect(loop.exit, Qt.QueuedConnection)
        checker.start()
        loop.exec_(flags = QEventLoop.ExcludeUserInputEvents)
        self._downloadfile(taskid, filename)
        QApplication.restoreOverrideCursor()

    def saveaudittables(self, filename, layer):
        newfilename = tempFilenameInTempFolder(os.path.basename(filename))

        conn = sqlite3.connect(newfilename)
        c = conn.cursor()
        c.execute("ATTACH DATABASE ? AS db2", (filename,))
        tables = ["%s_audit" % layer, "%s_fids" % layer, "geogig_audited_tables", "gpkg_geometry_columns"]
        for table in tables:
            c.execute("SELECT sql FROM db2.sqlite_master WHERE type='table' AND name='%s'" % table)
            c.execute(c.fetchone()[0])
            c.execute("INSERT INTO main.%s SELECT * FROM db2.%s" % (table, table))

        c.execute("SELECT sql FROM db2.sqlite_master WHERE type='table' AND name='%s'" % layer)
        c.execute(c.fetchone()[0])
        c.execute("SELECT * FROM db2.%s_audit WHERE audit_op<>3;" % layer)
        changed = c.fetchall()
        used = []
        for feature in changed[::-1]:
            if feature[0] not in used:
                c.execute('INSERT INTO main.%s SELECT * FROM db2.%s WHERE fid=%s;' % (layer, layer, feature[0]))
                used.append(feature[0])

        conn.commit()
        conn.close()

        return newfilename

    def importgeopkg(self, layer, branch, message, authorName, authorEmail, interchange):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        filename, layername = namesFromLayer(layer)
        r = requests.get(self.url + "beginTransaction", params = {"output_format":"json"})
        r.raise_for_status()
        transactionId = r.json()["response"]["Transaction"]["ID"]
        self._checkoutbranch(branch, transactionId)
        payload = {"authorEmail": authorEmail, "authorName": authorName,
                   "message": message, 'destPath':layername, "format": "gpkg",
                   "transactionId": transactionId}
        # fix_print_with_import
        if interchange:
            payload["interchange"]= True
            filename = self.saveaudittables(filename, layername)
        files = {'fileUpload': (os.path.basename(filename), open(filename, 'rb'))}

        encoder = MultipartEncoder(files)
        total = float(encoder.len)
        def callback(m):
            done = int(100 * m.bytes_read / total)
            iface.mainWindow().statusBar().showMessage("Transferring geopkg to GeoGig server [{}%]".format(done))
        monitor = MultipartEncoderMonitor(encoder, callback)
        r = requests.post(self.url + "import.json", params = payload, data=monitor,
                  headers={'Content-Type': monitor.content_type})
        self.__log(r.url, r.text, payload, "POST")
        r.raise_for_status()
        resp = r.json()
        taskId = resp["task"]["id"]
        checker = TaskChecker(self.rootUrl, taskId)
        loop = QEventLoop()
        checker.taskIsFinished.connect(loop.exit, Qt.QueuedConnection)
        checker.start()
        loop.exec_(flags = QEventLoop.ExcludeUserInputEvents)
        QApplication.restoreOverrideCursor()
        iface.mainWindow().statusBar().showMessage("")
        if not checker.ok and "error" in checker.response["task"]:
            errorMessage = checker.response["task"]["error"]["message"]
            raise GeoGigException("Cannot import layer: %s" % errorMessage)
        if interchange:
            try:
                nconflicts = checker.response["task"]["result"]["Merge"]["conflicts"]
            except KeyError, e:
                nconflicts = 0
            if nconflicts:
                mergeCommitId = self.HEAD
                importCommitId = checker.response["task"]["result"]["import"]["importCommit"]["id"]
                ancestor = checker.response["task"]["result"]["Merge"]["ancestor"]
                remote = checker.response["task"]["result"]["Merge"]["ours"]
                try:
                    featureIds = checker.response["task"]["result"]["import"]["NewFeatures"]["type"][0].get("ids", [])
                except:
                    featureIds = []
                con = sqlite3.connect(filename)
                cursor = con.cursor()
                geomField = cursor.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name='%s';" % layername).fetchone()[0]

                def _local(fid):
                    cursor.execute("SELECT gpkg_fid FROM %s_fids WHERE geogig_fid='%s';" % (layername, fid))
                    gpkgfid = int(cursor.fetchone()[0])
                    request = QgsFeatureRequest()
                    request.setFilterFid(gpkgfid)
                    try:
                        feature = next(layer.getFeatures(request))
                    except:
                        return None
                    def _ensureNone(v):
                        if v == NULL:
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
                self._checkoutbranch("master", transactionId)
                self.closeTransaction(transactionId)
                mergeCommitId = checker.response["task"]["result"]["newCommit"]["id"]
                importCommitId = checker.response["task"]["result"]["importCommit"]["id"]
                try:
                    featureIds = checker.response["task"]["result"]["NewFeatures"]["type"][0].get("id", [])
                except:
                    featureIds = []
                conflicts = []
            featureIds = [(f["provided"], f["assigned"]) for f in featureIds]
            return mergeCommitId, importCommitId, conflicts, featureIds
        else:
            self.closeTransaction(transactionId)

    def resolveConflictWithFeature(self, path, feature, ours, theirs, transactionId):
        merges = {k:{"value": v} for k,v in feature.items()}
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

    def deleteFeature(self, path, transactionId):
        payload = {"path": path, "transactionId": transactionId}
        r = requests.get(self.url + "remove", params = payload)
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

    def merge(self, branchToMerge, branchToMergeInto):
        r = requests.get(self.url + "beginTransaction", params = {"output_format":"json"})
        r.raise_for_status()
        transactionId = r.json()["response"]["Transaction"]["ID"]
        self.__log(r.url, r.json(), params = {"output_format":"json"})
        self._checkoutbranch(branchToMergeInto, transactionId)
        payload = {"commit":branchToMerge, "transactionId": transactionId, "output_format":"json"}
        r = requests.get(self.url + "merge", params=payload)
        r.raise_for_status()
        self.__log(r.url, r.json(), payload)
        response = r.json()["response"]["Merge"]
        try:
            nconflicts = response["conflicts"]
        except KeyError:
            nconflicts = 0
        if nconflicts:
            ancestor = response["ancestor"]
            ours = response["ours"]
            theirs = response["theirs"]

            conflicts = []
            conflictsResponse = _ensurelist(response["Feature"])
            for c in conflictsResponse:
                if c["change"] == "CONFLICT":
                    conflicts.append(ConflictDiff(self, c["id"], ancestor, ours, theirs, None,
                                    c["ourvalue"], c["theirvalue"], transactionId))
            return conflicts
        else:
            self._checkoutbranch("master", transactionId)
            self.closeTransaction(transactionId)
            return []

    def commitAndCloseMergeAndTransaction(self, user, email, message, transactionId):
        params = {"all": True, "message": message, "transactionId": transactionId,
                  "authorName": user, "authorEmail": email}
        r = requests.get(self.url + "commit", params = params)
        self.__log(r.url, r.text, params)
        r.raise_for_status()
        self._checkoutbranch("master", transactionId)
        self.closeTransaction(transactionId)

    def delete(self):
        r = self._apicall("delete")
        params = {"token": r["token"]}
        r = requests.delete(self.url, params = params)
        r.raise_for_status()

    def addremote(self, name, url):
        url = url.strip(" ")
        payload = {"remoteURL": url, "remoteName": name}
        self._apicall("remote", payload)

    def removeremote(self, name):
        payload = {"remove": True, "remoteName": name}
        self._apicall("remote", payload)

    def remotes(self):
        payload = {"list": True, "verbose": True}
        response = self._apicall("remote", payload)
        if "Remote" in response:
            remotes = _ensurelist(response["Remote"])
            remotes = {r["name"]:r["url"] for r in remotes}
            return remotes
        else:
            return {}

    def push(self, remote, branch):
        payload = {"ref": branch, "remoteName": remote}
        try:
            r = self._apicall("push", payload)
            success = r["success"]
            if not success:
                raise CannotPushException(r["error"])
        except HTTPError, e:
            raise CannotPushException(e.response.json()["response"]["error"])

    def pull (self, remote, branch):
        r = requests.get(self.url + "beginTransaction", params = {"output_format":"json"})
        r.raise_for_status()
        transactionId = r.json()["response"]["Transaction"]["ID"]
        self.__log(r.url, r.json(), params = {"output_format":"json"})
        self._checkoutbranch(branch, transactionId)
        payload = {"ref": branch, "remoteName": remote, "transactionId": transactionId, "output_format":"json"}
        r = requests.get(self.url + "pull", params=payload)
        r.raise_for_status()
        self.__log(r.url, r.json(), payload)
        response = r.json()["response"]
        try:
            nconflicts = response["Merge"]["conflicts"]
        except KeyError:
            nconflicts = 0
        if nconflicts:
            ancestor = response["Merge"]["ancestor"]
            ours = response["Merge"]["ours"]
            theirs = response["Merge"]["theirs"]
            conflicts = []
            conflictsResponse = _ensurelist(response["Merge"]["Feature"])
            for c in conflictsResponse:
                if c["change"] == "CONFLICT":
                    conflicts.append(ConflictDiff(self, c["id"], ancestor, ours, theirs, None,
                                    c["ourvalue"], c["theirvalue"], transactionId))
            return conflicts
        else:
            self.closeTransaction(transactionId)
            return []


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
            try:
                progressTask = self.response["task"]["progress"]["task"]
                progressAmount = self.response["task"]["progress"]["amount"]
                iface.mainWindow().statusBar().showMessage("%s [%s]" % (progressTask, progressAmount))
            except KeyError:
                pass
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
    towrite=[{"url": url, "title": title} for title,url in repoEndpoints.items()]
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
    r = requests.put(url + "repos/%s/init.json" % name, data = "dummy")
    if not r.json()["response"]["success"]:
        raise GeoGigException("A repository with that name already exists")
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

def refreshEndpoint(name):
    #TODO: optimize this
    readRepos()

def endpointRepos(name):
    groupRepos = [r for r in repos if r.group == name]
    return groupRepos

readRepos()
