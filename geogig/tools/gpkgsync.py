import sqlite3
from geogig.geogigwebapi.repository import Repository
from geogig.gui.dialogs.conflictdialog import ConflictDialog
from qgis.core import *
from geogig.tools.layertracking import getTrackingInfo
from PyQt4 import QtGui
from qgis.utils import iface
from geogig.geogigwebapi.diff import LocalDiff
from geogig import config
from geogig.gui.dialogs.userconfigdialog import UserConfigDialog
from geogig.tools.layertracking import setRef

INSERT, UPDATE, DELETE  = 1, 2, 3

def syncLayer(layer):
    filename, layername = layer.source().split("|")
    layername = layername.split("=")[-1]
    con = sqlite3.connect(filename)
    cursor = con.cursor()
    tracking = getTrackingInfo(layer)
    repo = Repository(tracking.repoUrl)
    commitid =  repo.revparse(repo.HEAD)
    local = _localChanges(cursor, layername, layer)
    remote = {d.path.split("/")[-1]:d for d in _remoteChanges(cursor, repo, layername)}
    conflicts = {}
    #TODO consider the case of a feature being edited in one part an deleted in the other
    for fid in local:
        if fid in remote:
            conflicts[fid] = (local[fid].newfeature, remote[fid])
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
            pass
        elif solved == ConflictDialog.THEIRS:
            pass
        elif solved == ConflictDialog.MANUAL:

            updateLocalVersionAfterConflicts(resolvedConflicts, layer, layername, cursor)
            syncLayer(layer)
    else:

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
            else:
                return

        applyRemoteChanges(remote, commitid)
        pushLocalChanges(repo, filename, layer, layername, cursor)

        layer.reload()
        layer.triggerRepaint()

        cursor.close()
        con.commit()

def pushLocalChanges(repo, filename, layer, layername, cursor):
    #TODO push changes
    cursor.execute("DELETE FROM %s_audit;" % layername)
    commitid =  repo.revparse(repo.HEAD)
    cursor.execute("UPDATE geogig_audited_tables SET root_tree_id='%s' WHERE table_name='%s'" % (commitid, layername))
    setRef(layer, commitid)

def applyRemoteChanges(remote, commitid, layer, layername, cursor):
    cursor.execute("UPDATE geogig_audited_tables SET root_tree_id='%s' WHERE table_name='%s'" % (commitid, layername))
    setRef(layer, commitid)
    #TODO complete this

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

def localChanges(layer):
    filename, layername = layer.source().split("|")
    layername = layername.split("=")[-1]
    con = sqlite3.connect(filename)
    cursor = con.cursor()
    return _localChanges(cursor, layername, layer)

def getFidColName(cursor, layername):
    tableInfo = cursor.execute("PRAGMA table_info('%s');" % layername)
    for col in tableInfo:
        if col[-1] == 1:
            return col[1]

def _localChanges(cursor, layername, layer):
    attributes = [v[1] for v in cursor.execute("PRAGMA table_info('%s');" % layername)]
    fidColName = getFidColName(cursor, layername)
    cursor.execute("SELECT * FROM %s_audit;" % layername)
    changes = cursor.fetchall()
    changesdict = {}
    tracking = getTrackingInfo(layer)
    repo = Repository(tracking.repoUrl)
    cursor.execute("SELECT root_tree_id FROM geogig_audited_tables WHERE table_name='%s';" % layername)
    commitid = cursor.fetchone()[0]
    for c in changes:
        featurechanges = {attr: c[attributes.index(attr)] for attr in [f.name() for f in layer.pendingFields()]}
        path = str(c[attributes.index(fidColName)])
        try:
            request = QgsFeatureRequest()
            request.setFilterFid(int(path.split("/")[-1]))
            feature = layer.getFeatures(request).next()
            featurechanges["the_geom"] = feature.geometry().exportToWkt()
        except:
            featurechanges["the_geom"] = None
        changesdict[path] = LocalDiff(layername, path, repo, featurechanges, commitid, c[-1])
    return changesdict


def _remoteChanges(cursor, repo, layername):
    cursor.execute("SELECT root_tree_id FROM geogig_audited_tables WHERE table_name='%s';" % layername)
    commitid = cursor.fetchone()[0]
    changes = repo.diff(commitid, repo.HEAD, layername)
    return changes


def solveConflicts(conflicts, layername):
    dlg = ConflictDialog(conflicts, layername)
    dlg.exec_()
    return dlg.solved, dlg.resolvedConflicts


def addGeoGigTablesAndTriggers(layer):
    pass


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