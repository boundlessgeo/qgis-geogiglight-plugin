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

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import os
from collections import defaultdict
from qgis.core import *
from qgis.gui import *
from PyQt4 import QtGui, QtCore
from geogig.gui.dialogs.diffviewerdialog import DiffViewerDialog
from geogig.gui.dialogs.createbranch import CreateBranchDialog
from geogig.gui.executor import execute
from geogig.gui.dialogs.htmldialog import HtmlDialog
from geogig import config
from geogig.tools.layertracking import getProjectLayerForGeoGigLayer, getTrackingInfo
from functools import partial
from geogig.repowatcher import repoWatcher
from geogig.tools.layers import hasLocalChanges, addDiffLayer
from geogig.tools.utils import tempFilename, loadLayerNoCrsDialog
from qgis.utils import iface
from geogig.gui.dialogs.conflictdialog import ConflictDialog


def icon(f):
    return QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                            os.pardir, os.pardir, "ui", "resources", f))

resetIcon = icon("reset.png")
branchIcon = icon("branch-active.png")
newBranchIcon = icon("create_branch.png")
diffIcon = icon("diff-selected.png")
deleteIcon = icon("delete.gif")
infoIcon = icon("repo-summary.png")
tagIcon = icon("tag.gif")
resetIcon = icon("reset.png")
mergeIcon = icon("merge-24.png")

