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
from functools import partial

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

from geogig.extlibs.qgiscommons2.gui import execute
from geogig.gui.dialogs.historyviewer import HistoryViewer, HistoryViewerDialog
from geogig.gui.dialogs.importdialog import ImportDialog
from geogig.gui.dialogs.geogigserverdialog import GeoGigServerDialog
from geogig.gui.dialogs.remotesdialog import RemotesDialog
from geogig.gui.dialogs.remoterefdialog import askForRemoteRef
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
                                            createRepoAtUrl, addRepoEndpoint, addRepo,
                                            NothingToPushException)
from builtins import zip
from builtins import str
from builtins import range

from geogig.extlibs.qgiscommons2.layers import vectorLayers

qtVersion = int(QT_VERSION_STR.split(".")[0])
pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]

def icon(f):
    return QIcon(os.path.join(pluginPath, "ui", "resources", f))

repoIcon = icon("repository.svg")
branchIcon = icon("branch.svg")
layerIcon = icon('geometry.svg')
copyIcon  = icon('copy.png')
mergeIcon = icon("merge-24.png")

WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'navigatordialog.ui'))

class NavigatorDialog(BASE, WIDGET):

    def __init__(self):
        super(NavigatorDialog, self).__init__(None)
        self.reposItem = None
        self.setupUi(self)

        self.repoTree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.repoTree.setSelectionBehavior(QAbstractItemView.SelectRows)
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
        self.btnRefresh.clicked.connect(self.refreshTree)

        self._enableOrDisableButtons()

        if qtVersion < 5:
            self.repoTree.header().setResizeMode(0, QHeaderView.Stretch)
            self.repoTree.header().setResizeMode(1, QHeaderView.ResizeToContents)

        def _repoChanged(repo):
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
        point = self.repoTree.mapToGlobal(point)
        self.menu.popup(point)

    def updateNavigator(self):
        self.fillCombo()

    def _itemExpanded(self, item):
        if item is not None and isinstance(item, (RepoItem, BranchItem)):
            item.populate()

    def fillCombo(self):
        self.comboEndpoint.clear()
        groups = repository.repoEndpoints.keys()
        #groups.insert(0, "Select a GeoGig server")
        self.comboEndpoint.addItems(groups)

    def refreshTree(self):
        groupName = self.comboEndpoint.currentText()
        repository.refreshEndpoint(groupName)
        self.fillTree()

    def fillTree(self):
        groupName = self.comboEndpoint.currentText()
        #repository.refreshEndpoint(groupName)
        self.btnAddRepo.setEnabled(groupName in repository.availableRepoEndpoints)
        self.repoTree.clear()

        groupRepos = repository.endpointRepos(groupName)
        for repo in groupRepos:
            try:
                item = RepoItem(self, self.repoTree, repo)
                self.repoTree.addTopLevelItem(item)
            except:
                #TODO: inform of failed repos
                pass

        self.repoTree.sortItems(0, Qt.AscendingOrder)

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
            item = RepoItem(self, self.repoTree, repo)
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
        res = QMessageBox.question(None,
                                  "Delete server?",
                                  "Are you sure you want to remove the "
                                  "'{}' GeoGig server from the list?".format(group),
                                  QMessageBox.Yes | QMessageBox.No,
                                  QMessageBox.No)
        if res == QMessageBox.Yes:
            removeRepoEndpoint(group)
            self.comboEndpoint.removeItem(self.comboEndpoint.currentIndex())
            self.fillTree()
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
        self.btnEditServer.setEnabled(len(repository.repoEndpoints) > 0)
        self.btnDeleteServer.setEnabled(len(repository.repoEndpoints) > 0)


class RepoItem(QTreeWidgetItem):
    def __init__(self, navigator, tree, repo):
        QTreeWidgetItem.__init__(self)
        self.navigator = navigator
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
                item = BranchItem(self.navigator, self.tree, self.repo, branch)
                self.addChild(item)

    def refreshContent(self):
        isPopulated = self.childCount()
        self.takeChildren()
        if isPopulated:
            self.populate()


    def menu(self):
        menu = QMenu()
        showHistoryAction = QAction(icon("history.png"), "Show history", menu)
        showHistoryAction.triggered.connect(self.showHistory)
        menu.addAction(showHistoryAction)
        copyUrlAction = QAction(icon("copy.png"), "Copy repository URL", menu)
        copyUrlAction.triggered.connect(self.copyUrl)
        menu.addAction(copyUrlAction)
        refreshAction = QAction(icon("refresh.svg"), "Refresh", menu)
        refreshAction.triggered.connect(lambda: self.refreshContent(True))
        menu.addAction(refreshAction)
        deleteAction = QAction(QgsApplication.getThemeIcon('/mActionDeleteSelected.svg'), "Delete", menu)
        deleteAction.triggered.connect(self.delete)
        menu.addAction(deleteAction)
        remotesAction = QAction("Manage remote connections", menu)
        remotesAction.triggered.connect(self.manageRemotes)
        menu.addAction(remotesAction)
        return menu

    def showHistory(self):
        dlg = HistoryViewerDialog(self.repo)
        dlg.exec_()

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

