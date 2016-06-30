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

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import sqlite3
from geogig.geogigwebapi.repository import Repository
from geogig.gui.dialogs.geogigref import RefDialog
from geogig.gui.dialogs.conflictdialog import ConflictDialog
from geogig.gui.dialogs.commitdialog import CommitDialog
from qgis.core import *
from qgis.gui import *
from geogig.tools.layertracking import getTrackingInfo
from PyQt4 import QtGui
from qgis.utils import iface
from geogig.geogigwebapi.diff import LocalDiff
from geogig.geogigwebapi.repository import GeoGigException
from geogig import config
from geogig.gui.dialogs.userconfigdialog import UserConfigDialog
from geogig.tools.layers import namesFromLayer
from geogig.tools.utils import tempFilename


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
    dlg = CommitDialog(repo, changes)
    dlg.exec_()
    if dlg.branch is None:
        return
    if changes:
        user, email = getUserInfo()
        if user is None:
            return

        if dlg.branch not in repo.branches():
            commitId = getCommitId(layer)
            repo.createbranch(commitId, dlg.branch)
        mergeCommitId, importCommitId, conflicts, featureIds = repo.importgeopkg(layer, dlg.branch, dlg.message, user, email)

        if conflicts:
            ret = QtGui.QMessageBox.warning(iface.mainWindow(), "Error while syncing",
                                      "There are conflicts between local and remote changes.\n"
                                      "Do you want to continue and fix them?",
                                      QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if ret == QtGui.QMessageBox.No:
                return
            solved, resolvedConflicts = solveConflicts(conflicts, layername)
            if solved == ConflictDialog.UNSOLVED:
                cursor.close()
                return
            elif solved == ConflictDialog.OURS:
                pass#TODO
            elif solved == ConflictDialog.THEIRS:
                pass#TODO
            elif solved == ConflictDialog.MANUAL:
                pass#TODO

        updateFeatureIds(repo, layer, featureIds)
        applyLayerChanges(repo, layer, importCommitId, mergeCommitId)
    else:
        commitId = getCommitId(layer)
        headCommitId = repo.revparse(dlg.branch)
        applyLayerChanges(repo, layer, commitId, headCommitId)

    layer.reload()
    layer.triggerRepaint()

    iface.messageBar().pushMessage("GeoGig", "Layer has been correctly synchronized",
                                                  level=QgsMessageBar.INFO)


def changeVersionForLayer(layer):
    tracking = getTrackingInfo(layer)
    repo = Repository(tracking.repoUrl)
    currentCommitId = getCommitId(layer)
    dlg = RefDialog(repo)
    dlg.exec_()
    if dlg.ref is not None:
        applyLayerChanges(repo, layer, currentCommitId, dlg.ref.commitid)
        layer.reload()
        layer.triggerRepaint()

def updateFeatureIds(repo, layer, featureIds):
    filename, layername = namesFromLayer(layer)
    con = sqlite3.connect(filename)
    cursor = con.cursor()
    for ids in featureIds:
        cursor.execute('INSERT INTO "%s_fids" VALUES ("%s", "%s")' % (layername, ids[0], ids[1]))

def gpkgfidFromGeogigfid(cursor, layername, geogigfid):
    cursor.execute("SELECT gpkg_fid FROM %s_fids WHERE geogig_fid='%s';" % (layername, geogigfid))
    gpkgfid = cursor.fetchone()[0]
    return gpkgfid

def applyLayerChanges(repo, layer, beforeCommitId, afterCommitId):
    filename, layername = namesFromLayer(layer)
    changesFilename = tempFilename("gpkg")
    print changesFilename
    repo.exportdiff(layername, beforeCommitId, afterCommitId, changesFilename)

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
        vals = ",".join(["%s=?" % k for k in attrs.keys()])
        cursor.execute("UPDATE %s SET %s WHERE fid='%s'" % (layername, vals, gpkgfid), attrs.values())

    changesCursor.execute("SELECT * FROM %s_changes WHERE audit_op=1;" % layername)
    added = changesCursor.fetchall()
    for a in added:
        geogigfid = a[0]
        changesGpkgfid = gpkgfidFromGeogigfid(changesCursor, layername, geogigfid)
        changesCursor.execute("SELECT * FROM %s WHERE fid='%s';" % (layername, changesGpkgfid))
        featureRow = changesCursor.fetchone()
        attrs = {attr: featureRow[attributes.index(attr)] for attr in attrnames}
        cols = ', '.join('"%s"' % col for col in attrs.keys())
        vals = ', '.join('?' for val in attrs.values())
        cursor.execute('INSERT INTO "%s" (%s) VALUES (%s)' % (layername, cols, vals), attrs.values())
        gpkgfid = cursor.lastrowid
        cursor.execute('INSERT INTO "%s_fids" VALUES ("%s", "%s")' % (layername, gpkgfid, geogigfid))

    changesCursor.execute("SELECT * FROM %s_changes WHERE audit_op=3;" % layername)
    removed = changesCursor.fetchall()
    for r in removed:
        geogigfid = r[0]
        gpkgfid = gpkgfidFromGeogigfid(cursor, layername, geogigfid)
        cursor.execute("DELETE FROM %s WHERE fid='%s'" % (layername, gpkgfid))
        cursor.execute("DELETE FROM %s_fids WHERE gpkg_fid='%s'" % (layername, gpkgfid))

    cursor.execute("DELETE FROM %s_audit;" % layername)

    cursor.execute("UPDATE geogig_audited_tables SET commit_id='%s' WHERE table_name='%s'" % (afterCommitId, layername))

    cursor.close()
    changesCursor.close()
    con.commit()
    con.close()
    changesCon.close()


def updateLocalVersionAfterConflicts(solved, layer, layername, cursor):
    #TODO: write geoms as WKB
    def quote(val):
        if isinstance(val, basestring):
            return "'%s'" % val
        else:
            return str(val)
    tableInfo = cursor.execute("PRAGMA table_info('%s');" % layername)
    for col in tableInfo:
        if col[-1] == 1:
            pkName = col[1]
    geomField = None
    for path, values in solved.iteritems():
        request = QgsFeatureRequest()
        request.setFilterFid(int(path))
        geom = None
        if geomField is not None:
            geom = QgsGeometry.fromWkt(values[geomField])
        else:
            for k,v in values.iteritems():
                try:
                    geom = QgsGeometry.fromWkt(v)
                    if geom is not None:
                        geomField = k
                        break
                except:
                    pass

        layer.dataProvider().changeAttributeValues({int(path): values})
        layer.dataProvider().changeGeometryValues({ int(path): geom})

        svalues = ",".join(["%s=%s"] % (k,quote(v)) for k,v in values.iteritems())
        sql = "UPDATE %s_audit SET %s WHERE %s='%s'" % (layername, svalues, pkName, path)
        cursor.execute(sql)

def getCommitId(layer):
    filename, layername = namesFromLayer(layer)
    con = sqlite3.connect(filename)
    cursor = con.cursor()
    cursor.execute("SELECT commit_id FROM geogig_audited_tables WHERE table_name='%s';" % layername)
    commitid = cursor.fetchone()[0]
    cursor.close()
    con.close()
    return commitid

def solveConflicts(conflicts, layername):
    dlg = ConflictDialog(conflicts, layername)
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

def getUserInfo():
    user = config.getConfigValue(config.GENERAL, config.USERNAME).strip()
    email = config.getConfigValue(config.GENERAL, config.EMAIL).strip()
    if not (user and email):
        configdlg = UserConfigDialog(config.iface.mainWindow())
        configdlg.exec_()
        if configdlg.user is not None:
            user = configdlg.user
            email = configdlg.email
            config.setConfigValue(config.GENERAL, config.USERNAME, user)
            config.setConfigValue(config.GENERAL, config.EMAIL, email)
            return user, email
        else:
            return None
    return user, email