class HistoryViewer(QtGui.QTreeWidget):

    def __init__(self, showContextMenu = True):
        super(HistoryViewer, self).__init__()
        self.repo = None
        self.layername = None
        self.initGui(showContextMenu)

    def initGui(self, showContextMenu):
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.header().setStretchLastSection(True)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.header().setVisible(False)
        if showContextMenu:
            self.customContextMenuRequested.connect(self.showPopupMenu)
        self.itemExpanded.connect(self._itemExpanded)

    def getRef(self):
        selected = self.selectedItems()
        if len(selected) == 1:
            return selected[0].ref

    def changeVersion(self, repo, layer, commit):
        if hasLocalChanges(layer):
            QtGui.QMessageBox.warning(config.iface.mainWindow(), 'Cannot change version',
                "There are local changes that would be overwritten.\n"
                "Revert them before changing version.",
                QtGui.QMessageBox.Ok)
        else:
            tracking = getTrackingInfo(layer)
            repo.checkoutlayer(tracking.geopkg, tracking.layername, None, commit)
            config.iface.messageBar().pushMessage("GeoGig", "Layer has been updated to version %s" % commit,
                                                   level=QgsMessageBar.INFO,
                                                   duration=5)
            layer.reload()
            layer.triggerRepaint()
            repoWatcher.repoChanged.emit(repo)
            repoWatcher.layerUpdated.emit(layer)

    def showPopupMenu(self, point):
        selected = self.selectedItems()
        if len(selected) == 1:
            item = selected[0]
            if isinstance(item, CommitTreeItem):
                trees = self.repo.trees(item.commit.commitid)
                changeVersionActions = []
                for tree in trees:
                    layer = getProjectLayerForGeoGigLayer(self.repo.url, tree)
                    if layer is not None:
                        changeVersionActions.append(QtGui.QAction(resetIcon, "Change '%s' layer to this version" % tree, None))
                        changeVersionActions[-1].triggered.connect(partial(self.changeVersion, self.repo, layer, item.commit.commitid))
                menu = QtGui.QMenu()
                describeAction = QtGui.QAction(infoIcon, "Show detailed description of this version", None)
                describeAction.triggered.connect(lambda: self.describeVersion(item.commit))
                menu.addAction(describeAction)
                diffAction = QtGui.QAction(diffIcon, "Show changes introduced by this version...", None)
                diffAction.triggered.connect(lambda: self.showDiffs(item.commit))
                menu.addAction(diffAction)
                exportDiffAction = QtGui.QAction(diffIcon, "Export changes introduced by this version as new layer", None)
                exportDiffAction.triggered.connect(lambda: self.exportDiffs(item.commit))
                menu.addAction(exportDiffAction)
                createBranchAction = QtGui.QAction(newBranchIcon, "Create new branch at this version...", None)
                createBranchAction.triggered.connect(lambda: self.createBranch(item.commit.commitid))
                menu.addAction(createBranchAction)
                createTagAction = QtGui.QAction(tagIcon, "Create new tag at this version...", None)
                createTagAction.triggered.connect(lambda: self.createTag(item))
                menu.addAction(createTagAction)
                deleteTagsAction = QtGui.QAction(tagIcon, "Delete tags at this version", None)
                deleteTagsAction.triggered.connect(lambda: self.deleteTags(item))
                menu.addAction(deleteTagsAction)
                if changeVersionActions:
                    menu.addSeparator()
                    for action in changeVersionActions:
                        menu.addAction(action)
                point = self.mapToGlobal(point)
                menu.exec_(point)
            elif isinstance(item, BranchTreeItem):
                menu = QtGui.QMenu()
                mergeActions = []
                menu = QtGui.QMenu()
                for branch in self.repo.branches():
                    if branch != item.branch:
                        mergeAction = QtGui.QAction(mergeIcon, branch, None)
                        mergeAction.triggered.connect(partial(self.mergeInto, branch, item.branch))
                        mergeActions.append(mergeAction)
                if mergeActions:
                    mergeMenu = QtGui.QMenu("Merge this branch into")
                    mergeMenu.setIcon(mergeIcon)
                    menu.addMenu(mergeMenu)
                    for action in mergeActions:
                        mergeMenu.addAction(action)
                if self.topLevelItemCount() > 1 and item.branch != "master":
                    deleteAction = QtGui.QAction("Delete this branch", None)
                    deleteAction.triggered.connect(lambda: self.deleteBranch(item.text(0)))
                    menu.addAction(deleteAction)
                if not menu.isEmpty():
                    point = self.mapToGlobal(point)
                    menu.exec_(point)
        elif len(selected) == 2:
            if isinstance(selected[0], CommitTreeItem) and isinstance(selected[1], CommitTreeItem):
                menu = QtGui.QMenu()
                diffAction = QtGui.QAction(diffIcon, "Show changes between selected versions...", None)
                diffAction.triggered.connect(lambda: self.showDiffs(selected[0].commit, selected[1].commit))
                menu.addAction(diffAction)
                point = self.mapToGlobal(point)
                menu.exec_(point)

    def _itemExpanded(self, item):
        if item is not None and isinstance(item, BranchTreeItem):
            item.populate()

    def mergeInto(self, mergeInto, branch):
        conflicts = self.repo.merge(branch, mergeInto)
        if conflicts:
            ret = QtGui.QMessageBox.warning(iface.mainWindow(), "Error while syncing",
                                      "There are conflicts between local and remote changes.\n"
                                      "Do you want to continue and fix them?",
                                      QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if ret == QtGui.QMessageBox.No:
                self.repo.closeTransaction(conflicts[0].transactionId)
                return

            dlg = ConflictDialog(conflicts)
            dlg.exec_()
            solved, resolvedConflicts = dlg.solved, dlg.resolvedConflicts
            if not solved:
                self.repo.closeTransaction(conflicts[0].transactionId)
                return
            for conflict, resolution in zip(conflicts, resolvedConflicts.values()):
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
                "<p><b>Changes added by this version </b>:"
                "<ul><li><b><font color='#FBB117'>%i features modified</font></b></li>"
                "<li><b><font color='green'>%i features added</font></b></li>"
                "<li><b><font color='red'>%i features deleted</font></b></li></ul></p>"
                % (commit.commitid, commit.authorname, commit.authordate.strftime(" %m/%d/%y %H:%M"),
                   commit.message.replace("\n", "<br>"),commit.modified, commit.added,
                   commit.removed))
        dlg = HtmlDialog("Version description", html, self)
        dlg.exec_()


    def exportDiffs(self, commit):
        for tree in self.repo.trees(commit.commitid):
            addDiffLayer(self.repo, tree, commit)


    def showDiffs(self, commit):
        dlg = DiffViewerDialog(self, self.repo, commit.parent, commit)
        dlg.exec_()


    def createTag(self, item):
        tagname, ok = QtGui.QInputDialog.getText(self, 'Tag name',
                                              'Enter the tag name:')
        if ok:
            self.repo.createtag(item.commit.commitid, tagname)
            w = self.itemWidget(item, 0)
            w.tags.append(tagname)
            w.updateText()

    def deleteTags(self, item):
        w = self.itemWidget(item, 0)
        for tag in w.tags:
            self.repo.deletetag(tag)
        w.tags = []
        w.updateText()

    def createBranch(self, ref):
        text, ok = QtGui.QInputDialog.getText(self, 'Title',
                                              'Enter the name for the new branch:')
        if ok:
            self.repo.createbranch(ref, text)
            repoWatcher.repoChanged.emit(self.repo)

    def deleteBranch(self, branch):
        ret = QtGui.QMessageBox.question(self, 'Delete Branch',
                    'Are you sure you want to delete this branch?',
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                    QtGui.QMessageBox.No)
        if ret == QtGui.QMessageBox.No:
            return

        self.repo.deletebranch(branch)
        repoWatcher.repoChanged.emit(self.repo)

    def updateContent(self, repo, layername = None):
        self.repo = repo
        self.layername = layername
        self.clear()
        branches = repo.branches()
        for branch in branches:
            item = BranchTreeItem(branch, repo, self.layername)
            self.addTopLevelItem(item)
        self.resizeColumnToContents(0)



