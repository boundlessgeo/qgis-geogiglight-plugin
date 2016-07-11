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
from collections import defaultdict

from PyQt4 import uic
from PyQt4.QtCore import Qt, QUrl, QSize
from PyQt4.QtGui import (QIcon,
                         QHeaderView,
                         QVBoxLayout,
                         QAbstractItemView,
                         QTreeWidgetItem,
                         QAction,
                         QMessageBox,
                         QBrush,
                         QColor,
                         QToolButton)

from qgis.core import QgsApplication
from qgis.gui import QgsMessageBar

from geogig import config
from geogig.gui.executor import execute
from geogig.gui.dialogs.historyviewer import HistoryViewer
from geogig.gui.dialogs.importdialog import ImportDialog
from geogig.gui.dialogs.createrepodialog import CreateRepoDialog
from geogig.layeractions import setAsRepoLayer, setAsNonRepoLayer
from geogig.repowatcher import repoWatcher
from geogig.tools.layers import (getAllLayers,
                                 getVectorLayers,
                                 resolveLayerFromSource,
                                 WrongLayerSourceException,
                                 formatSource)
from geogig.tools.layertracking import *
from geogig.tools.utils import *

from geogig.geogigwebapi import repository
from geogig.geogigwebapi.repository import *

pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]

def icon(f):
    return QIcon(os.path.join(pluginPath, "ui", "resources", f))

