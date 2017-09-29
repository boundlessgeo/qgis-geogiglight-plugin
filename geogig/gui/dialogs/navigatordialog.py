# -*- coding: utf-8 -*-

"""
***************************************************************************
    navigatordialog.py
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


import os
import sys
import sqlite3
import webbrowser
from collections import defaultdict

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QUrl, QSize, QT_VERSION_STR
from qgis.PyQt.QtGui import QIcon, QMessageBox, QPixmap
from qgis.PyQt.QtWidgets import (QHeaderView,
                                 QVBoxLayout,
                                 QAbstractItemView,
                                 QTreeWidgetItem,
                                 QMessageBox,
                                 QInputDialog,
                                 QLabel,
                                 QHBoxLayout,
                                 QSizePolicy,
                                 QWidget,
                                 QPushButton,
                                 QApplication,
                                 QAction,
                                 QMenu
                                )

from qgis.core import QgsApplication, QgsMessageLog
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from geogig import config
from geogig.repowatcher import repoWatcher

from qgiscommons2.gui import execute
from geogig.gui.dialogs.historyviewer import HistoryViewer
from geogig.gui.dialogs.importdialog import ImportDialog
from geogig.gui.dialogs.geogigserverdialog import GeoGigServerDialog
from geogig.gui.dialogs.remotesdialog import RemotesDialog
from geogig.gui.dialogs.remoterefdialog import RemoteRefDialog
from geogig.gui.dialogs.conflictdialog import ConflictDialog

from geogig.layeractions import setAsRepoLayer, setAsNonRepoLayer, updateInfoActions
from geogig.tools.layers import (WrongLayerSourceException,
                                 formatSource)
from geogig.tools.utils import resourceFile
from geogig.tools.gpkgsync import checkoutLayer, HasLocalChangesError
from geogig.tools.layertracking import (removeTrackedLayer,
                                        getProjectLayerForGeoGigLayer,
                                        removeTrackedForRepo,
                                        isRepoLayer,
                                        getTrackingInfoForGeogigLayer,
                                        getTrackedPathsForRepo
                                       )
from geogig.geogigwebapi import repository
from geogig.geogigwebapi.repository import (GeoGigException, CannotPushException,
                                            readRepos, removeRepo, removeRepoEndpoint,
                                            createRepoAtUrl, addRepoEndpoint, addRepo)
from builtins import zip
from builtins import str
from builtins import range

from qgiscommons2.layers import vectorLayers

qtVersion = int(QT_VERSION_STR.split(".")[0])
pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]

def icon(f):
    return QIcon(os.path.join(pluginPath, "ui", "resources", f))

repoIcon = icon("repository.svg")
branchIcon = icon("branch.svg")
layerIcon = icon('geometry.svg')

WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'navigatordialog.ui'))

class NavigatorDialog(BASE, WIDGET):

    def __init__(self):
        super(NavigatorDialog, self).__init__(None)

        self.currentRepo = None
        self.reposItem = None
        self.setupUi(self)


        self.repoTree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.repoTree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.repoTree.itemSelectionChanged.connect(self.selectionChanged)
        self.repoTree.customContextMenuRequested.connect(self.showPopupMenu)

        self.comboEndpoint.currentIndexChanged.connect(self.fillTree)

        self.btnAddServer.setIcon(icon("add-server.svg"))
        self.btnEditServer.setIcon(icon("edit-server.svg"))
        self.btnDeleteServer.setIcon(icon("delete-server.svg"))
        self.btnAddRepo.setIcon(icon("add-repository.svg"))
        self.btnRefresh.setIcon(icon("refresh.svg"))

        self.btnAddServer.clicked.connect(self.addGeoGigServer)
        self.btnEditServer.clicked.connect(self.editGeoGigServer)
        self.btnDeleteServer.clicked.connect(self.deleteGeoGigServer)
        self.btnAddRepo.clicked.connect(self.createRepo)
        self.btnRefresh.clicked.connect(self.fillTree)

        self._enableOrDisableButtons()

        if qtVersion < 5:
            self.repoTree.header().setResizeMode(0, QHeaderView.Stretch)
            self.repoTree.header().setResizeMode(1, QHeaderView.ResizeToContents)

        self.versionsTree = HistoryViewer()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.addWidget(self.versionsTree)
        self.versionsWidget.setLayout(layout)

        def _repoChanged(repo):
            if self.currentRepo is not None and repo.url == self.currentRepo.url:
                self.updateCurrentRepo(repo)
            for i in range(self.repoTree.topLevelItemCount()):
                item = self.repoTree.topLevelItem(i)
                if item.repo == repo:
                    item.refreshContent()
        repoWatcher.repoChanged.connect(_repoChanged)

        self.updateNavigator()

        self.repoTree.itemExpanded.connect(self._itemExpanded)


    def showPopupMenu(self, point):
        item = self.repoTree.currentItem()
        self.menu = item.menu()
        point = self.mapToGlobal(point)
        self.menu.popup(point)

    def updateNavigator(self):
        self.fillCombo()
        self.updateCurrentRepo(None)
        #self.checkButtons()

    def _itemExpanded(self, item):
        if item is not None and isinstance(item, (RepoItem, BranchItem)):
            item.populate()

    def _checkoutLayer(self, layername, bbox):
        checkoutLayer(self.currentRepo, layername, bbox)

    def fillCombo(self):
        self.comboEndpoint.clear()
        groups = repository.repoEndpoints.keys()
        #groups.insert(0, "Select a GeoGig server")
        self.comboEndpoint.addItems(groups)

    def fillTree(self):
        groupName = self.comboEndpoint.currentText()
        #repository.refreshEndpoint(groupName)
        self.btnAddRepo.setEnabled(groupName in repository.availableRepoEndpoints)
        self.updateCurrentRepo(None)
        self.repoTree.clear()

        groupRepos = repository.endpointRepos(groupName)
        for repo in groupRepos:
            try:
                item = RepoItem(self.repoTree, repo)
                self.repoTree.addTopLevelItem(item)
            except:
                #TODO: inform of failed repos
                pass

        self.repoTree.sortItems(0, Qt.AscendingOrder)

    def addLayer(self):
        layers = [layer for layer in vectorLayers()
                        if layer.source().lower().split("|")[0].split(".")[-1] in["gpkg", "geopkg"]
                        and not isRepoLayer(layer)]
        if layers:
            dlg = ImportDialog(self, repo = self.currentRepo)
            dlg.exec_()
            if dlg.ok:
                #self.versionsTree.updateCurrentBranchItem()
                setAsRepoLayer(dlg.layer)
                repoWatcher.repoChanged.emit(self.currentRepo)
        else:
            QMessageBox.warning(self, 'Cannot add layer',
                "No suitable layers can be found in your current QGIS project.\n"
                "Only Geopackage layers that do not already belong to a repository can be added.",
                QMessageBox.Ok)


    def selectionChanged(self):
        items = self.repoTree.selectedItems()
        if items:
            self.updateCurrentRepo(items[0].repo)
        else:
            self.updateCurrentRepo(None)

    def updateCurrentRepo(self, repo):
        def _update():
            self.currentRepo = repo
            self.versionsTree.updateContent(repo)
        try:
            self.repoTree.setSelectionMode(QAbstractItemView.NoSelection)
            self.repoTree.blockSignals(True)
            execute(_update)
        finally:
            self.repoTree.setSelectionMode(QAbstractItemView.SingleSelection)
            self.repoTree.blockSignals(False)

    def createRepo(self):
        name, ok = QInputDialog.getText(self, 'Create repository',
                                              'Enter the repository name:')
        if ok:
            group = self.comboEndpoint.currentText()
            url = repository.repoEndpoints[group]
            try:
                repo = execute(lambda: createRepoAtUrl(url, group, name))
            except GeoGigException as e:
                config.iface.messageBar().pushMessage("Error", str(e),
                               level=QgsMessageBar.CRITICAL,
                               duration=5)
                return
            item = RepoItem(self.repoTree, repo)
            addRepo(repo)
            self.repoTree.addTopLevelItem(item)
            config.iface.messageBar().pushMessage("Create repository", "Repository correctly created",
                                           level=QgsMessageBar.INFO,
                                           duration=5)

    def editGeoGigServer(self):
        group = self.comboEndpoint.currentText()
        dlg = GeoGigServerDialog(repository.repoEndpoints[group], group)
        dlg.setWindowTitle("Edit GeoGig server")
        dlg.exec_()
        if dlg.title is not None:
            removeRepoEndpoint(group)
            self.comboEndpoint.removeItem(self.comboEndpoint.currentIndex())
            self._addGeoGigServer(dlg.title, dlg.url)

    def deleteGeoGigServer(self):
        group = self.comboEndpoint.currentText()
        removeRepoEndpoint(group)
        self.comboEndpoint.removeItem(self.comboEndpoint.currentIndex())
        self._enableOrDisableButtons()

    def addGeoGigServer(self):
        dlg = GeoGigServerDialog()
        dlg.exec_()
        if dlg.title is not None:
            self._addGeoGigServer(dlg.title, dlg.url)
        self._enableOrDisableButtons()

    def _addGeoGigServer(self, title, url):
        try:
            repos = addRepoEndpoint(url, title)
            if not repos:
                msg = "No repositories found at the specified server"
                QMessageBox.warning(self, 'Add repositories',
                                "No repositories found at the specified server",
                                QMessageBox.Ok)


        except Exception as e:
            msg = "No geogig server found at the specified url. %s"
            QgsMessageLog.logMessage(msg % e, level=QgsMessageLog.CRITICAL)
            QMessageBox.warning(self, 'Add repositories',
                                msg % "See the logs for details.",
                                QMessageBox.Ok)

        self.comboEndpoint.addItem(title)
        self.comboEndpoint.setCurrentIndex(self.comboEndpoint.count() - 1)

    def _enableOrDisableButtons(self):
        self.btnEditServer.setEnabled(len(repository.availableRepoEndpoints) > 0)
        self.btnDeleteServer.setEnabled(len(repository.availableRepoEndpoints) > 0)


class RepoItem(QTreeWidgetItem):
    def __init__(self, tree, repo):
        QTreeWidgetItem.__init__(self)
        self.repo = repo
        self.tree = tree
        self.setSizeHint(0, QSize(self.sizeHint(0).width(), 25))
        self.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        self.setText(0, self.repo.title)
        self.setIcon(0, repoIcon)

    def populate(self):
        if not self.childCount():
            branches = self.repo.branches()
            for branch in branches:
                item = BranchItem(self.tree, self.repo, branch)
                self.addChild(item)

    def refreshContent(self):
        isPopulated = self.childCount()
        self.takeChildren()
        if isPopulated:
            self.populate()

    def menu(self):
        menu = QMenu()
        copyUrlAction = QAction("Copy repository URL", menu)
        copyUrlAction.triggered.connect(self.copyUrl)
        menu.addAction(copyUrlAction)
        refreshAction = QAction("Refresh", menu)
        refreshAction.triggered.connect(self.refreshContent)
        menu.addAction(refreshAction)
        deleteAction = QAction("Delete", menu)
        deleteAction.triggered.connect(self.delete)
        menu.addAction(deleteAction)
        remotesAction = QAction("Manage connections", menu)
        remotesAction.triggered.connect(self.manageRemotes)
        menu.addAction(remotesAction)
        pullAction = QAction("Pull", menu)
        pullAction.triggered.connect(self.pull)
        menu.addAction(pullAction)
        pushAction = QAction("Push", menu)
        pushAction.triggered.connect(self.push)
        menu.addAction(pushAction)
        return menu

    def copyUrl(self):
        QApplication.clipboard().setText(self.repo.url)

    def delete(self):
        ret = QMessageBox.warning(config.iface.mainWindow(), "Remove repository",
                            "Are you sure you want to remove this repository and all the data in it?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes);
        if ret == QMessageBox.No:
            return
        tracked = getTrackedPathsForRepo(self.repo)
        self.repo.delete()
        removeRepo(self.repo)
        removeTrackedForRepo(self.repo)
        layers = vectorLayers()
        for layer in layers:
            if formatSource(layer) in tracked:
                setAsNonRepoLayer(layer)
        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(self))
        repoWatcher.repoChanged.emit(self.repo)

    def manageRemotes(self):
        dlg = RemotesDialog(iface.mainWindow(), self.repo)
        dlg.exec_()

    def pull(self):
        dlg = RemoteRefDialog(self.repo)
        dlg.exec_()
        if dlg.remote is not None:
            conflicts = execute(lambda: self.repo.pull(dlg.remote, dlg.branch))
            if conflicts:
                ret = QMessageBox.warning(iface.mainWindow(), "Error while syncing",
                                          "There are conflicts between local repository and connection.\n"
                                          "Do you want to continue and fix them?",
                                          QMessageBox.Yes | QMessageBox.No)
                if ret == QMessageBox.No:
                    self.currentRepo.closeTransaction(conflicts[0].transactionId)
                    return

                dlg = ConflictDialog(conflicts)
                dlg.exec_()
                solved, resolvedConflicts = dlg.solved, dlg.resolvedConflicts
                if not solved:
                    self.repo.closeTransaction(conflicts[0].transactionId)
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
                user, email = config.getUserInfo()
                if user is None:
                    return
                self.repo.commitAndCloseMergeAndTransaction(user, email, "Resolved merge conflicts", conflicts[0].transactionId)
                config.iface.messageBar().pushMessage("Changes have been correctly pulled from the connection",
                                               level = QgsMessageBar.INFO, duration = 5)
                repoWatcher.repoChanged.emit(self.repo)
            else:
                config.iface.messageBar().pushMessage("Changes have been correctly pulled from the connection",
                                               level = QgsMessageBar.INFO, duration = 5)
                repoWatcher.repoChanged.emit(self.repo)

    def push(self):
        dlg = RemoteRefDialog(self.repo)
        dlg.exec_()
        if dlg.remote is not None:
            try:
                self.repo.push(dlg.remote, dlg.branch)
                config.iface.messageBar().pushMessage("Changes have been correctly pushed to connection",
                                               level = QgsMessageBar.INFO, duration = 5)
            except CannotPushException:
                config.iface.messageBar().pushMessage("Changes could not be pushed to connection. Make sure you have pulled changes from it first.",
                                               level = QgsMessageBar.WARNING, duration = 5)



class BranchItem(QTreeWidgetItem):
    def __init__(self, tree, repo, branch):
        QTreeWidgetItem.__init__(self)
        self.repo = repo
        self.tree = tree
        self.branch = branch
        self.setText(0, branch)
        self.setIcon(0, branchIcon)
        self.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

    def populate(self):
        if not self.childCount():
            layers = self.repo.trees(self.branch)
            if layers:
                branchCommitId = self.repo.revparse(self.branch)
            for layer in layers:
                item = LayerItem(self.tree, self, self.repo, layer, self.branch, branchCommitId)
                self.addChild(item)

    def refreshContent(self):
        isPopulated = self.childCount()
        self.takeChildren()
        if isPopulated:
            self.populate()

    def menu(self):
        menu = QMenu()
        refreshAction = QAction("Refresh", menu)
        refreshAction.triggered.connect(self.refreshContent)
        menu.addAction(refreshAction)
        deleteAction = QAction("Delete", menu)
        deleteAction.triggered.connect(self.delete)
        menu.addAction(deleteAction)
        deleteAction.setEnabled(self.parent().childCount() > 1 and self.branch != "master")
        return menu

    def delete(self):
        ret = QMessageBox.question(self, 'Delete branch',
                'Are you sure you want to delete this branch?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret == QMessageBox.No:
            return
        self.repo.deletebranch(self.branch)
        repoWatcher.repoChanged.emit(self.repo)

class LayerItem(QTreeWidgetItem):

    NOT_EXPORTED, NOT_IN_SYNC, IN_SYNC = list(range(3))

    def __init__(self, tree, parent, repo, layer, branch, branchCommitId):
        QTreeWidgetItem.__init__(self, parent)
        self.repo = repo
        self.tree = tree
        self.layer = layer
        self.branch = branch
        self.currentCommitId = None
        self.branchCommitId = branchCommitId
        self.setIcon(0, layerIcon)
        self.setText(0, self.layer)

        self.status = self.NOT_EXPORTED
        trackedlayer = getTrackingInfoForGeogigLayer(self.repo.url, layer)
        if trackedlayer:
            if os.path.exists(trackedlayer.geopkg):
                try:
                    con = sqlite3.connect(trackedlayer.geopkg)
                    cursor = con.cursor()
                    cursor.execute("SELECT commit_id FROM geogig_audited_tables WHERE table_name='%s';" % layer)
                    self.currentCommitId = cursor.fetchone()[0]
                    cursor.close()
                    con.close()
                    if branchCommitId == self.currentCommitId:
                        self.status = self.IN_SYNC
                    else:
                        self.status = self.NOT_IN_SYNC
                except:
                    pass


    def add(self):
        if self.status == self.NOT_IN_SYNC:
            msgBox = QMessageBox()
            msgBox.setText("This layer was exported already at a different commit.\nWhich one would you like to add to your QGIS project?")
            msgBox.addButton(QPushButton('Use previously exported commit'), QMessageBox.YesRole)
            msgBox.addButton(QPushButton('Use latest commit from this branch'), QMessageBox.NoRole)
            msgBox.addButton(QPushButton('Cancel'), QMessageBox.RejectRole)
            QApplication.restoreOverrideCursor()
            ret = msgBox.exec_()
            if ret == 0:
                checkoutLayer(self.repo, self.layer, None, self.currentCommitId)
            elif ret == 1:
                try:
                    layer = checkoutLayer(self.repo, self.layer, None, self.branchCommitId)
                    repoWatcher.layerUpdated.emit(layer)
                except HasLocalChangesError:
                    QMessageBox.warning(config.iface.mainWindow(), 'Cannot export this commit',
                                        "There are local changes that would be overwritten.\n"
                                        "Revert them before exporting.",QMessageBox.Ok)
        else:
            checkoutLayer(self.repo, self.layer, None, self.branchCommitId)


    def menu(self):
        menu = QMenu()
        status = "[A different commit of the layer has been already exported]" if self.status == self.NOT_IN_SYNC else ""
        addAction = QAction("Add to project %s" % status, menu)
        addAction.triggered.connect(self.add)
        menu.addAction(addAction)
        deleteAction = QAction("Delete", menu)
        deleteAction.triggered.connect(self.delete)
        menu.addAction(deleteAction)
        return menu

    def delete(self):
        ret = QMessageBox.question(self.tree, 'Delete layer',
                'Are you sure you want to delete this layer from this branch?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret == QMessageBox.No:
            return
        execute(lambda: self._removeLayer())

    def _removeLayer(self):
        user, email = config.getUserInfo()
        if user is None:
            return

        self.repo.removetree(self.layer, user, email, self.branch)

        config.iface.messageBar().pushMessage("Layer correctly removed from repository",
                                               level = QgsMessageBar.INFO, duration = 5)

        layer = getProjectLayerForGeoGigLayer(self.repo.url, self.layer)
        if layer:
            branches = self.repo.branches()
            layerInRepo = False
            for branch in branches:
                layers = self.repo.trees(branch)
                if self.layer in layers:
                    layerInRepo = True
                    break
            if not layerInRepo:
                setAsNonRepoLayer(layer)
                tracking = getTrackingInfoForGeogigLayer(self.repo.url, self.layer)
                if tracking:
                    removeTrackedLayer(tracking.source)
        #TODO remove triggers from layer
        repoWatcher.repoChanged.emit(self.repo)


navigatorInstance = NavigatorDialog()
