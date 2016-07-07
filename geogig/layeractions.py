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


from geogig import config
from qgis.core import *
from qgis.gui import *
from qgis.utils import iface
from geogig.tools.utils import *
from geogig.tools.layers import namesFromLayer, hasLocalChanges
from geogig.tools.layertracking import *
from geogig.gui.dialogs.importdialog import ImportDialog
from geogig.gui.dialogs.historyviewer import HistoryViewerDialog
from geogig.gui.dialogs.userconfigdialog import *
from PyQt4 import QtGui
from geogig.tools.gpkgsync import syncLayer, changeVersionForLayer
from geogigwebapi import repository
from geogigwebapi.repository import Repository
from geogig.gui.dialogs.localdiffviewerdialog import LocalDiffViewerDialog
from geogig.tools.gpkgsync import getCommitId
from geogig.repowatcher import repoWatcher
from geogig.gui.dialogs.geogigref import RefDialog


def setAsRepoLayer(layer):
    removeLayerActions(layer)
    removeAction = QtGui.QAction(u"Remove layer from repository", config.iface.legendInterface())
    removeAction.triggered.connect(lambda: removeLayer(layer))
    config.iface.legendInterface().addLegendLayerAction(removeAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerAction(removeAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(removeAction, layer)
    syncAction = QtGui.QAction(u"Sync layer with repository branch...", config.iface.legendInterface())
    syncAction.triggered.connect(lambda: syncLayer(layer))
    config.iface.legendInterface().addLegendLayerAction(syncAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(syncAction, layer)
    changeVersionAction = QtGui.QAction(u"Change to a different version...", config.iface.legendInterface())
    changeVersionAction.triggered.connect(lambda: changeVersion(layer))
    config.iface.legendInterface().addLegendLayerAction(changeVersionAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(changeVersionAction, layer)
    changesAction = QtGui.QAction(u"Show local changes", config.iface.legendInterface())
    changesAction.triggered.connect(lambda: showLocalChanges(layer))
    config.iface.legendInterface().addLegendLayerAction(changesAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(changesAction, layer)
    revertAction = QtGui.QAction(u"Revert local changes", config.iface.legendInterface())
    revertAction.triggered.connect(lambda: revertLocalChanges(layer))
    config.iface.legendInterface().addLegendLayerAction(revertAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(revertAction, layer)
    layer.geogigActions = [removeAction, syncAction, changeVersionAction, changesAction, revertAction]

def setAsNonRepoLayer(layer):
    removeLayerActions(layer)
    action = QtGui.QAction(u"Add layer to Repository...", config.iface.legendInterface())
    action.triggered.connect(lambda: addLayer(layer))
    config.iface.legendInterface().addLegendLayerAction(action, u"GeoGig", u"id2", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(action, layer)
    layer.geogigActions = [action]

def removeLayerActions(layer):
    try:
        for action in layer.geogigActions:
            config.iface.legendInterface().removeLegendLayerAction(action)
        layer.geogigActions = []
    except AttributeError:
        pass

def changeVersion(layer):
    if hasLocalChanges(layer):
        QtGui.QMessageBox.warning(config.iface.mainWindow(), 'Cannot change version',
                "There are local changes that would be overwritten.\n"
                "Revert them before changing version.",
                QtGui.QMessageBox.Ok)
    else:
        tracking = getTrackingInfo(layer)
        repo = Repository(tracking.repoUrl)
        dlg = RefDialog(repo)
        dlg.exec_()
        if dlg.ref is not None:
            repo.checkoutlayer(tracking.geopkg, tracking.layername, None, dlg.ref)
            config.iface.messageBar().pushMessage("GeoGig", "Layer has been updated to version %s" % dlg.ref.commitid,
                                                      level=QgsMessageBar.INFO)
            layer.reload()
            layer.triggerRepaint()

def addLayer(layer):
    if not layer.source().lower().split("|")[0].split(".")[-1] in ["geopkg", "gpkg"]:
        QtGui.QMessageBox.warning(config.iface.mainWindow(), 'Cannot add layer',
                "Only geopackage layers are supported at the moment",
                QtGui.QMessageBox.Ok)
        return
    repos = repository.repos
    if repos:
        dlg = ImportDialog(config.iface.mainWindow(), layer = layer)
        dlg.exec_()
        if dlg.ok:
            setAsRepoLayer(layer)
            repoWatcher.repoChanged.emit(dlg.repo)

    else:
        QtGui.QMessageBox.warning(config.iface.mainWindow(), 'Cannot add layer',
                "No local repositories were found",
                QtGui.QMessageBox.Ok)



def revertLocalChanges(layer):
    if hasLocalChanges(layer):
        tracking = getTrackingInfo(layer)
        repo = Repository(tracking.repoUrl)
        commitid = getCommitId(layer)
        repo.checkoutlayer(tracking.geopkg, tracking.layername, None, commitid)
        config.iface.messageBar().pushMessage("GeoGig", "Local changes have been discarded",
                                                      level=QgsMessageBar.INFO)
    else:
        config.iface.messageBar().pushMessage("GeoGig", "No local changes were found",
                                                      level=QgsMessageBar.INFO)

def showLocalChanges(layer):
    dlg = LocalDiffViewerDialog(iface.mainWindow(), layer)
    dlg.exec_()

def removeLayer(layer):
    ret = QtGui.QMessageBox.warning(config.iface.mainWindow(), "Delete layer",
                        "Are you sure you want to delete this layer?",
                        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                        QtGui.QMessageBox.Yes);
    if ret == QtGui.QMessageBox.No:
        return
    tracking = getTrackingInfo(layer)
    repo = Repository(tracking.repoUrl)
    repo.removetree(tracking.layername)

    #TODO remove triggers from layer

    removeTrackedLayer(layer)
    config.iface.messageBar().pushMessage("Layer correctly removed from repository",
                                           level = QgsMessageBar.INFO, duration = 4)
    setAsNonRepoLayer(layer)
    repoWatcher.repoChanged.emit(repo)