#addIcon = icon("new-repo.png")
repoIcon = icon("repo-downloaded.png")
#deleteIcon = icon("delete.gif")

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

        self.actionAddRepositories.setIcon(icon('download-repo.png'))
        self.actionAddLayer.setIcon(icon('new-repo.png'))
        self.actionRefresh.setIcon(QgsApplication.getThemeIcon('/mActionDraw.svg'))
        self.actionShowFilter.setIcon(QgsApplication.getThemeIcon('/mActionFilter2.svg'))
        # ,maybe mActionDeleteSelected.svg (red recycle bin) is better here
        self.actionDeleteKeepUpstream.setIcon(QgsApplication.getThemeIcon('/mActionRemoveLayer.svg'))
        self.actionDeleteWithUpstream.setIcon(QgsApplication.getThemeIcon('/mActionRemoveLayer.svg'))

        btnDelete = QToolButton(self.navigatorToolbar)
        btnDelete.setPopupMode(QToolButton.MenuButtonPopup)
        btnDelete.addAction(self.actionDeleteKeepUpstream)
        btnDelete.addAction(self.actionDeleteWithUpstream)
        btnDelete.setDefaultAction(self.actionDeleteKeepUpstream)
        actionDelete = self.navigatorToolbar.addWidget(btnDelete)
        actionDelete.setObjectName('actionDeleteRepo')

        self.actionAddRepositories.triggered.connect(self.addRepo)
        self.actionAddLayer.triggered.connect(self.addLayer)
        self.actionRefresh.triggered.connect(self.updateNavigator)
        self.actionShowFilter.triggered.connect(self.showFilterWidget)
        self.actionDeleteKeepUpstream.triggered.connect(lambda: self.deleteRepo(False))
        self.actionDeleteWithUpstream.triggered.connect(lambda: self.deleteRepo(True))

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

        def _updateDescription(repo):
            if self.currentRepo is not None and repo.url == self.currentRepo.url:
                self.updateCurrentRepoDescription()
                self.versionsTree.updateCurrentBranchItem()
        repoWatcher.repoChanged.connect(_updateDescription)

        self.updateNavigator()

    def updateNavigator(self):
        readRepos()
        self.fillTree()
        self.updateCurrentRepo(None, None)
        self.checkButtons()

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
            #===================================================================
            # item, ok = QInputDialog.getItem(self, "Layer download",
            #                                       "Download mode", items, 0, False)
            # if ok:
            #     if item == items[0]:
            #         bbox = None
            #     elif item == items[1]:
            #         bbox = (config.iface.mapCanvas().extent(),
            #                 config.iface.mapCanvas().mapRenderer().destinationCrs())
            #     else:
            #         layer = allLayers[items.index(item) - 2]
            #         bbox = (layer.extent(), layer.crs())
            #     layernames = url.split(":")[-1].split(",")
            #     for layername in layernames:
            #         self._checkoutLayer(layername, bbox)
            #
            #===================================================================

    def _checkoutLayer(self, layername, bbox):
        trackedlayer = getTrackingInfoForGeogigLayer(self.currentRepo.url, layername)
        if trackedlayer is not None:
            if not os.path.exists(trackedlayer.geopkg):
                removeTrackedLayer(trackedlayer.source)
                trackedlayer = None
                filename = layerGeopackageFilename(layername, self.currentRepoName, self.currentRepo.group)
                source = "%s|layername=%s" % (filename, layername)
            else:
                source = trackedlayer.source
        else:
            filename = layerGeopackageFilename(layername, self.currentRepoName, self.currentRepo.group)
            source = "%s|layername=%s" % (filename, layername)
        if trackedlayer is None:
            self.currentRepo.checkoutlayer(filename, layername, bbox, self.currentRepo.HEAD)
            addTrackedLayer(source, self.currentRepo.url)

        try:
            resolveLayerFromSource(source)
            config.iface.messageBar().pushMessage("GeoGig", "Layer was already included in the current QGIS project",
                                  level=QgsMessageBar.INFO)
        except WrongLayerSourceException:
            layer = loadLayerNoCrsDialog(source, layername, "ogr")
            QgsMapLayerRegistry.instance().addMapLayers([layer])
            config.iface.messageBar().pushMessage("GeoGig", "Layer correctly added to the current QGIS project",
                                                  level=QgsMessageBar.INFO)

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

        for groupName, groupRepos in groupedRepos.iteritems():
            groupItem = QTreeWidgetItem()
            groupItem.setText(0, groupName)
            groupItem.setIcon(0, repoIcon)
            for repo in groupRepos:
                try:
                    item = RepoItem(repo)
                    groupItem.addChild(item)
                except:
                    #TODO: inform of failed repos
                    pass
            if groupItem.childCount():
                self.reposItem.addChild(groupItem)

        self.repoTree.addTopLevelItem(self.reposItem)
        if self.reposItem.childCount():
            self.filterRepos()
            self.reposItem.setExpanded(True)
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
                "Open the layers in QGIS before trying to add them.",
                QMessageBox.Ok)

    def deleteRepo(self, deleteUpstream):
        if len(self.repoTree.selectedItems()) == 0:
            return

        item = self.repoTree.selectedItems()[0]
        if not isinstance(item, RepoItem):
            return

        ret = QMessageBox.warning(config.iface.mainWindow(), "Remove repository",
                        "Are you sure you want to remove this repository?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes);
        if ret == QMessageBox.No:
            return
        removeRepo(item.repo)
        if deleteUpstream:
            item.repo.delete()

        parent = self.lastSelectedRepoItem.parent()
        parent.removeChild(self.lastSelectedRepoItem)
        if parent.childCount() == 0:
            parent.parent().removeChild(parent)

        self.updateCurrentRepo(None, None)

        tracked = getTrackedPathsForRepo(item.repo)
        layers = getVectorLayers()
        for layer in layers:
            if formatSource(layer) in tracked:
                setAsNonRepoLayer(layer)

        removeTrackedForRepo(item.repo)

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
        if isinstance(item, RepoItem):
            self.updateCurrentRepo(item.repo, item.text(0))
        else:
            self.updateCurrentRepo(None, None)
            if item.parent() == self.repoTree.invisibleRootItem():
                url = QUrl.fromLocalFile(resourceFile("localrepos_offline.html"))
                self.repoDescription.setSource(url)
            else:
                self.repoDescription.setText("")

    def updateCurrentRepo(self, repo, name):
        def _update():
            if repo != self.currentRepo:
                self.tabWidget.setCurrentIndex(0)
            self.tabWidget.setTabEnabled(1, False)
            if repo is None:
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

    def addRepo(self):
        dlg = CreateRepoDialog()
        dlg.exec_()
        if dlg.title is not None:
            try:
                repos = repositoriesFromUrl(dlg.url, dlg.title)
                addRepoEndpoint(dlg.url, dlg.title)
                groupItem = QTreeWidgetItem()
                groupItem.setText(0, dlg.title)
                groupItem.setIcon(0, repoIcon)
                for repo in repos:
                    item = RepoItem(repo)
                    addRepo(repo)
                    groupItem.addChild(item)
                if groupItem.childCount():
                    self.reposItem.addChild(groupItem)
                    self.reposItem.setExpanded(True)
                    self.repoTree.sortItems(0, Qt.AscendingOrder)
            except:
                QMessageBox.warning(self, 'Add repositories',
                    "No repositories found at the specified url.",
                    QMessageBox.Ok)

    def showFilterWidget(self, visible):
        self.filterWidget.setVisible(visible)
        if not visible:
            self.leFilter.setText("")
            self.filterRepos()
        else:
            self.leFilter.setFocus()

    def checkButtons(self):
        if len(self.repoTree.selectedItems()) == 0:
            self.actionRefresh.setEnabled(False)
            self.actionDeleteKeepUpstream.setEnabled(False)
            self.actionDeleteWithUpstream.setEnabled(False)
            return

        item = self.repoTree.selectedItems()[0]
        if isinstance(item, RepoItem):
            self.actionRefresh.setEnabled(False)
            self.actionDeleteKeepUpstream.setEnabled(True)
            self.actionDeleteWithUpstream.setEnabled(True)
        elif isinstance(item, RepositoriesItem):
            self.actionRefresh.setEnabled(True)
            self.actionDeleteKeepUpstream.setEnabled(False)
            self.actionDeleteWithUpstream.setEnabled(False)
        else:
            self.actionRefresh.setEnabled(False)
            self.actionDeleteKeepUpstream.setEnabled(False)
            self.actionDeleteWithUpstream.setEnabled(False)


class RepositoriesItem(QTreeWidgetItem):
    def __init__(self):
        QTreeWidgetItem.__init__(self)
        self.setText(0, "Repositories")


class RepoItem(QTreeWidgetItem):
    def __init__(self, repo):
        QTreeWidgetItem.__init__(self)
        self.repo = repo
        self.refreshTitle()
        self.setSizeHint(0, QSize(self.sizeHint(0).width(), 25))

    def refreshTitle(self):
        self.setText(0, self.repo.title)
        self.setIcon(0, repoIcon)
        self.setForeground(1, QBrush(QColor("#5f6b77")))
        lastUpdate = self.repo.lastupdated()
        lastUpdate = "Updated " + relativeDate(lastUpdate) if lastUpdate is not None else ""
        self.setText(1, lastUpdate)

navigatorInstance = NavigatorDialog()
