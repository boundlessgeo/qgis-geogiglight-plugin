# -*- coding: utf-8 -*-

"""
***************************************************************************
    historyviewer.py
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
from builtins import zip
from builtins import str

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import sqlite3
from functools import partial
from collections import defaultdict

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (QTreeWidget,
                                 QAbstractItemView,
                                 QMessageBox,
                                 QAction,
                                 QMenu,
                                 QInputDialog,
                                 QTreeWidgetItem,
                                 QLabel,
                                 QTextEdit,
                                 QListWidgetItem,
                                 QDialog,
                                 QVBoxLayout,
                                 QHBoxLayout,
                                 QDialogButtonBox,
                                 QApplication,
                                 QPushButton,
                                 QSplitter
                                )
from qgis.gui import QgsMessageBar
from qgis.utils import iface
from qgis.core import QgsApplication

from geogig import config
from geogig.repowatcher import repoWatcher

from geogig.extlibs.qgiscommons2.gui import execute
from geogig.gui.dialogs.diffviewerdialog import DiffViewerDialog
from geogig.gui.dialogs.conflictdialog import ConflictDialog
from geogig.gui.dialogs.historygraphviewer import GraphView
from geogig.geogigwebapi.commit import Commit, setChildren
from geogig.tools.gpkgsync import checkoutLayer, HasLocalChangesError
from geogig.tools.layertracking import getTrackingInfo
from geogig.tools.layers import hasLocalChanges, addDiffLayers
from geogig.extlibs.qgiscommons2.layers import loadLayerNoCrsDialog
from geogig.extlibs.qgiscommons2.gui import showMessageDialog

def icon(f):
    return QIcon(os.path.join(os.path.dirname(__file__),
                            os.pardir, os.pardir, "ui", "resources", f))

resetIcon = icon("reset.png")
branchIcon = icon("branch.svg")
newBranchIcon = icon("create_branch.png")
diffIcon = icon("diff-selected.png")
deleteIcon = QgsApplication.getThemeIcon('/mActionDeleteSelected.svg')
infoIcon = icon("repo-summary.png")
tagIcon = icon("tag.gif")
resetIcon = icon("reset.png")
mergeIcon = icon("merge-24.png")

class HistoryViewer(QTreeWidget):

    tagsUpdated = pyqtSignal(dict)
    itemSelected = pyqtSignal(list)

    def __init__(self, showContextMenu = True):
        super(HistoryViewer, self).__init__()
        self.repo = None
        self.layername = None
        self.initGui(showContextMenu)
        self.selecting = False

    def initGui(self, showContextMenu):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.header().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setHeaderLabels(["Description", "Changes", "Author", "Date"])
        if showContextMenu:
            self.customContextMenuRequested.connect(self._showPopupMenu)
        self.itemSelectionChanged.connect(self.selectedCommitChanged)

    def selectedCommitChanged(self):
        items = self.selectedItems()
        commits = [item.commit for item in items]
        self.selecting = True
        self.itemSelected.emit(commits)
        self.selecting = False

    def getRef(self):
        selected = self.selectedItems()
        if len(selected) == 1:
            return selected[0].ref

    def exportVersion(self, repo, layer, commitId):
        checkoutLayer(repo, layer, None, commitId)

    def selectCommits(self, commitids):
        if self.selecting:
            return
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item.setSelected(item.commit.commitid in commitids)

    def _showPopupMenu(self, point):
        point = self.mapToGlobal(point)
        self.showPopupMenu(point)

    def showPopupMenu(self, point):
        selected = self.selectedItems()
        if len(selected) == 1:
            item = selected[0]
            trees = self.repo.trees(item.commit.commitid)
            exportVersionActions = []
            for tree in trees:
                exportVersionActions.append(QAction(resetIcon, "Add '%s' layer to QGIS from this commit" % tree, None))
                exportVersionActions[-1].triggered.connect(partial(self.exportVersion, self.repo, tree, item.commit.commitid))
            menu = QMenu()
            diffAction = QAction(diffIcon, "Show changes introduced by this commit...", None)
            diffAction.triggered.connect(lambda: self.showDiffs(item.commit))
            menu.addAction(diffAction)
            exportDiffAction = QAction(diffIcon, "Export changes introduced by this commit as new layer", None)
            exportDiffAction.triggered.connect(lambda: self.exportDiffs(item.commit))
            menu.addAction(exportDiffAction)
            createBranchAction = QAction(newBranchIcon, "Create new branch at this commit...", None)
            createBranchAction.triggered.connect(lambda: self.createBranch(item.commit.commitid))
            menu.addAction(createBranchAction)
            createTagAction = QAction(tagIcon, "Create new tag at this commit...", None)
            createTagAction.triggered.connect(lambda: self.createTag(item))
            menu.addAction(createTagAction)
            deleteTagsAction = QAction(tagIcon, "Delete tags at this commit", None)
            deleteTagsAction.triggered.connect(lambda: self.deleteTags(item))
            menu.addAction(deleteTagsAction)
            if exportVersionActions:
                menu.addSeparator()
                for action in exportVersionActions:
                    menu.addAction(action)
            menu.exec_(point)
        elif len(selected) == 2:
            menu = QMenu()
            diffAction = QAction(diffIcon, "Show changes between selected commits...", None)
            diffAction.triggered.connect(lambda: self.showDiffs(selected[0].commit, selected[1].commit))
            menu.addAction(diffAction)
            exportDiffAction = QAction(diffIcon, "Export changes between selected commits as new layers", None)
            exportDiffAction.triggered.connect(lambda: self.exportDiffs(selected[0].commit, selected[1].commit))
            menu.addAction(exportDiffAction)
            menu.exec_(point)

    def exportDiffs(self, commit, commit2 = None):
        commit2 = commit2 or commit.parent
        layers = self.repo.trees(commit.commitid)
        layers2 = self.repo.trees(commit2.commitid)
        if layers != layers2:
            QMessageBox.warning(config.iface.mainWindow(), 'Cannot export diffs',
                "Diffs cannot be exported for commits that add/remove layers",
                QMessageBox.Ok)
            return

        commit, commit2 = self._sortCommits(commit, commit2)
        addDiffLayers(self.repo, commit, commit2, layers)

    def _sortCommits(self, commit, commit2):
        try:
            if commit2.authordate > commit.authordate:
                return commit2, commit
            else:
                return commit, commit2
        except:
            return commit, commit2

    def showDiffs(self, commit, commit2 = None):
        commit2 = commit2 or commit.parent
        commit, commit2 = self._sortCommits(commit, commit2)

        dlg = DiffViewerDialog(self, self.repo, commit2, commit)
        dlg.exec_()

    def createTag(self, item):
        tagname, ok = QInputDialog.getText(self, 'Tag name',
                                              'Enter the tag name:')
        if ok:
            self.repo.createtag(item.commit.commitid, tagname)
            self.updateTags(item.commit.commitid, tagname)

    def deleteTags(self, item):
        tags = defaultdict(list)
        for k, v in self.repo.tags().items():
            tags[v].append(k)
        for tag in tags[item.commit.commitid]:
            self.repo.deletetag(tag)
        self.updateTags(item.commit.commitid)

    def updateTags(self, commitid, tag=None):
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.commit.commitid == commitid:
                w = self.itemWidget(item, 0)
                if tag is None:
                    w.tags = []
                else:
                    w.tags.append(tag)
                w.updateText()
        tags = defaultdict(list)
        for k, v in self.repo.tags().items():
            tags[v].append(k)
        self.tagsUpdated.emit(tags)

    def createBranch(self, ref):
        text, ok = QInputDialog.getText(self, 'Create New Branch',
                                              'Enter the name for the new branch:')
        if ok:
            branchName =  text.replace(" ", "_")
            self.repo.createbranch(ref, branchName)
            repoWatcher.repoChanged.emit(self.repo)

    def updateContent(self, repo, branch, layername = None):
        self.repo = repo
        self.branch = branch
        self.layername = layername
        self.clear()
        tags = defaultdict(list)
        for k, v in self.repo.tags().items():
            tags[v].append(k)
        commits = self.repo.log(until = branch, path = layername)
        for commit in commits:
            item = CommitTreeItem(commit)
            item.setText(2, commit.authorname)
            item.setText(3, commit.authordate.strftime(" %m/%d/%y %H:%M"))
            self.addTopLevelItem(item)
            w = CommitMessageItemWidget(commit, tags.get(commit.commitid, []))
            self.setItemWidget(item, 0, w)
            w = CommitChangesItemWidget(commit)
            self.setItemWidget(item, 1, w)

        self.resizeColumnToContents(0)
        self.expandAll()
        return commits


class CommitMessageItemWidget(QLabel):
    def __init__(self, commit, tags):
        QLabel.__init__(self)
        self.setWordWrap(False)
        self.tags = tags
        self.commit = commit
        self.updateText()

    def updateText(self):
        if self.tags:
            tags = "&nbsp;" + "&nbsp;".join(['<font color="black" style="background-color:yellow">&nbsp;%s&nbsp;</font>'
                                             % t for t in self.tags]) + "&nbsp;"
        else:
            tags = ""
        text = ('%s %s' %  (tags, self.commit.message.splitlines()[0]))
        self.setText(text)

class CommitChangesItemWidget(QLabel):

    def __init__(self, commit):
        QLabel.__init__(self)
        text = (("<font color='#FBB117'>~%i </font>"
                "<font color='green'>+%i </font>"
                "<font color='red'>-%i</font>") %
                (commit.modified, commit.added, commit.removed))
        self.setText(text)


class CommitTreeItem(QTreeWidgetItem):

    def __init__(self, commit):
        QTreeWidgetItem.__init__(self)
        self.commit = commit
        self.ref = commit.commitid


class HistoryViewerDialog(QDialog):

    def __init__(self, repo, layer = None, branch = None, showButtons = False):
        self.repo = repo
        self.layer = layer
        self.branch = branch
        self.ref = None
        self.showButtons = showButtons
        QDialog.__init__(self, config.iface.mainWindow(),
                               Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        execute(self.initGui)

    def initGui(self):
        layout = QHBoxLayout()
        splitterH = QSplitter(Qt.Horizontal)
        splitterV = QSplitter(Qt.Vertical)
        self.commitDetail = QTextEdit()
        branch = self.branch or "master"
        self.history = HistoryViewer()
        commits = self.history.updateContent(self.repo, layername = self.layer, branch = branch)
        self.graph = GraphView(self)
        self.graph.itemSelected.connect(self.itemSelectedInGraph)
        self.graph.contextMenuRequested.connect(self.contextMenuRequestedInGraph)
        self.history.itemSelected.connect(self.itemSelectedInHistory)
        self.history.tagsUpdated.connect(self.tagsUpdated)
        tags = defaultdict(list)
        for k, v in self.repo.tags().items():
            tags[v].append(k)
        for commit in commits:
            commit.tags = tags.get(commit.commitid, [])
        self.graph.setCommits(commits)
        splitterV.addWidget(self.history)
        splitterV.addWidget(self.commitDetail)
        splitterH.addWidget(splitterV)
        splitterH.addWidget(self.graph)
        layout.addWidget(splitterH)
        if self.showButtons:
            buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
            buttonBox.accepted.connect(self.okPressed)
            buttonBox.rejected.connect(self.cancelPressed)
            layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.resize(800, 600)
        self.setWindowTitle("Repository history")

    def tagsUpdated(self, tags):
        self.graph.updateTags(tags)

    def itemSelectedInHistory(self, commits):
        self.graph.selectCommits(commits)
        self.showCommitDetail(commits[0])

    def itemSelectedInGraph(self, commits):
        self.history.selectCommits(commits)

    def showCommitDetail(self, commit):
        self.commitDetail.setText(str([c.commitid for c in commit.parents]))

    def contextMenuRequestedInGraph(self, point):
        self.history.showPopupMenu(point)

    def okPressed(self):
        selected = self.history.getRef()
        if selected is None:
            QMessageBox.warning(self, 'No reference selected',
                    "Select a commit or branch from the from the history tree.",
                    QMessageBox.Ok)
        else:
            self.ref = selected
            self.close()

    def cancelPressed(self):
        self.ref = None
        self.close()
