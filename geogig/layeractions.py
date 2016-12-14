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
from __future__ import absolute_import

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from functools import partial

from qgis.PyQt.QtWidgets import QAction, QMessageBox

from qgis.core import QgsMapLayer
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
from geogig.gui.dialogs.geogigref import CommitSelectDialog
from geogig.gui.dialogs import commitdialog
from geogig.gui.dialogs.historyviewer import HistoryViewerDialog

from geogig.tools.gpkgsync import syncLayer, getCommitId, applyLayerChanges
from geogig.tools.layers import namesFromLayer, hasLocalChanges
from geogig.tools.layertracking import getTrackingInfo


def setAsRepoLayer(layer):
    removeLayerActions(layer)
    canConnect = addInfoActions(layer)
    separatorAction = QAction("", config.iface.legendInterface())
    separatorAction.setSeparator(True)
    config.iface.legendInterface().addLegendLayerAction(separatorAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(separatorAction, layer)
    syncAction = QAction(u"Sync layer with repository branch...", config.iface.legendInterface())
    syncAction.triggered.connect(partial(syncLayer, layer))
    config.iface.legendInterface().addLegendLayerAction(syncAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(syncAction, layer)
    changeVersionAction = QAction(u"Change to a different version...", config.iface.legendInterface())
    changeVersionAction.triggered.connect(partial(changeVersion, layer))
    config.iface.legendInterface().addLegendLayerAction(changeVersionAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(changeVersionAction, layer)
    revertChangeAction = QAction(u"Revert changes introduced by a version...", config.iface.legendInterface())
    revertChangeAction.triggered.connect(partial(revertChange, layer))
    config.iface.legendInterface().addLegendLayerAction(revertChangeAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(revertChangeAction, layer)
    changesAction = QAction(u"Show local changes...", config.iface.legendInterface())
    changesAction.triggered.connect(partial(showLocalChanges, layer))
    config.iface.legendInterface().addLegendLayerAction(changesAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(changesAction, layer)
    revertAction = QAction(u"Revert local changes", config.iface.legendInterface())
    revertAction.triggered.connect(partial(revertLocalChanges, layer))
    config.iface.legendInterface().addLegendLayerAction(revertAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(revertAction, layer)
    layer.geogigActions = [separatorAction, syncAction, changeVersionAction, revertChangeAction, changesAction, revertAction]
    for action in layer.geogigActions:
        action.setEnabled(canConnect)
    if not canConnect:
        refreshAction = QAction(u"Retry connecting...", config.iface.legendInterface())
        refreshAction.triggered.connect(lambda: setAsRepoLayer(layer))
        config.iface.legendInterface().addLegendLayerAction(refreshAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
        config.iface.legendInterface().addLegendLayerActionForLayer(refreshAction, layer)
        layer.geogigActions.append(refreshAction)
    layer.geogigActions.extend(layer.infoActions)
    repoWatcher.layerUpdated.connect(updateInfoActions)

def addInfoActions(layer):
    commitId = getCommitId(layer)
    tracking = getTrackingInfo(layer)
    repo = Repository(tracking.repoUrl)
    layer.infoActions = []
    try:
        commit = Commit.fromref(repo, commitId)
        messageAction = QAction("Message: '%s'" % commit.message.splitlines()[0], config.iface.legendInterface())
        f = messageAction.font();
        f.setBold(True);
        messageAction.setFont(f);
        config.iface.legendInterface().addLegendLayerAction(messageAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
        config.iface.legendInterface().addLegendLayerActionForLayer(messageAction, layer)
        layer.infoActions.append(messageAction)
    except:
        messageAction = QAction("Error: Cannot connect with repository", config.iface.legendInterface())
        f = messageAction.font();
        f.setBold(True);
        messageAction.setFont(f);
        config.iface.legendInterface().addLegendLayerAction(messageAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
        config.iface.legendInterface().addLegendLayerActionForLayer(messageAction, layer)
        layer.infoActions.append(messageAction)
        return False
    shaAction = QAction("Version ID: %s" % commitId, config.iface.legendInterface())
    f = shaAction.font();
    f.setBold(True);
    shaAction.setFont(f);
    config.iface.legendInterface().addLegendLayerAction(shaAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(shaAction, layer)
    layer.infoActions.append(shaAction)
    return True

def updateInfoActions(layer):
    setAsRepoLayer(layer)

def setAsNonRepoLayer(layer):
    removeLayerActions(layer)
    action = QAction(u"Add layer to Repository...", config.iface.legendInterface())
    action.triggered.connect(partial(addLayer, layer))
    if layer.type() == QgsMapLayer.RasterLayer or layer.storageType() != 'GPKG':
        action.setEnabled(False)
    config.iface.legendInterface().addLegendLayerAction(action, u"GeoGig", u"id2", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(action, layer)
    layer.geogigActions = [action]
    try:
        repoWatcher.layerUpdated.disconnect(updateInfoActions)
    except:
        pass #In case it is a layer that was never a repo layer

def removeLayerActions(layer):
    try:
        for action in layer.geogigActions:
            config.iface.legendInterface().removeLegendLayerAction(action)
        layer.geogigActions = []
        layer.infoActions = []
    except AttributeError:
        pass

def revertChange(layer):
    tracking = getTrackingInfo(layer)
    repo = Repository(tracking.repoUrl)
    currentCommitId = getCommitId(layer)
    filename, layername = namesFromLayer(layer)
    dlg = CommitSelectDialog(repo, currentCommitId, layername)
    dlg.exec_()
    if dlg.ref is not None:
        #TODO check that selected commit is in history line
        applyLayerChanges(repo, layer, dlg.ref.commitid, dlg.ref.parent.commitid, False)
        layer.reload()
        layer.triggerRepaint()
        config.iface.messageBar().pushMessage("GeoGig", "Version changes have been reverted in local layer",
                                                      level=QgsMessageBar.INFO,
                                                      duration=5)
        commitdialog.suggestedMessage = "Reverted changes from version %s [%s] " % (dlg.ref.commitid, dlg.ref.message)

def changeVersion(layer):
    if hasLocalChanges(layer):
        QMessageBox.warning(config.iface.mainWindow(), 'Cannot change version',
                "There are local changes that would be overwritten.\n"
                "Revert them before changing version.",
                QMessageBox.Ok)
    else:
        tracking = getTrackingInfo(layer)
        repo = Repository(tracking.repoUrl)
        dlg = HistoryViewerDialog(repo, tracking.layername)
        dlg.exec_()
        if dlg.ref is not None:
            layers = repo.trees(dlg.ref)
            if tracking.layername not in layers:
                QMessageBox.warning(config.iface.mainWindow(), 'Cannot change version',
                "The selected version does not contain the specified layer.",
                QMessageBox.Ok)
            else:
                repo.checkoutlayer(tracking.geopkg, tracking.layername, None, dlg.ref)
                config.iface.messageBar().pushMessage("GeoGig", "Layer has been updated to version %s" % dlg.ref,
                                                       level=QgsMessageBar.INFO,
                                                       duration=5)
                layer.reload()
                layer.triggerRepaint()
                repoWatcher.layerUpdated.emit(layer)
                repoWatcher.repoChanged.emit(repo)

def addLayer(layer):
    if not layer.source().lower().split("|")[0].split(".")[-1] in ["geopkg", "gpkg"]:
        QMessageBox.warning(config.iface.mainWindow(), 'Cannot add layer',
                "Only geopackage layers are supported at the moment",
                QMessageBox.Ok)
        return
    repos = repository.repos
    if repos:
        dlg = ImportDialog(config.iface.mainWindow(), layer = layer)
        dlg.exec_()
        if dlg.ok:
            setAsRepoLayer(layer)
            repoWatcher.repoChanged.emit(dlg.repo)

    else:
        QMessageBox.warning(config.iface.mainWindow(), 'Cannot add layer',
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

