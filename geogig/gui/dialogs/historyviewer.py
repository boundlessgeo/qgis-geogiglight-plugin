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

from qgis.PyQt.QtCore import Qt
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
                                 QDialogButtonBox,
                                 QApplication,
                                 QPushButton
                                )
from qgis.gui import QgsMessageBar
from qgis.utils import iface
from qgis.core import QgsApplication

from geogig import config
from geogig.repowatcher import repoWatcher

from qgiscommons2.gui import execute
from geogig.gui.dialogs.diffviewerdialog import DiffViewerDialog
from geogig.gui.dialogs.conflictdialog import ConflictDialog
from geogig.geogigwebapi.commit import Commit
from geogig.tools.gpkgsync import checkoutLayer, HasLocalChangesError
from geogig.tools.layertracking import getTrackingInfo
from geogig.tools.layers import hasLocalChanges, addDiffLayers
from qgiscommons2.layers import loadLayerNoCrsDialog
from qgiscommons2.gui import showMessageDialog

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

    def __init__(self, showContextMenu = True):
        super(HistoryViewer, self).__init__()
        self.repo = None
        self.layername = None
        self.initGui(showContextMenu)

    def initGui(self, showContextMenu):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.header().setStretchLastSection(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.header().setVisible(False)
        if showContextMenu:
            self.customContextMenuRequested.connect(self.showPopupMenu)
        self.itemExpanded.connect(self._itemExpanded)

    def getRef(self):
        selected = self.selectedItems()
        if len(selected) == 1:
            return selected[0].ref

    def exportVersion(self, repo, layer, commitId):
        checkoutLayer(repo, layer, None, commitId)

    def showPopupMenu(self, point):
        selected = self.selectedItems()
        if len(selected) == 1:
            item = selected[0]
            if isinstance(item, CommitTreeItem):
                trees = self.repo.trees(item.commit.commitid)
                exportVersionActions = []
                for tree in trees:
                    exportVersionActions.append(QAction(resetIcon, "Add '%s' layer to QGIS from this commit" % tree, None))
                    exportVersionActions[-1].triggered.connect(partial(self.exportVersion, self.repo, tree, item.commit.commitid))
                menu = QMenu()
                describeAction = QAction(infoIcon, "Show detailed description of this commit", None)
                describeAction.triggered.connect(lambda: self.describeVersion(item.commit))
                menu.addAction(describeAction)
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
                point = self.mapToGlobal(point)
                menu.exec_(point)
            elif isinstance(item, BranchTreeItem):
                mergeActions = []
                menu = QMenu()
                for branch in self.repo.branches():
                    if branch != item.branch:
                        mergeAction = QAction(mergeIcon, branch, None)
                        mergeAction.triggered.connect(partial(self.mergeInto, branch, item.branch))
                        mergeActions.append(mergeAction)
                if mergeActions:
                    mergeMenu = QMenu("Merge this branch into")
                    mergeMenu.setIcon(mergeIcon)
                    menu.addMenu(mergeMenu)
                    for action in mergeActions:
                        mergeMenu.addAction(action)
                if self.topLevelItemCount() > 1 and item.branch != "master":
                    deleteAction = QAction("Delete this branch", None)
                    deleteAction.triggered.connect(lambda: self.deleteBranch(item.text(0)))
                    menu.addAction(deleteAction)
                if not menu.isEmpty():
                    point = self.mapToGlobal(point)
                    menu.exec_(point)
        elif len(selected) == 2:
            if isinstance(selected[0], (CommitTreeItem, BranchTreeItem)) and isinstance(selected[1], (CommitTreeItem, BranchTreeItem)):
                menu = QMenu()
                diffAction = QAction(diffIcon, "Show changes between selected commits...", None)
                diffAction.triggered.connect(lambda: self.showDiffs(selected[0].commit, selected[1].commit))
                menu.addAction(diffAction)
                exportDiffAction = QAction(diffIcon, "Export changes between selected commits as new layers", None)
                exportDiffAction.triggered.connect(lambda: self.exportDiffs(selected[0].commit, selected[1].commit))
                menu.addAction(exportDiffAction)
                point = self.mapToGlobal(point)
                menu.exec_(point)

    def _itemExpanded(self, item):
        if item is not None and isinstance(item, BranchTreeItem):
            item.populate()

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

    def describeVersion(self, commit):
        html = ("<p><b>Full commit Id:</b> %s </p>"
                "<p><b>Author:</b> %s </p>"
                "<p><b>Created at:</b> %s</p>"
                "<p><b>Description message:</b> %s</p>"
                "<p><b>Changes added by this commit </b>:"
                "<ul><li><b><font color='#FBB117'>%i features modified</font></b></li>"
                "<li><b><font color='green'>%i features added</font></b></li>"
                "<li><b><font color='red'>%i features deleted</font></b></li></ul></p>"
                % (commit.commitid, commit.authorname, commit.authordate.strftime(" %m/%d/%y %H:%M"),
                   commit.message.replace("\n", "<br>"),commit.modified, commit.added,
                   commit.removed))
        showMessageDialog("Commit description", html)

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
        for i in range(self.topLevelItemCount()):
            branchItem = self.topLevelItem(i)
            for j in range(branchItem.childCount()):
                commitItem = branchItem.child(j)
                if commitItem.commit.commitid == commitid:
                    w = self.itemWidget(commitItem, 0)
                    if tag is None:
                        w.tags = []
                    else:
                        w.tags.append(tag)
                    w.updateText()

    def createBranch(self, ref):
        text, ok = QInputDialog.getText(self, 'Create New Branch',
                                              'Enter the name for the new branch:')
        if ok:
            branchName =  text.replace(" ", "_")
            self.repo.createbranch(ref, branchName)
            item = BranchTreeItem(branchName, self.repo, self.layername)
            self.addTopLevelItem(item)
            item.populate()
            repoWatcher.repoChanged.emit(self.repo)

    def deleteBranch(self, branch):
        ret = QMessageBox.question(self, 'Delete Branch',
                    'Are you sure you want to delete this branch?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No)
        if ret == QMessageBox.No:
            return

        self.repo.deletebranch(branch)
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.branch == branch:
                self.takeTopLevelItem(i)
                break
        repoWatcher.repoChanged.emit(self.repo)

    def updateContent(self, repo, layername = None, branch = None):
        self.repo = repo
        self.layername = layername
        self.clear()
        if repo is not None:
            branches = repo.branches()
            for b in branches:
                if branch is None or b == branch:
                    item = BranchTreeItem(b, repo, layername)
                    self.addTopLevelItem(item)
                    item.populate()
            self.resizeColumnToContents(0)
        if (branch or layername):
            self.expandAll()

class BranchTreeItem(QTreeWidgetItem):

    def __init__(self, branch, repo, path):
        QTreeWidgetItem.__init__(self)
        self.branch = branch
        self.ref = branch
        self.repo = repo
        self.path = path
        self.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        self.setText(0, branch)
        self.setIcon(0, branchIcon)
        self._commit = None

    @property
    def commit(self):
        if self._commit is None:
            self._commit = Commit.fromref(self.repo, self.branch)
        return self._commit


    def populate(self):
        if not self.childCount():
            tags = defaultdict(list)
            for k, v in self.repo.tags().items():
                tags[v].append(k)
            commits = self.repo.log(until = self.branch, limit = 100, path = self.path)
            if commits:
                self._commit = commits[0]
            for commit in commits:
                item = CommitTreeItem(commit)
                self.addChild(item)
                w = CommitTreeItemWidget(commit, tags.get(commit.commitid, []))
                self.treeWidget().setItemWidget(item, 0, w)
            self.treeWidget().resizeColumnToContents(0)


class CommitTreeItemWidget(QLabel):
    def __init__(self, commit, tags):
        QTextEdit.__init__(self)
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
        size = self.font().pointSize()
        text = ('%s<b><font style="font-size:%spt">%s</font></b>'
            '<br><font color="#5f6b77" style="font-size:%spt"><b>%s</b> by <b>%s</b></font> '
            '<font color="#5f6b77" style="font-size:%spt; background-color:rgb(225,225,225)"> %s </font>' %
            (tags, str(size), self.commit.message.splitlines()[0], str(size - 1),
             self.commit.authorprettydate(), self.commit.authorname, str(size - 1), self.commit.id[:10]))
        self.setText(text)


class CommitTreeItem(QTreeWidgetItem):

    def __init__(self, commit):
        QListWidgetItem.__init__(self)
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
        layout = QVBoxLayout()
        self.history = HistoryViewer()
        self.history.updateContent(self.repo, layername = self.layer, branch = self.branch)
        layout.addWidget(self.history)
        if self.showButtons:
            buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
            buttonBox.accepted.connect(self.okPressed)
            buttonBox.rejected.connect(self.cancelPressed)
            layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.resize(400, 500)
        self.setWindowTitle("Repository history")

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
