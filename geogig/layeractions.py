# -*- coding: utf-8 -*-

"""
***************************************************************************
    layeractions.py
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

from functools import partial

from qgis.PyQt.QtWidgets import QAction, QMessageBox

from qgis.core import QgsMapLayer, QgsVectorLayer ,QgsMessageLog
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from geogig import config
from geogig.repowatcher import repoWatcher

from .geogigwebapi import repository
from .geogigwebapi.repository import Repository
from .geogigwebapi.commit import Commit

from geogig.gui.dialogs.importdialog import ImportDialog
from geogig.gui.dialogs.userconfigdialog import UserConfigDialog
from geogig.gui.dialogs.localdiffviewerdialog import LocalDiffViewerDialog
from geogig.gui.dialogs import commitdialog
from geogig.gui.dialogs.historyviewer import HistoryViewerDialog

from geogig.tools.gpkgsync import syncLayer, getCommitId, applyLayerChanges
from geogig.tools.layers import namesFromLayer, hasLocalChanges
from geogig.tools.layertracking import getTrackingInfo

_actions = {}
_infoActions = {}

def setAsRepoLayer(layer):
    removeLayerActions(layer)
    canConnect = addInfoActions(layer)
    separatorAction = QAction("", config.iface.mainWindow())
    separatorAction.setSeparator(True)
    config.iface.addCustomActionForLayerType(separatorAction, "GeoGig", QgsMapLayer.VectorLayer, False)
    config.iface.addCustomActionForLayer(separatorAction, layer)
    syncAction = QAction("Sync layer with branch...", config.iface.mainWindow())
    syncAction.triggered.connect(partial(syncLayer, layer))
    config.iface.addCustomActionForLayerType(syncAction, "GeoGig", QgsMapLayer.VectorLayer, False)
    config.iface.addCustomActionForLayer(syncAction, layer)
    changeVersionAction = QAction("Change to a different commit...", config.iface.mainWindow())
    changeVersionAction.triggered.connect(partial(changeVersion, layer))
    config.iface.addCustomActionForLayerType(changeVersionAction, "GeoGig", QgsMapLayer.VectorLayer, False)
    config.iface.addCustomActionForLayer(changeVersionAction, layer)
    revertChangeAction = QAction("Revert commit...", config.iface.mainWindow())
    revertChangeAction.triggered.connect(partial(revertChange, layer))
    config.iface.addCustomActionForLayerType(revertChangeAction, "GeoGig", QgsMapLayer.VectorLayer, False)
    config.iface.addCustomActionForLayer(revertChangeAction, layer)
    changesAction = QAction("Show local changes...", config.iface.mainWindow())
    changesAction.triggered.connect(partial(showLocalChanges, layer))
    config.iface.addCustomActionForLayerType(changesAction, "GeoGig", QgsMapLayer.VectorLayer, False)
    config.iface.addCustomActionForLayer(changesAction, layer)
    revertAction = QAction("Revert local changes", config.iface.mainWindow())
    revertAction.triggered.connect(partial(revertLocalChanges, layer))
    config.iface.addCustomActionForLayerType(revertAction, "GeoGig", QgsMapLayer.VectorLayer, False)
    config.iface.addCustomActionForLayer(revertAction, layer)
    _actions[layer.id()] = [separatorAction, syncAction, changeVersionAction, revertChangeAction, changesAction, revertAction]
    for action in _actions[layer.id()]:
        action.setEnabled(canConnect)
    if not canConnect:
        refreshAction = QAction("Retry connecting...", config.iface.mainWindow())
        refreshAction.triggered.connect(lambda: setAsRepoLayer(layer))
        config.iface.addCustomActionForLayerType(refreshAction, "GeoGig", QgsMapLayer.VectorLayer, False)
        config.iface.addCustomActionForLayer(refreshAction, layer)
        _actions[layer.id()].append(refreshAction)
    _actions[layer.id()].extend(_infoActions[layer.id()])
    repoWatcher.layerUpdated.connect(updateInfoActions)

def addInfoActions(layer):
    commitId = getCommitId(layer)
    tracking = getTrackingInfo(layer)
    repo = Repository(tracking.repoUrl)
    _infoActions[layer.id()] = []
    try:
        commit = Commit.fromref(repo, commitId)
        messageAction = QAction("Message: '%s'" % commit.message.splitlines()[0], config.iface.mainWindow())
        f = messageAction.font()
        f.setBold(True)
        messageAction.setFont(f)
        config.iface.addCustomActionForLayerType(messageAction, "GeoGig", QgsMapLayer.VectorLayer, False)
        config.iface.addCustomActionForLayer(messageAction, layer)
        _infoActions[layer.id()].append(messageAction)
    except Exception as e:
        QgsMessageLog.logMessage("Cannot connect to server when creating GeoGig layer context:\n %s" % str(e), level=QgsMessageLog.WARNING)
        messageAction = QAction("Error: Cannot connect with repository", config.iface.mainWindow())
        f = messageAction.font()
        f.setBold(True)
        messageAction.setFont(f)
        config.iface.addCustomActionForLayerType(messageAction, "GeoGig", QgsMapLayer.VectorLayer, False)
        config.iface.addCustomActionForLayer(messageAction, layer)
        _infoActions[layer.id()].append(messageAction)
        return False
    shaAction = QAction("Commit ID: %s" % commitId, config.iface.mainWindow())
    f = shaAction.font()
    f.setBold(True)
    shaAction.setFont(f)
    config.iface.addCustomActionForLayerType(shaAction, "GeoGig", QgsMapLayer.VectorLayer, False)
    config.iface.addCustomActionForLayer(shaAction, layer)
    _infoActions[layer.id()].append(shaAction)
    return True

def updateInfoActions(layer):
    setAsRepoLayer(layer)

def setAsNonRepoLayer(layer):
    removeLayerActions(layer)
    action = QAction("Import to GeoGig...", config.iface.mainWindow())
    action.triggered.connect(partial(addLayer, layer))
    if layer.type() != QgsMapLayer.VectorLayer:
        action.setEnabled(False)
    config.iface.addCustomActionForLayerType(action, "GeoGig", QgsMapLayer.VectorLayer, False)
    config.iface.addCustomActionForLayer(action, layer)
    _actions[layer.id()] = [action]
    try:
        repoWatcher.layerUpdated.disconnect(updateInfoActions)
    except:
        pass #In case it is a layer that was never a repo layer

def removeLayerActions(layer):
    if layer is None:
        return
    try:
        for action in _actions[layer.id()]:
            config.iface.removeCustomActionForLayerType(action)
        _actions[layer.id()] = []
        _infoActions[layer.id()] = []
    except KeyError:
        pass

def revertChange(layer):
    if hasLocalChanges(layer):
        QMessageBox.warning(config.iface.mainWindow(), 'Cannot revert commit',
                "The layer has local changes.\n"
                "Revert local changes before reverting a previous commit.",
                QMessageBox.Ok)
        return
    tracking = getTrackingInfo(layer)
    repo = Repository(tracking.repoUrl)
    filename, layername = namesFromLayer(layer)
    from geogig.gui.dialogs.historyviewer import HistoryViewerDialog
    dlg = HistoryViewerDialog(repo, layername, showButtons = True)
    dlg.exec_()
    if dlg.ref is not None:
        #TODO check that selected commit is in history line

        commit = Commit.fromref(repo, dlg.ref)
        # check if we are reverting commit which adds layer to the repo
        if commit.addsLayer():
            QMessageBox.warning(config.iface.mainWindow(), 'Cannot revert commit',
                    "Commits which add layer to the repository can not "
                    "be reverted. Use GeoGig Navigator to remove layer "
                    "from branch.")
            return

        applyLayerChanges(repo, layer, commit.commitid, commit.parent.commitid, False)
        layer.reload()
        layer.triggerRepaint()
        config.iface.messageBar().pushMessage("GeoGig", "Commit changes have been reverted in local layer",
                                                      level=QgsMessageBar.INFO,
                                                      duration=5)
        commitdialog.suggestedMessage = "Reverted changes from commit %s [%s] " % (commit.commitid, commit.message)

def changeVersion(layer):
    if hasLocalChanges(layer):
        QMessageBox.warning(config.iface.mainWindow(), 'Cannot change commit',
                "The layer has local changes that would be overwritten. "
                "Either sync layer with branch or revert local changes "
                "before changing commit.",
                QMessageBox.Ok)
    else:
        tracking = getTrackingInfo(layer)
        repo = Repository(tracking.repoUrl)
        dlg = HistoryViewerDialog(repo, tracking.layername, showButtons = True)
        dlg.exec_()
        if dlg.ref is not None:
            layers = repo.trees(dlg.ref)
            if tracking.layername not in layers:
                QMessageBox.warning(config.iface.mainWindow(), 'Cannot change commit',
                "The selected commit does not contain the specified layer.",
                QMessageBox.Ok)
            else:
                repo.checkoutlayer(tracking.geopkg, tracking.layername, None, dlg.ref)
                config.iface.messageBar().pushMessage("GeoGig", "Layer has been updated to commit %s" % dlg.ref,
                                                       level=QgsMessageBar.INFO,
                                                       duration=5)
                layer.reload()
                layer.triggerRepaint()
                repoWatcher.layerUpdated.emit(layer)
                #repoWatcher.repoChanged.emit(repo)

def addLayer(layer):
    if not isinstance(layer, QgsVectorLayer):
        QMessageBox.warning(config.iface.mainWindow(), 'Cannot import layer',
                "Only vector layers are supported",
                QMessageBox.Ok)
        return

    repos = repository.repos
    if repos:
        dlg = ImportDialog(config.iface.mainWindow(), layer = layer)
        dlg.exec_()
        if dlg.ok:
            #setAsRepoLayer(layer)
            repoWatcher.repoChanged.emit(dlg.repo)

    else:
        QMessageBox.warning(config.iface.mainWindow(), 'Cannot import layer',
                "No repositories were found",
                QMessageBox.Ok)



def revertLocalChanges(layer):
    if hasLocalChanges(layer):
        tracking = getTrackingInfo(layer)
        repo = Repository(tracking.repoUrl)
        commitid = getCommitId(layer)
        repo.checkoutlayer(tracking.geopkg, tracking.layername, None, commitid)
        config.iface.messageBar().pushMessage("GeoGig", "Local changes have been discarded",
                                                      level=QgsMessageBar.INFO,
                                                      duration=5)
        layer.reload()
        layer.triggerRepaint()
    else:
        config.iface.messageBar().pushMessage("GeoGig", "No local changes were found",
                                                      level=QgsMessageBar.INFO,
                                                      duration=5)

def showLocalChanges(layer):
    dlg = LocalDiffViewerDialog(iface.mainWindow(), layer)
    dlg.exec_()

