
from geogig import config
from qgis.core import *
from qgis.gui import *
from qgis.utils import iface
from geogig.tools.utils import *
from geogig.tools.layertracking import *
from geogig.gui.dialogs.importdialog import ImportDialog
from geogig.gui.dialogs.historyviewer import HistoryViewerDialog
from geogig.gui.dialogs.commitdialog import CommitDialog
from geogig.gui.dialogs.userconfigdialog import *
from geogig.tools.exporter import exportVectorLayer
from PyQt4 import QtGui
from PyQt4.QtCore import pyqtSignal, QObject
from geogig.tools.gpkgsync import syncLayer, localChanges
from geogigwebapi import repository
from geogigwebapi.repository import Repository
from geogig.gui.dialogs.localdiffviewerdialog import LocalDiffViewerDialog


class RepoWatcher(QObject):

    repoChanged = pyqtSignal(object)

repoWatcher = RepoWatcher()

def setAsRepoLayer(layer):
    removeLayerActions(layer)
    removeAction = QtGui.QAction(u"Remove layer from repository", config.iface.legendInterface())
    config.iface.legendInterface().addLegendLayerAction(removeAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(removeAction, layer)
    removeAction.triggered.connect(lambda: removeLayer(layer))
    syncAction = QtGui.QAction(u"Sync layer with repository", config.iface.legendInterface())
    config.iface.legendInterface().addLegendLayerAction(syncAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(syncAction, layer)
    syncAction.triggered.connect(lambda: syncLayer(layer))
    changesAction = QtGui.QAction(u"Show local changes", config.iface.legendInterface())
    config.iface.legendInterface().addLegendLayerAction(changesAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(changesAction, layer)
    changesAction.triggered.connect(lambda: showLocalChanges(layer))
    revertAction = QtGui.QAction(u"Revert local changes", config.iface.legendInterface())
    config.iface.legendInterface().addLegendLayerAction(revertAction, u"GeoGig", u"id1", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(revertAction, layer)
    revertAction.triggered.connect(lambda: revertLocalChanges(layer))
    layer.geogigActions = [removeAction, syncAction, changesAction, revertAction]

def setAsNonRepoLayer(layer):
    removeLayerActions(layer)
    action = QtGui.QAction(u"Add layer to Repository...", config.iface.legendInterface())
    config.iface.legendInterface().addLegendLayerAction(action, u"GeoGig", u"id2", QgsMapLayer.VectorLayer, False)
    config.iface.legendInterface().addLegendLayerActionForLayer(action, layer)
    action.triggered.connect(lambda: addLayer(layer))
    layer.geogigActions = [action]

def removeLayerActions(layer):
    try:
        for action in layer.geogigActions:
            config.iface.legendInterface().removeLegendLayerAction(action)
        layer.geogigActions = []
    except AttributeError:
        pass


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
    pass

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


