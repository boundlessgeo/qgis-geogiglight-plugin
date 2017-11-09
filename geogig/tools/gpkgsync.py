# -*- coding: utf-8 -*-

"""
***************************************************************************
    gpkgsync.py
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
from builtins import zip

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import os
import sqlite3

from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox

from qgis.core import QgsMessageLog, QgsMapLayerRegistry, QgsVectorLayer
from qgis.gui import QgsMessageBar
from qgis.utils import iface


from geogig import config
from geogig.repowatcher import repoWatcher

from geogig.gui.dialogs.conflictdialog import ConflictDialog
from geogig.gui.dialogs.commitdialog import CommitDialog
from geogig.gui.dialogs import commitdialog
from geogig.gui.dialogs.userconfigdialog import UserConfigDialog

from geogig.geogigwebapi.diff import LocalDiff
from geogig.geogigwebapi.repository import GeoGigException, Repository

from geogig.tools.layertracking import (getTrackingInfoForGeogigLayer,
                                        removeTrackedLayer,
                                        addTrackedLayer,
                                        getTrackingInfo)
from geogig.tools.utils import (layerGeopackageFilename)
from geogig.tools.layers import (WrongLayerSourceException,
                                 layerFromSource,
                                 namesFromLayer,
                                 hasLocalChanges
                                )

from qgiscommons2.files import tempFilename
from qgiscommons2.layers import loadLayerNoCrsDialog

INSERT, UPDATE, DELETE  = 1, 2, 3


def syncLayer(layer):
    tracking = getTrackingInfo(layer)
    repo = Repository(tracking.repoUrl)
    filename, layername = namesFromLayer(layer)
    con = sqlite3.connect(filename)
    cursor = con.cursor()
    cursor.execute("SELECT * FROM %s_audit;" % layername)
    changes = bool(cursor.fetchall())
    cursor.close()
    con.close()
    if changes:
        con = sqlite3.connect(filename)
        cursor = con.cursor()
        beforeAttrs = set(v[1] for v in cursor.execute("PRAGMA table_info('%s');" % layername))
        afterAttrs = set(v[1] for v in cursor.execute("PRAGMA table_info('%s_audit');" % layername)
                         if v[1]not in ["audit_timestamp", "audit_op"])
        cursor.close()
        con.close()
        if beforeAttrs != afterAttrs:
            ret = QMessageBox.warning(iface.mainWindow(), "Cannot commit changes to repository",
                          "The structure of attributes table has been modified.\n"
                          "This type of change is not supported by GeoGig.",
                          QMessageBox.Yes)
            return

        user, email = config.getUserInfo()
        if user is None:
            return

        dlg = CommitDialog(repo, layername)
        dlg.exec_()
        if dlg.branch is None:
            return

        if dlg.branch not in repo.branches():
            commitId = getCommitId(layer)
            repo.createbranch(commitId, dlg.branch)
        mergeCommitId, importCommitId, conflicts, featureIds = repo.importgeopkg(layer, dlg.branch, dlg.message, user, email, True)

        if conflicts:
            ret = QMessageBox.warning(iface.mainWindow(), "Error while syncing",
                                      "There are conflicts between local and remote changes.\n"
                                      "Do you want to continue and fix them?",
                                      QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                repo.closeTransaction(conflicts[0].transactionId)
                return
            solved, resolvedConflicts = solveConflicts(conflicts)
            if not solved:
                repo.closeTransaction(conflicts[0].transactionId)
                return
            for conflict, resolution in zip(conflicts, list(resolvedConflicts.values())):
                if resolution == ConflictDialog.LOCAL:
                    conflict.resolveWithLocalVersion()
                elif resolution == ConflictDialog.REMOTE:
                    conflict.resolveWithRemoteVersion()
                elif resolution == ConflictDialog.DELETE:
                    conflict.resolveDeletingFeature()
                else:
                    conflict.resolveWithNewFeature(resolution)
            repo.commitAndCloseMergeAndTransaction(user, email, "Resolved merge conflicts", conflicts[0].transactionId)

        updateFeatureIds(repo, layer, featureIds)
        try:
            applyLayerChanges(repo, layer, importCommitId, mergeCommitId)
        except:
            QgsMessageLog.logMessage("Database locked while syncing. Using full layer checkout instead", level=QgsMessageLog.CRITICAL)
            repo.checkoutlayer(tracking.geopkg, layername, None, mergeCommitId)

        commitdialog.suggestedMessage = ""
    else:
        branches = []
        for branch in repo.branches():
            trees = repo.trees(branch)
            if layername in trees:
                branches.append(branch)

        branch, ok = QInputDialog.getItem(iface.mainWindow(), "Sync",
                                          "Select branch to update from",
                                          branches, 0, False)
        if not ok:
            return
        commitId = getCommitId(layer)
        headCommitId = repo.revparse(branch)
        applyLayerChanges(repo, layer, commitId, headCommitId)

    layer.reload()
    layer.triggerRepaint()
    repoWatcher.repoChanged.emit(repo)

    iface.messageBar().pushMessage("GeoGig", "Layer has been correctly synchronized",
                                                  level=QgsMessageBar.INFO,
                                                  duration=5)
    repoWatcher.layerUpdated.emit(layer)

def updateFeatureIds(repo, layer, featureIds):
    filename, layername = namesFromLayer(layer)
    con = sqlite3.connect(filename)
    cursor = con.cursor()
    for ids in featureIds:
        cursor.execute('INSERT INTO "%s_fids" VALUES ("%s", "%s")' % (layername, ids[0], ids[1]))
    cursor.close()
    con.commit()
    con.close()

def gpkgfidFromGeogigfid(cursor, layername, geogigfid):
    cursor.execute("SELECT gpkg_fid FROM %s_fids WHERE geogig_fid='%s';" % (layername, geogigfid))
    gpkgfid = cursor.fetchone()[0]
    return gpkgfid

def applyLayerChanges(repo, layer, beforeCommitId, afterCommitId, clearAudit = True):
    layer.reload()
    filename, layername = namesFromLayer(layer)
    changesFilename = tempFilename("gpkg")
    beforeCommitId, afterCommitId = repo.revparse(beforeCommitId), repo.revparse(afterCommitId)
    repo.exportdiff(beforeCommitId, afterCommitId, changesFilename, layername)

    con = sqlite3.connect(filename)
    cursor = con.cursor()
    changesCon = sqlite3.connect(changesFilename)
    changesCursor = changesCon.cursor()

    attributes = [v[1] for v in cursor.execute("PRAGMA table_info('%s');" % layername)]
    attrnames = [a for a in attributes if a != "fid"]

    changesCursor.execute("SELECT * FROM %s_changes WHERE audit_op=2;" % layername)
    modified = changesCursor.fetchall()
    for m in modified:
        geogigfid = m[0]
        changesGpkgfid = gpkgfidFromGeogigfid(changesCursor, layername, geogigfid)
        gpkgfid = gpkgfidFromGeogigfid(cursor, layername, geogigfid)
        changesCursor.execute("SELECT * FROM %s WHERE fid='%s';" % (layername, changesGpkgfid))
        featureRow = changesCursor.fetchone()
        attrs = {attr: featureRow[attributes.index(attr)] for attr in attrnames}
        vals = ",".join(['"%s"=?' % k for k in list(attrs.keys())])
        cursor.execute("UPDATE %s SET %s WHERE fid='%s'" % (layername, vals, gpkgfid), list(attrs.values()))

    changesCursor.execute("SELECT * FROM %s_changes WHERE audit_op=1;" % layername)
    added = changesCursor.fetchall()
    for a in added:
        geogigfid = a[0]
        changesGpkgfid = gpkgfidFromGeogigfid(changesCursor, layername, geogigfid)
        changesCursor.execute("SELECT * FROM %s WHERE fid='%s';" % (layername, changesGpkgfid))
        featureRow = changesCursor.fetchone()
        attrs = {attr: featureRow[attributes.index(attr)] for attr in attrnames}
        cols = ', '.join('"%s"' % col for col in list(attrs.keys()))
        vals = ', '.join('?' for val in list(attrs.values()))
        cursor.execute('INSERT INTO "%s" (%s) VALUES (%s)' % (layername, cols, vals), list(attrs.values()))
        gpkgfid = cursor.lastrowid
        cursor.execute('INSERT INTO "%s_fids" VALUES ("%s", "%s")' % (layername, gpkgfid, geogigfid))

    changesCursor.execute("SELECT * FROM %s_changes WHERE audit_op=3;" % layername)
    removed = changesCursor.fetchall()
    for r in removed:
        geogigfid = r[0]
        gpkgfid = gpkgfidFromGeogigfid(cursor, layername, geogigfid)
        cursor.execute("DELETE FROM %s WHERE fid='%s'" % (layername, gpkgfid))

    changesCursor.close()
    changesCon.close()

    if clearAudit:
        cursor.execute("DELETE FROM %s_audit;" % layername)
        cursor.execute("UPDATE geogig_audited_tables SET commit_id='%s' WHERE table_name='%s'" % (afterCommitId, layername))

    con.commit()
    cursor.close()
    con.close()


def getCommitId(layer):
    filename, layername = namesFromLayer(layer)
    con = sqlite3.connect(filename)
    cursor = con.cursor()
    cursor.execute("SELECT commit_id FROM geogig_audited_tables WHERE table_name='%s';" % layername)
    commitid = cursor.fetchone()[0]
    cursor.close()
    con.close()
    return commitid

def solveConflicts(conflicts):
    dlg = ConflictDialog(conflicts)
    dlg.exec_()
    return dlg.solved, dlg.resolvedConflicts

def isGeoGigGeopackage(layer):
    filename = layer.source().split("|")[0]
    ext = filename.split(".")[-1].lower()
    if ext not in ["geopkg", "gpkg"]:
        return False
    con = sqlite3.connect(filename)
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    return "geogig_audited_tables" in tables


class HasLocalChangesError(Exception):
    pass

def checkoutLayer(repo, layername, bbox, ref = None):
    ref = ref or repo.HEAD
    newCommitId = repo.revparse(ref)
    trackedlayers = getTrackingInfoForGeogigLayer(repo.url, layername, newCommitId)
    if trackedlayers:
        trackedlayer = trackedlayers[0]
        try:
            source = trackedlayer.source
            layer = QgsVectorLayer(source, layername, "ogr")
            assert layer.isValid()
        except:
            removeTrackedLayer(trackedlayer.source)
            trackedlayer = None
            filename = layerGeopackageFilename(layername, repo.title, repo.group)
            source = "%s|layername=%s" % (filename, layername)
    else:
        filename = layerGeopackageFilename(layername, repo.title, repo.group)
        source = "%s|layername=%s" % (filename, layername)

    if trackedlayers:
        trackedlayer = trackedlayers[0]
        try:
            layer = layerFromSource(source)
            ret = QMessageBox.warning(iface.mainWindow(), "Layer already exist",
                                      "A layer at this commit is already loaded.\nYou want to create a new one corresponding to this commit?",
                                      QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                return
            filename = layerGeopackageFilename(layername, repo.title, repo.group)
            source = "%s|layername=%s" % (filename, layername)
            repo.checkoutlayer(filename, layername, bbox, ref)
            addTrackedLayer(source, repo.url)
        except WrongLayerSourceException:
            pass

        layer = loadLayerNoCrsDialog(source, layername, "ogr")

        QgsMapLayerRegistry.instance().addMapLayers([layer])
        iface.messageBar().pushMessage("GeoGig", "Layer correctly added to project",
                          level=QgsMessageBar.INFO,
                          duration=5)
    else:
        repo.checkoutlayer(filename, layername, bbox, ref)
        addTrackedLayer(source, repo.url)
        layer = loadLayerNoCrsDialog(source, layername, "ogr")
        QgsMapLayerRegistry.instance().addMapLayers([layer])
        iface.messageBar().pushMessage("GeoGig", "Layer correctly added to project",
                                      level=QgsMessageBar.INFO,
                                      duration=5)
        #currentCommitId = getCommitId(source)

    return layer
