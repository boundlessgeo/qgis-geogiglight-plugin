import os
import logging
from PyQt4 import QtGui, QtCore, uic
from qgis.core import *
from qgis.gui import *
from geogig import config
from geogig.gui.executor import execute
from geogig.tools.exporter import loadRepoExportedLayers, exportFullRepo
from geogig.tools.layertracking import *
from geogig.tools.utils import *
from geogig.gui.dialogs.historyviewer import HistoryViewer
from geogig.gui.dialogs.layerfilter import LayersFilterDialog
from geogig.gui.dialogs.importdialog import ImportDialog
from geogig.tools.layers import getAllLayers, getVectorLayers, resolveLayerFromSource, WrongLayerSourceException
from geogig.tools.repowrapper import *
from geogig.layeractions import setAsRepoLayer, repoWatcher, setAsNonRepoLayer
import sys
from geogig.geogigwebapi.repository import *
from geogig.geogigwebapi import repository
from requests.exceptions import ConnectionError
from geogig.gui.dialogs.createrepodialog import CreateRepoDialog


def icon(f):
    return QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                            os.pardir, os.pardir, "ui", "resources", f))

addIcon = icon("new-repo.png")
resetIcon = icon("reset.png")
refreshIcon = icon("refresh.png")
privateReposIcon = icon("your-repos.png")
sharedReposIcon = icon("shared-repos.png")
repoIcon = icon("repo-downloaded.png")
disabledRepoIcon = QtGui.QIcon(repoIcon.pixmap(16, 16, mode = QtGui.QIcon.Disabled))
searchIcon = icon("search-repos.png")
newBranchIcon = icon("create_branch.png")
deleteIcon = icon("delete.gif")
syncIcon = icon("sync-repo.png")

logger = logging.getLogger("geogigpy")

# Adding so that our UI files can find resources_rc.py
sys.path.append(os.path.dirname(__file__))

pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'navigatordialog.ui'))