class BranchItem(QTreeWidgetItem):
    def __init__(self, navigator, tree, repo, branch):
        QTreeWidgetItem.__init__(self)
        self.navigator = navigator
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
        showHistoryAction = QAction(icon("history.png"), "Show history", menu)
        showHistoryAction.triggered.connect(self.showHistory)
        menu.addAction(showHistoryAction)
        refreshAction = QAction(icon("refresh.svg"), "Refresh", menu)
        refreshAction.triggered.connect(self.refreshContent)
        menu.addAction(refreshAction)
        createBranchAction = QAction(icon("create_branch.png"), "Create branch", menu)
        createBranchAction.triggered.connect(self.createBranch)
        menu.addAction(createBranchAction)
        deleteAction = QAction(QgsApplication.getThemeIcon('/mActionDeleteSelected.svg'), "Delete", menu)
        deleteAction.triggered.connect(self.delete)
        menu.addAction(deleteAction)
        pullAction = QAction(icon("pull.svg"), "Pull", menu)
        pullAction.triggered.connect(self.pull)
        menu.addAction(pullAction)
        pushAction = QAction(icon("push.svg"), "Push", menu)
        pushAction.triggered.connect(self.push)
        menu.addAction(pushAction)
        deleteAction.setEnabled(self.parent().childCount() > 1 and self.branch != "master")
        mergeActions = []
        for branch in self.repo.branches():
            if branch != self.branch:
                mergeAction = QAction(mergeIcon, branch, None)
                mergeAction.triggered.connect(partial(self.mergeInto, branch, self.branch))
                mergeActions.append(mergeAction)
        if mergeActions:
            mergeMenu = QMenu("Merge this branch into")
            mergeMenu.setIcon(mergeIcon)
            menu.addMenu(mergeMenu)
            for action in mergeActions:
                mergeMenu.addAction(action)
                
        return menu

    def mergeInto(self, mergeInto, branch):
        conflicts = self.repo.merge(branch, mergeInto)
        if conflicts:
            ret = QMessageBox.warning(iface.mainWindow(), "Conflict(s) found while syncing",
                                      "There are conflicts between local and remote changes.\n"
                                      "Do you want to continue and fix them?",
                                      QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                self.repo.closeTransaction(conflicts[0].transactionId)
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

        iface.messageBar().pushMessage("GeoGig", "Branch has been correctly merged",
                                              level=QgsMessageBar.INFO, duration=5)
        repoWatcher.repoChanged.emit(self.repo)
        
    def showHistory(self):
        dlg = HistoryViewerDialog(self.repo, branch = self.branch)
        dlg.exec_()


    def createBranch(self):
        text, ok = QInputDialog.getText(self.tree, 'Create New Branch',
                                              'Enter the name for the new branch:')
        if ok:
            self.repo.createbranch(self.branch, text.replace(" ", "_"))
            repoWatcher.repoChanged.emit(self.repo)

    def delete(self):
        ret = QMessageBox.question(self.tree, 'Delete branch',
                'Are you sure you want to delete this branch?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret == QMessageBox.No:
            return
        self.repo.deletebranch(self.branch)
        repoWatcher.repoChanged.emit(self.repo)
        

    def pull(self):
        remote, branch = askForRemoteRef(self.repo)
        if remote is not None:
            conflicts = execute(lambda: self.repo.pull(remote, branch, self.branch))
            if conflicts:
                ret = QMessageBox.warning(iface.mainWindow(), "Conflict(s) found while syncing",
                                          "There are conflicts between local repository and connection.\n"
                                          "Do you want to continue and fix them?",
                                          QMessageBox.Yes | QMessageBox.No)
                if ret == QMessageBox.No:
                    self.repo.closeTransaction(conflicts[0].transactionId)
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
        remote, branch = askForRemoteRef(self.repo)
        if remote is not None:
            try:
                self.repo.push(remote, branch, self.branch)
                config.iface.messageBar().pushMessage("Changes have been correctly pushed to connection",
                                               level = QgsMessageBar.INFO, duration = 5)
            except CannotPushException, e:
                config.iface.messageBar().pushMessage(str(e),
                                               level = QgsMessageBar.WARNING, duration = 5)
            except NothingToPushException, e:
                config.iface.messageBar().pushMessage("Nothing to push. Already up to date",
                                               level = QgsMessageBar.INFO, duration = 5)


class LayerItem(QTreeWidgetItem):

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

    def add(self):
        checkoutLayer(self.repo, self.layer, None, self.branchCommitId)

    def menu(self):
        menu = QMenu()
        showHistoryAction = QAction(icon("history.png"), "Show history", menu)
        showHistoryAction.triggered.connect(self.showHistory)
        menu.addAction(showHistoryAction)
        addAction = QAction(icon("reset.png"), "Add to project", menu)
        addAction.triggered.connect(self.add)
        menu.addAction(addAction)
        deleteAction = QAction(QgsApplication.getThemeIcon('/mActionDeleteSelected.svg'), "Delete", menu)
        deleteAction.triggered.connect(self.delete)
        menu.addAction(deleteAction)
        return menu

    def showHistory(self):
        dlg = HistoryViewerDialog(self.repo, layer = self.layer, branch = self.branch)
        dlg.exec_()

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

        projectLayers = getProjectLayerForGeoGigLayer(self.repo.url, self.layer)
        if projectLayers:
            branches = self.repo.branches()
            layerInRepo = False
            for branch in branches:
                layers = self.repo.trees(branch)
                if self.layer in layers:
                    layerInRepo = True
                    break
            if not layerInRepo:
                for projectLayer in projectLayers:
                    setAsNonRepoLayer(projectLayer)
                tracking = getTrackingInfoForGeogigLayer(self.repo.url, self.layer)
                for t in tracking:
                    removeTrackedLayer(t.source)
        #TODO remove triggers from layer

        config.iface.messageBar().pushMessage("Layer correctly removed from repository",
                                               level = QgsMessageBar.INFO, duration = 5)

        repoWatcher.repoChanged.emit(self.repo)


navigatorInstance = NavigatorDialog()
