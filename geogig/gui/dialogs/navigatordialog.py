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
from collections import defaultdict

from PyQt4 import uic
from PyQt4.QtCore import Qt, QUrl, QSize
from PyQt4.QtGui import (QIcon,
                         QHeaderView,
                         QVBoxLayout,
                         QAbstractItemView,
                         QTreeWidgetItem,
                         QMessageBox,
                         QBrush,
                         QColor,
                         QInputDialog,
                         QDesktopServices, QLabel, QHBoxLayout, QSizePolicy,
    QLineEdit, QWidget)

from qgis.core import QgsApplication, QgsMessageLog
from qgis.gui import QgsMessageBar

from geogig import config
from geogig.gui.executor import execute
from geogig.gui.dialogs.historyviewer import HistoryViewer
from geogig.gui.dialogs.importdialog import ImportDialog
from geogig.gui.dialogs.geogigserverdialog import GeoGigServerDialog
from geogig.layeractions import setAsRepoLayer, setAsNonRepoLayer
from geogig.repowatcher import repoWatcher
from geogig.tools.layers import (getAllLayers,
                                 getVectorLayers,
                                 resolveLayerFromSource,
                                 WrongLayerSourceException,
                                 formatSource)
from geogig.tools.layertracking import *
from geogig.tools.utils import *
from geogig.tools.gpkgsync import checkoutLayer
from geogig.tools.layertracking import removeTrackedLayer, getProjectLayerForGeoGigLayer
from geogig.geogigwebapi import repository
from geogig.geogigwebapi.repository import *

pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]

def icon(f):
    return QIcon(os.path.join(pluginPath, "ui", "resources", f))

repoIcon = icon("repo-downloaded.png")
branchIcon = icon("branch-active.png")
layerIcon = icon('geometry.png')

WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'navigatordialog.ui'))

