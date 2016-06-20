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
from PyQt4 import QtGui, QtCore
from geogig.tools.layertracking import updateTrackedLayers
from geogig.gui.dialogs.diffviewerdialog import DiffViewerDialog
from geogig.gui.dialogs.createbranch import CreateBranchDialog
from geogig.gui.executor import execute
from geogig.gui.dialogs.htmldialog import HtmlDialog
from geogig import config

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

class HistoryViewer(QtGui.QTreeWidget):

    repoChanged = QtCore.pyqtSignal()
    headChanged = QtCore.pyqtSignal()

    def __init__(self):
        super(HistoryViewer, self).__init__()
        self.repo = None
        self._filterLayers = None
        self.initGui()

    def initGui(self):
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.header().setStretchLastSection(True)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.header().setVisible(False)
        self.customContextMenuRequested.connect(self.showPopupMenu)
        self.itemExpanded.connect(self._itemExpanded)

    def setFilterLayers(self, layers):
        self._filterLayers = layers
        for i in xrange(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.childCount():
                item.takeChildren()
                item.populate()

    def getFilterLayers(self):
        return self._filterLayers

    filterLayers = property(getFilterLayers, setFilterLayers)

    def showPopupMenu(self, point):
        selected = self.selectedItems()
        if len(selected) == 1:
            item = selected[0]
            if isinstance(item, CommitTreeItem):
                menu = QtGui.QMenu()
                describeAction = QtGui.QAction(infoIcon, "Show detailed description of this version", None)
                describeAction.triggered.connect(lambda: self.describeVersion(item.commit))
                menu.addAction(describeAction)
                diffAction = QtGui.QAction(diffIcon, "Show changes introduced by this version...", None)
                diffAction.triggered.connect(lambda: self.showDiffs(item.commit))
                menu.addAction(diffAction)
                createBranchAction = QtGui.QAction(newBranchIcon, "Create new branch at this version...", None)
                createBranchAction.triggered.connect(lambda: self.createBranch(item.commit.commitid))
                menu.addAction(createBranchAction)
                createTagAction = QtGui.QAction(tagIcon, "Create new tag at this version...", None)
                createTagAction.triggered.connect(lambda: self.createTag(item))
                menu.addAction(createTagAction)
                deleteTagsAction = QtGui.QAction(tagIcon, "Delete tags at this version", None)
                deleteTagsAction.triggered.connect(lambda: self.deleteTags(item))
                menu.addAction(deleteTagsAction)
                point = self.mapToGlobal(point)
                menu.exec_(point)
            elif isinstance(item, BranchTreeItem):
                menu = QtGui.QMenu()
                deleteAction = QtGui.QAction(deleteIcon, "Delete this branch", None)
                deleteAction.triggered.connect(lambda: self.deleteBranch(item.text(0)))
                menu.addAction(deleteAction)
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

    def describeVersion(self, commit):
        html = ("<p><b>Author:</b> %s </p>"
                "<p><b>Created at:</b> %s</p>"
                "<p><b>Description message:</b> %s</p>"
                "<p><b>Changes added by this version </b>:"
                "<ul><li><b><font color='#FBB117'>%i features modified</font></b></li>"
                "<li><b><font color='green'>%i features added</font></b></li>"
                "<li><b><font color='red'>%i features deleted</font></b></li></ul></p>"
                % (commit.authorname, commit.authordate.strftime(" %m/%d/%y %H:%M"),
                   commit.message.replace("\n", "<br>"),commit.modified, commit.added,
                   commit.removed))
        dlg = HtmlDialog("Version description", html, self)
        dlg.exec_()


    def showDiffs(self, commita, commitb = None):
        if commitb is None:
            commitb = commita
            commita = commita.parent
        else:
            pass
        dlg = DiffViewerDialog(self, self.repo, commita, commitb)
        dlg.exec_()


    def createTag(self, item):
        tagname, ok = QtGui.QInputDialog.getText(self, 'Tag name',
                                              'Enter the tag name:')
        if ok:
            self.repo.createtag(item.commit.commitid, tagname, tagname)
            w = self.itemWidget(item, 0)
            w.tags = [tagname]
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
            item = BranchTreeItem(text, self.repo)
            self.addTopLevelItem(item)

    def deleteBranch(self, branch):
        ret = QtGui.QMessageBox.question(self, 'Delete Branch',
                    'Are you sure you want to delete this branch?',
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                    QtGui.QMessageBox.No)
        if ret == QtGui.QMessageBox.No:
            return

        self.repo.deletebranch(branch)
        for i in xrange(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.text(0) == branch:
                self.takeTopLevelItem(i)
                return

    def updateContent(self, repo):
        self.repo = repo
        self.clear()
        branches = repo.branches()
        for branch in branches:
            item = BranchTreeItem(branch, repo)
            self.addTopLevelItem(item)
        self.resizeColumnToContents(0)


    def updateCurrentBranchItem(self):
        for i in xrange(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.isCurrentBranch:
                item.takeChildren()
                item.populate()


class BranchTreeItem(QtGui.QTreeWidgetItem):

    def __init__(self, branch, repo):
        QtGui.QTreeWidgetItem.__init__(self)
        self.branch = branch
        self.repo = repo
        self.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.ShowIndicator)
        self.setText(0, branch)
        self.setIcon(0, branchIcon)

    def populate(self):
        if not self.childCount():
            tags = defaultdict(list)
            for k, v in self.repo.tags().iteritems():
                tags[v].append(k)
            commits = self.repo.log(until = self.branch, path = self.treeWidget().filterLayers)
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

class HistoryViewerDialog(QtGui.QDialog):

    def __init__(self, repo, layer):
        self.repo = repo
        self.layer = layer
        QtGui.QDialog.__init__(self, config.iface.mainWindow(),
                               QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        execute(self.initGui)

    def initGui(self):
        layout = QtGui.QVBoxLayout()
        history = HistoryViewer()
        history.updateContent(self.repo.repo())
        history.filterLayers = [self.layer]
        layout.addWidget(history)

        self.setLayout(layout)

        self.resize(400, 500)
        self.setWindowTitle("Repository history")