class NavigatorDialog(BASE, WIDGET):

    def __init__(self):
        super(NavigatorDialog, self).__init__(None)

        self.currentRepo = None
        self.currentRepoName = None
        self.reposItem = None
        self.setupUi(self)

        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

        self.filterBox.adjustSize()
        tabHeight = self.filterBox.height() + self.filterBox.parent().layout().spacing()
        self.tabWidget.setStyleSheet("QTabWidget::pane {border: 0;} QTabBar::tab { height: %ipx}" % tabHeight);

        self.addRepoButton.clicked.connect(self.addRepo)
        self.filterBox.textChanged.connect(self.filterRepos)
        self.repoTree.itemClicked.connect(self.treeItemClicked)
        self.repoTree.customContextMenuRequested.connect(self.showRepoTreePopupMenu)
        self.repoDescription.setOpenLinks(False)
        self.repoDescription.anchorClicked.connect(self.descriptionLinkClicked)
        self.repoTree.setFocusPolicy(QtCore.Qt.NoFocus)

        with open(resourceFile("repodescription.css")) as f:
            sheet = "".join(f.readlines())
        self.repoDescription.document().setDefaultStyleSheet(sheet)
        self.repoTree.header().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.repoTree.header().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)

        self.versionsTree = HistoryViewer()
        layout = QtGui.QVBoxLayout()
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
        self.fillTree()
        self.updateCurrentRepo(None, None)


    def descriptionLinkClicked(self, url):
        url = url.toString()
        if url.startswith("checkout"):
            allLayers = getAllLayers()
            items = ["Download complete layer", "Filter using bounding box of current project"]
            items.extend(["Filter using bounding box of layer " + lay.name() for lay in allLayers])

            layernames = url.split(":")[-1].split(",")
            for layername in layernames:
                self._checkoutLayer(layername, None)
            #===================================================================
            # item, ok = QtGui.QInputDialog.getItem(self, "Layer download",
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
            filename = layerGeopackageFilename(layername, self.currentRepoName)
            source = "%s|layername=%s" % (filename, layername)
            trackedlayer = getTrackingInfoForGeogigLayer(self.currentRepo.url, layername)
            if trackedlayer is None or not os.path.exists(filename):
                print bbox
                self.currentRepo.checkoutlayer(filename, layername, bbox, self.currentRepo.HEAD)
                addTrackedLayer(source, self.currentRepo.url, self.currentRepo.revparse(self.currentRepo.HEAD))
            try:
                resolveLayerFromSource(source)
                config.iface.messageBar().pushMessage("GeoGig", "Layer was already included in the current QGIS project",
                                      level=QgsMessageBar.INFO)
            except WrongLayerSourceException:
                layer = loadLayerNoCrsDialog("%s|layername=%s" % (filename, layername), layername, "ogr")
                QgsMapLayerRegistry.instance().addMapLayers([layer])
                config.iface.messageBar().pushMessage("GeoGig", "Layer correctly added to the current QGIS project",
                                                      level=QgsMessageBar.INFO)



    def updateCurrentRepoDescription(self):
        self.repoDescription.setText(self.currentRepo.fullDescription)

    def fillTree(self):
        self.updateCurrentRepo(None, None)
        self.repoTree.clear()
        self.reposItem = None
        repos = repository.repos

        self.reposItem = OrderedParentItem("Repositories", 0)
        self.reposItem.setIcon(0, privateReposIcon)
        for repo in repos.values():
            try:
                item = RepoItem(repo)
                self.reposItem.addChild(item)
            except ConnectionError:
                pass

        if self.reposItem.childCount():
            self.repoTree.addTopLevelItem(self.reposItem)
            self.filterRepos()
            self.reposItem.setExpanded(True)
        self.repoTree.sortItems(0, QtCore.Qt.AscendingOrder)


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

    def showRepoTreePopupMenu(self, point):
        item = self.repoTree.selectedItems()[0]
        if isinstance(item, RepoItem):
            menu = QtGui.QMenu()
            addAction = QtGui.QAction(addIcon, "Add layer to repository...", None)
            addAction.triggered.connect(self.addLayer)
            menu.addAction(addAction)
            deleteAction = QtGui.QAction(deleteIcon, "Remove this repository", None)
            deleteAction.triggered.connect(lambda: self.deleteRepo(item))
            menu.addAction(deleteAction)
            point = self.repoTree.mapToGlobal(point)
            menu.exec_(point)


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
            QtGui.QMessageBox.warning(self, 'Cannot add layer',
                "No suitable layers can be found in your current QGIS project.\n"
                "Open the layers in QGIS before trying to add them.",
                QtGui.QMessageBox.Ok)

    def deleteRepo(self, item):
        ret = QtGui.QMessageBox.warning(config.iface.mainWindow(), "Remove repository",
                        "Are you sure you want to remove this repository?",
                        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                        QtGui.QMessageBox.Yes);
        if ret == QtGui.QMessageBox.No:
            return
        removeRepo(item.repo)
        self.lastSelectedRepoItem.parent().removeChild(self.lastSelectedRepoItem)
        self.updateCurrentRepo(None, None)

        tracked = getTrackedPathsForRepo(item.repo)
        layers = getVectorLayers()
        for layer in layers:
            if formatSource(layer) in tracked:
                setAsNonRepoLayer(layer)

        removeTrackedForRepo(item.repo)


    def filterRepos(self):
        text = self.filterBox.text().strip()
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
            url = QtCore.QUrl.fromLocalFile(resourceFile("localrepos_offline.html"))
            self.repoDescription.setSource(url)


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
            self.repoTree.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
            self.repoTree.blockSignals(True)
            execute(_update)
        finally:
            self.repoTree.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
            self.repoTree.blockSignals(False)

    def addRepo(self):
        dlg = CreateRepoDialog()
        dlg.exec_()
        if dlg.title is not None:
            repo = Repository(dlg.url, dlg.title)
            item = RepoItem(repo)
            addRepo(repo)
            self.reposItem.addChild(item)
            self.repoTree.addTopLevelItem(self.reposItem)
            self.reposItem.setExpanded(True)
            self.repoTree.sortItems(0, QtCore.Qt.AscendingOrder)
            return repo


class OrderedParentItem(QtGui.QTreeWidgetItem):
    def __init__(self, text, order):
        QtGui.QTreeWidgetItem.__init__(self)
        self.setText(0, text)
        self.order = order
        self.setSizeHint(0, QtCore.QSize(self.sizeHint(0).width(), 25))

    def __lt__(self, o):
        if isinstance(o, OrderedParentItem):
            return o.order > self.order
        else:
            return True

    def __gt__(self, o):
        return not self.__lt__(o)

class RepoItem(QtGui.QTreeWidgetItem):
    def __init__(self, repo):
        QtGui.QTreeWidgetItem.__init__(self)
        self.repo = repo
        self.refreshTitle()
        self.setSizeHint(0, QtCore.QSize(self.sizeHint(0).width(), 25))

    def refreshTitle(self):
        self.setText(0, self.repo.title)
        self.setIcon(0, repoIcon)
        self.setForeground(1, QtGui.QBrush(QtGui.QColor("#5f6b77")))
        self.setText(1, "Updated " + relativeDate(self.repo.lastupdated()))

navigatorInstance = NavigatorDialog()