class BranchTreeItem(QtGui.QTreeWidgetItem):

    def __init__(self, branch, repo, path):
        QtGui.QTreeWidgetItem.__init__(self)
        self.branch = branch
        self.ref = branch
        self.repo = repo
        self.path = path
        self.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.ShowIndicator)
        self.setText(0, branch)
        self.setIcon(0, branchIcon)

    def populate(self):
        if not self.childCount():
            tags = defaultdict(list)
            for k, v in self.repo.tags().iteritems():
                tags[v].append(k)
            commits = self.repo.log(until = self.branch, limit = 100, path = self.path)
            for commit in commits:
                item = CommitTreeItem(commit)
                self.addChild(item)
                w = CommitTreeItemWidget(commit, tags.get(commit.commitid, []))
                self.treeWidget().setItemWidget(item, 0, w)
            self.treeWidget().resizeColumnToContents(0)


class CommitTreeItemWidget(QtGui.QLabel):
    def __init__(self, commit, tags):
        QtGui.QTextEdit.__init__(self)
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


class CommitTreeItem(QtGui.QTreeWidgetItem):

    def __init__(self, commit):
        QtGui.QListWidgetItem.__init__(self)
        self.commit = commit
        self.ref = commit.commitid

class HistoryViewerDialog(QtGui.QDialog):

    def __init__(self, repo, layer):
        self.repo = repo
        self.layer = layer
        self.ref = None
        QtGui.QDialog.__init__(self, config.iface.mainWindow(),
                               QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        execute(self.initGui)

    def initGui(self):
        layout = QtGui.QVBoxLayout()
        self.history = HistoryViewer(False)
        self.history.updateContent(self.repo, self.layer)
        layout.addWidget(self.history)
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Close)
        buttonBox.accepted.connect(self.okPressed)
        buttonBox.rejected.connect(self.cancelPressed)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.resize(400, 500)
        self.setWindowTitle("Repository history")

    def okPressed(self):
        selected = self.history.getRef()
        if selected is None:
            QtGui.QMessageBox.warning(self, 'No reference selected',
                    "Select a version or branch from the from the history tree.",
                    QtGui.QMessageBox.Ok)
        else:
            self.ref = selected
            self.close()

    def cancelPressed(self):
        self.ref = None
        self.close()