class NavigatorDialog(BASE, WIDGET):

    def __init__(self):
        super(NavigatorDialog, self).__init__(None)

        self.currentRepo = None
        self.currentRepoName = None
        self.reposItem = None
        self.setupUi(self)

        self.filterWidget.hide()
        self.leFilter.setPlaceholderText(self.tr("Type here to filter repositories..."))

        self.actionAddGeoGigServer.setIcon(icon('geogig_server.png'))
        self.actionCreateRepository.setIcon(icon('new-repo.png'))
        self.actionAddLayer.setIcon(icon('layer_group.gif'))
        self.actionEdit.setIcon(QgsApplication.getThemeIcon('/symbologyEdit.png'))
        self.actionRefresh.setIcon(QgsApplication.getThemeIcon('/mActionDraw.svg'))
        self.actionShowFilter.setIcon(QgsApplication.getThemeIcon('/mActionFilter2.svg'))
        self.actionDelete.setIcon(QgsApplication.getThemeIcon('/mActionDeleteSelected.svg'))
        self.actionHelp.setIcon(QgsApplication.getThemeIcon('/mActionHelpContents.svg'))

        self.actionAddGeoGigServer.triggered.connect(self.addGeoGigServer)
        self.actionCreateRepository.triggered.connect(self.createRepo)
        self.actionAddLayer.triggered.connect(self.addLayer)
        self.actionEdit.triggered.connect(self.editGeoGigServer)
        self.actionRefresh.triggered.connect(self.updateNavigator)
        self.actionShowFilter.triggered.connect(self.showFilterWidget)
        self.actionDelete.triggered.connect(self.deleteCurrentElement)
        self.actionHelp.triggered.connect(self.openHelp)

        self.leFilter.returnPressed.connect(self.filterRepos)
        self.leFilter.cleared.connect(self.filterRepos)
        self.leFilter.textChanged.connect(self.filterRepos)

        self.repoTree.itemClicked.connect(self.treeItemClicked)
        self.repoTree.itemSelectionChanged.connect(self.checkButtons)
        self.repoDescription.setOpenLinks(False)
        self.repoDescription.anchorClicked.connect(self.descriptionLinkClicked)
        self.repoTree.setFocusPolicy(Qt.NoFocus)

        with open(resourceFile("repodescription.css")) as f:
            sheet = "".join(f.readlines())
        self.repoDescription.document().setDefaultStyleSheet(sheet)
        self.repoTree.header().setResizeMode(0, QHeaderView.Stretch)
        self.repoTree.header().setResizeMode(1, QHeaderView.ResizeToContents)

        self.versionsTree = HistoryViewer()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.addWidget(self.versionsTree)
        self.versionsWidget.setLayout(layout)

        self.lastSelectedRepoItem = None

        def _repoChanged(repo):
            if self.currentRepo is not None and repo.url == self.currentRepo.url:
                self.updateCurrentRepo(repo, repo.title)
        repoWatcher.repoChanged.connect(_repoChanged)

        self.updateNavigator()

        self.repoTree.itemExpanded.connect(self._itemExpanded)

    def updateNavigator(self):
        readRepos()
        self.fillTree()
        self.updateCurrentRepo(None, None)
        self.checkButtons()

    def _itemExpanded(self, item):
        if item is not None and isinstance(item, (RepoItem, BranchItem)):
            item.populate()

    def descriptionLinkClicked(self, url):
        url = url.toString()
        if url.startswith("checkout"):
            allLayers = getAllLayers()
            items = ["Download complete layer", "Filter using bounding box of current project"]
            items.extend(["Filter using bounding box of layer " + lay.name() for lay in allLayers])
            layernames = url[url.find(":")+1:].split(",")
            for layername in layernames:
                if layername:
                    self._checkoutLayer(layername, None)
            self.updateCurrentRepo(self.currentRepo, self.currentRepo.title)
        elif url.startswith("remove"):
            ret = QMessageBox.warning(config.iface.mainWindow(), "Delete layer",
                        "Are you sure you want to delete this layer?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes);
            if ret == QMessageBox.No:
                return

            user, email = config.getUserInfo()
            if user is None:
                return

            layername = url[url.find(":")+1:]
            self.currentRepo.removetree(layername, user, email)

            config.iface.messageBar().pushMessage("Layer correctly removed from repository",
                                                   level = QgsMessageBar.INFO, duration = 5)

            layer = getProjectLayerForGeoGigLayer(self.currentRepo.url, layername)
            if layer:
                setAsNonRepoLayer(layer)
                removeTrackedLayer(layer)
            #TODO remove triggers from layer
            self.updateCurrentRepo(self.currentRepo, self.currentRepo.title)


    def _checkoutLayer(self, layername, bbox):
        checkoutLayer(self.currentRepo, layername, bbox)

    def updateCurrentRepoDescription(self):
        self.repoDescription.setText(self.currentRepo.fullDescription())

    def fillTree(self):
        self.updateCurrentRepo(None, None)
        self.repoTree.clear()
        self.reposItem = None
        repos = repository.repos

        self.reposItem = RepositoriesItem()
        self.reposItem.setIcon(0, repoIcon)
        groupedRepos = defaultdict(list)
        for repo in repos:
            groupedRepos[repo.group].append(repo)

        for groupName in repository.repoEndpoints:
            groupRepos = groupedRepos.get(groupName, [])
            groupItem = GroupItem(groupName)
            for repo in groupRepos:
                try:
                    item = RepoItem(self.repoTree,repo)
                    groupItem.addChild(item)
                except:
                    #TODO: inform of failed repos
                    pass

            self.reposItem.addChild(groupItem)

        self.repoTree.addTopLevelItem(self.reposItem)
        if self.reposItem.childCount():
            self.filterRepos()
        self.reposItem.setExpanded(True)
        for i in xrange(self.reposItem.childCount()):
            self.reposItem.child(i).setExpanded(True)
        #self.repoTree.expandAll()
        self.repoTree.sortItems(0, Qt.AscendingOrder)

    def showHistoryTab(self):
        self.historyTabButton.setAutoRaise(False)
        self.descriptionTabButton.setAutoRaise(True)
        self.versionsWidget.setVisible(True)
        self.repoDescription.setVisible(False)

    def showDescriptionTab(self):
        self.historyTabButton.setAutoRaise(True)
        self.descriptionTabButton.setAutoRaise(False)
        self.versionsWidget.setVisible(False)
        self.repoDescription.setVisible(True)

    def addLayer(self):
        layers = [layer for layer in getVectorLayers()
                        if layer.source().lower().split("|")[0].split(".")[-1] in["gpkg", "geopkg"]
                        and not isRepoLayer(layer)]
        if layers:
            dlg = ImportDialog(self, repo = self.currentRepo)
            dlg.exec_()
            if dlg.ok:
                self.versionsTree.updateCurrentBranchItem()
                self.updateCurrentRepoDescription()
                setAsRepoLayer(dlg.layer)
        else:
            QMessageBox.warning(self, 'Cannot add layer',
                "No suitable layers can be found in your current QGIS project.\n"
                "Only Geopackage layers that do not already belong to a repository can be added.",
                QMessageBox.Ok)

    def deleteCurrentElement(self):
        if len(self.repoTree.selectedItems()) == 0:
            return

        item = self.repoTree.selectedItems()[0]
        if isinstance(item, RepoItem):
            ret = QMessageBox.warning(config.iface.mainWindow(), "Remove repository",
                            "Are you sure you want to remove this repository and all the data in it?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes);
            if ret == QMessageBox.No:
                return
            tracked = getTrackedPathsForRepo(item.repo)
            item.repo.delete()
            removeRepo(item.repo)
            removeTrackedForRepo(item.repo)
            layers = getVectorLayers()
            for layer in layers:
                if formatSource(layer) in tracked:
                    setAsNonRepoLayer(layer)
            parent = item.parent()
            parent.removeChild(item)
            self.updateCurrentRepo(None, None)
        elif isinstance(item, GroupItem):
            self._removeRepoEndpoint(item)
        elif isinstance(item, BranchItem):
            ret = QMessageBox.question(self, 'Delete Branch',
                    'Are you sure you want to delete this branch?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret == QMessageBox.No:
                return
            item.repo.deletebranch(item.branch)
            repoWatcher.repoChanged.emit(item.repo)


    def _removeRepoEndpoint(self, item):
        parent = item.parent()
        parent.removeChild(item)
        removeRepoEndpoint(item.text(0))

    def filterRepos(self):
        text = self.leFilter.text().strip()
        for i in xrange(self.repoTree.topLevelItemCount()):
            parent = self.repoTree.topLevelItem(i)
            for j in xrange(parent.childCount()):
                item = parent.child(j)
                itemText = item.text(0)
                item.setHidden(text != "" and text not in itemText)

    def treeItemClicked(self, item, i):
        if self.lastSelectedRepoItem == item:
            return
        self.lastSelectedRepoItem = item
        try:
            if isinstance(item, (GroupItem, RepositoriesItem)):
                self.updateCurrentRepo(None, None)
                url = QUrl.fromLocalFile(resourceFile("localrepos_offline.html"))
                self.repoDescription.setSource(url)
            else:
                self.updateCurrentRepo(item.repo, item.repo.title)

        except Exception, e:
                msg = "An error occurred while fetching repository data! %s"
                QgsMessageLog.logMessage(msg % e, level=QgsMessageLog.CRITICAL)
                QMessageBox.warning(self, 'Add repositories',
                                    msg % "See the logs for details.",
                                    QMessageBox.Ok)

    def updateCurrentRepo(self, repo, name):
        def _update():
            if repo != self.currentRepo:
                self.tabWidget.setCurrentIndex(0)
            if repo is None:
                self.tabWidget.setTabEnabled(1, False)
                self.currentRepo = None
                self.currentRepoName = None
                self.repoDescription.setText("")
                self.lastSelectedRepoItem = None
            else:
                self.currentRepo = repo
                self.currentRepoName = name
                self.repoDescription.setText(repo.fullDescription())
                self.versionsTree.updateContent(repo)
                self.tabWidget.setTabEnabled(1, True)
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
            groupItem = self.repoTree.selectedItems()[0]
            group = groupItem.text(0)
            url = repository.repoEndpoints[group]
            repo = createRepoAtUrl(url, group, name)
            item = RepoItem(repo)
            addRepo(repo)
            groupItem.addChild(item)

    def editGeoGigServer(self):
        item = self.repoTree.selectedItems()[0]
        dlg = GeoGigServerDialog(repository.repoEndpoints[item.name], item.name)
        dlg.exec_()
        if dlg.title is not None:
            self._removeRepoEndpoint(item)
            self._addGeoGigServer(dlg.title, dlg.url)

    def addGeoGigServer(self):
        dlg = GeoGigServerDialog()
        dlg.exec_()
        if dlg.title is not None:
            self._addGeoGigServer(dlg.title, dlg.url)

    def _addGeoGigServer(self, title, url):
        try:
            repos = addRepoEndpoint(url, title)
            if not repos:
                msg = "No repositories found at the specified server"
                QMessageBox.warning(self, 'Add repositories',
                                "No repositories found at the specified server",
                                QMessageBox.Ok)
            else:
                groupItem = GroupItem(title)
                for repo in repos:
                    item = RepoItem(repo)
                    groupItem.addChild(item)
        except Exception, e:
            msg = "No geogig server found at the specified url. %s"
            QgsMessageLog.logMessage(msg % e, level=QgsMessageLog.CRITICAL)
            QMessageBox.warning(self, 'Add repositories',
                                msg % "See the logs for details.",
                                QMessageBox.Ok)
            groupItem = GroupItem(title)
        self.reposItem.addChild(groupItem)
        self.reposItem.setExpanded(True)
        self.repoTree.sortItems(0, Qt.AscendingOrder)

    def showFilterWidget(self, visible):
        self.filterWidget.setVisible(visible)
        if not visible:
            self.leFilter.setText("")
            self.filterRepos()
        else:
            self.leFilter.setFocus()

    def checkButtons(self):
        self.actionCreateRepository.setEnabled(False)
        self.actionRefresh.setEnabled(False)
        self.actionDelete.setEnabled(False)
        self.actionEdit.setEnabled(False)
        if len(self.repoTree.selectedItems()) == 0:
            return

        item = self.repoTree.selectedItems()[0]
        if isinstance(item, RepositoriesItem):
            self.actionRefresh.setEnabled(True)
        elif isinstance(item, GroupItem):
            self.actionEdit.setEnabled(True)
            if item.isRepoAvailable:
                self.actionCreateRepository.setEnabled(True)
            self.actionDelete.setEnabled(True)
        elif isinstance(item, BranchItem):
            self.actionDelete.setEnabled(item.parent().childCount() > 1)
        else:
            self.actionDelete.setEnabled(True)

    def openHelp(self):
        if not QDesktopServices.openUrl(QUrl('http://boundlessgeo.github.io/qgis-plugins-documentation/geogig-light/index.html')):
            QMessageBox.warning(self, self.tr('Error'), self.tr('Can not open help URL in browser'))



class RepositoriesItem(QTreeWidgetItem):
    def __init__(self):
        QTreeWidgetItem.__init__(self)
        self.setText(0, "Repositories")

class GroupItem(QTreeWidgetItem):
    def __init__(self, name):
        QTreeWidgetItem.__init__(self)
        self.setIcon(0, repoIcon)
        self.setText(0, name)
        if name not in repository.availableRepoEndpoints:
            self.setForeground(0,Qt.gray)
            self.isRepoAvailable = False
        else:
            self.isRepoAvailable = True
        self.name = name

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
                item = LayerItem(self.tree, self, self.repo, layer, branchCommitId)
                self.addChild(item)

class LayerItem(QTreeWidgetItem):
    def __init__(self, tree, parent, repo, layer, branchCommitId):
        QTreeWidgetItem.__init__(self, parent)
        self.repo = repo
        self.tree = tree
        self.layer = layer
        self.setIcon(0, layerIcon)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        self.label.setText(layer)
        self.labelLinks = QLabel()
        self.labelLinks.setText("<a href='#'>Add to QGIS</a>")
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.label)
        layout.addWidget(self.labelLinks)
        layout.addStretch()
        def add():
            checkoutLayer(self.repo, self.layer, None)
        self.labelLinks.linkActivated.connect(add)
        w = QWidget()
        w.setLayout(layout)
        self.tree.setItemWidget(self, 0, w)

        trackedlayer = getTrackingInfoForGeogigLayer(self.repo.url, layer)
        if trackedlayer:
            try:
                con = sqlite3.connect(trackedlayer.geopkg)
                cursor = con.cursor()
                cursor.execute("SELECT commit_id FROM geogig_audited_tables WHERE table_name='%s';" % layer)
                currentCommitId = cursor.fetchone()[0]
                cursor.close()
                con.close()
                if branchCommitId == currentCommitId:
                    self.label.setText("<font color='green'>%s</font>" % layer)
                else:
                    self.label.setText("<font color='orange'>%s</font>" % layer)
            except:
                pass




navigatorInstance = NavigatorDialog()
