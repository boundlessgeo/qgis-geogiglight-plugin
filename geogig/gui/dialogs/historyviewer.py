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

from qgis.PyQt.QtCore import Qt, pyqtSignal, QPoint, QRectF
from qgis.PyQt.QtGui import QIcon, QImage, QPixmap, QPainter, QColor, QPainterPath, QPen, QBrush
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
                                 QSplitter,
                                 QWidget
                                )
from qgis.gui import QgsMessageBar
from qgis.utils import iface
from qgis.core import QgsApplication

from geogig import config
from geogig.repowatcher import repoWatcher

from geogig.extlibs.qgiscommons2.gui import execute
from geogig.gui.dialogs.diffviewerdialog import DiffViewerDialog
from geogig.gui.dialogs.conflictdialog import ConflictDialog
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
        self.setHeaderLabels(["Graph", "Description", "Changes", "Author", "Date", "CommitID"])
        if showContextMenu:
            self.customContextMenuRequested.connect(self._showPopupMenu)

    def getRef(self):
        selected = self.selectedItems()
        if len(selected) == 1:
            return selected[0].ref

    def exportVersion(self, repo, layer, commitId):
        checkoutLayer(repo, layer, None, commitId)

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

    def createBranch(self, ref):
        text, ok = QInputDialog.getText(self, 'Create New Branch',
                                              'Enter the name for the new branch:')
        if ok:
            branchName =  text.replace(" ", "_")
            self.repo.createbranch(ref, branchName)
            repoWatcher.repoChanged.emit(self.repo)

    def computeGraph(self):
        self.commitRows = {}
        self.commitColumns = {}
        for i, commit in enumerate(self.commits):
            self.commitRows[commit.commitid] = i + 1
        used = []
        self.maxCol = 0
        def addCommit(commit, col):
            used.append(commit.commitid)
            self.commitColumns[commit.commitid] = col
            try:
                for i, parent in enumerate(commit.parents):
                    if parent.commitid not in used:
                        if i == 0:
                            nextCol = col
                        else:
                            self.maxCol = self.maxCol + 1
                            nextCol = self.maxCol
                        addCommit(parent, nextCol)
            except:
                pass

        addCommit(self.commits[0], 0)

        cols = 0

        for i, commit in enumerate(reversed(self.commits)):
            try:
                parent = commit.parent
                if parent.children[0].commitid == commit.commitid:
                    self.commitColumns[commit.commitid] = self.commitColumns[parent.commitid]
                else:
                    col = self.commitColumns[commit.commitid]
                    self.commitColumns[commit.commitid] = min(col, cols)
            except:
                pass

            if  commit.isFork():
                cols += 1
            elif commit.isMerge():
                cols -= 1
            elif parent.isMerge() and parent.isFork():
                cols -= 1

    COMMIT_GRAPH_HEIGHT = 20
    COMMIT_GRAPH_WIDTH = 100
    COLUMN_SEPARATION = 20
    RADIUS = 5
    PEN_WIDTH = 4

    COLORS = [QColor(Qt.red),
                QColor(Qt.green),
                QColor(Qt.blue),
                QColor(Qt.black),
                QColor(Qt.darkRed),
                QColor(Qt.darkGreen),
                QColor(Qt.darkBlue),
                QColor(Qt.cyan),
                QColor(Qt.magenta)]

    def createGraphImage(self):
        self.image = QPixmap(self.COMMIT_GRAPH_WIDTH, 1000).toImage()
        qp = QPainter(self.image)
        qp.fillRect(QRectF(0, 0, self.COMMIT_GRAPH_WIDTH, 1000), Qt.white);
        qp.begin(self.image)
        self.drawLines(qp)
        qp.end()

    def _columnColor(self, column):
        if column in self.columnColor:
            color = self.columnColor[column]
        else:
            self.lastColor += 1
            color = self.COLORS[self.lastColor % len(self.COLORS)]
            self.columnColor[column] = color
        return color

    def drawLine(self, painter, commit, parent):
        commitRow = self.commitRows[commit.commitid]
        commitCol = self.commitColumns[commit.commitid]
        parentRow = self.commitRows[parent.commitid]
        parentCol = self.commitColumns[parent.commitid]
        commitX = self.RADIUS * 3 + commitCol * self.COLUMN_SEPARATION
        parentX = self.RADIUS * 3 + parentCol * self.COLUMN_SEPARATION
        commitY = commitRow * self.COMMIT_GRAPH_HEIGHT
        parentY = parentRow * self.COMMIT_GRAPH_HEIGHT
        path = QPainterPath()

        color = self._columnColor(parentCol)
        if parentCol != commitCol:
            if parent.isFork() and commit.parents[0].commitid == parent.commitid:
                path.moveTo(commitX, commitY)
                path.lineTo(commitX, parentY)
                path.lineTo(parentX + self.RADIUS + 1, parentY)
                color = self._columnColor(commitCol)
            else:
                path2 = QPainterPath()
                path2.moveTo(commitX + self.RADIUS + 1, commitY)
                path2.lineTo(commitX + self.RADIUS + self.COLUMN_SEPARATION / 2, commitY + self.COLUMN_SEPARATION / 3)
                path2.lineTo(commitX + self.RADIUS + self.COLUMN_SEPARATION / 2, commitY - self.COLUMN_SEPARATION / 3)
                path2.lineTo(commitX + + self.RADIUS + 1, commitY)
                painter.setBrush(color)
                painter.setPen(color)
                painter.drawPath(path2)
                path.moveTo(commitX + self.RADIUS + self.COLUMN_SEPARATION / 2, commitY)
                path.lineTo(parentX, commitY)
                path.lineTo(parentX, parentY)

            if parent.isFork():
                del self.columnColor[commitCol]

        else:
            path.moveTo(commitX, commitY)
            path.lineTo(parentX, parentY)

        pen = QPen(color, self.PEN_WIDTH, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin)
        painter.strokePath(path, pen)

        if not commit.commitid in self.linked:
            y = commitRow * self.COLUMN_SEPARATION
            x = self.RADIUS * 3 + commitCol * self.COLUMN_SEPARATION
            painter.setPen(color)
            painter.setBrush(color)
            painter.drawEllipse(QPoint(x, y), self.RADIUS, self.RADIUS)
            self.linked.append(commit.commitid)

    def drawLines(self, painter):
        self.linked = []
        self.columnColor = {}
        self.lastColor = -1
        def linkCommit(commit):
            for parent in commit.parents:
                try:
                    self.drawLine(painter, commit, parent)
                    if parent.commitid not in self.linked:
                        linkCommit(parent)
                except:
                    continue

        linkCommit(self.commits[0])

        y = len(self.commits) * self.COLUMN_SEPARATION
        x = self.RADIUS * 3
        painter.setPen(self.COLORS[0])
        painter.setBrush(self.COLORS[0])
        painter.drawEllipse(QPoint(x, y), self.RADIUS, self.RADIUS)

    def graphSlice(self, row, width):
        return self.image.copy(0, (row - .5) * self.COMMIT_GRAPH_HEIGHT,
                               width, self.COMMIT_GRAPH_HEIGHT)

    def updateContent(self, repo, branch, layername = None):
        self.repo = repo
        self.branch = branch
        self.layername = layername
        self.clear()
        tags = defaultdict(list)
        for k, v in self.repo.tags().items():
            tags[v].append(k)
        self.commits = self.repo.log(until = branch, path = layername)
        self.computeGraph()
        self.createGraphImage()
        width = self.COLUMN_SEPARATION * (max(self.commitColumns.values()) + 1) + self.RADIUS
        for i, commit in enumerate(self.commits):
            item = CommitTreeItem(commit)
            item.setText(3, commit.authorname)
            item.setText(4, commit.authordate.strftime(" %m/%d/%y %H:%M"))
            item.setText(5, commit.commitid)
            self.addTopLevelItem(item)
            w = CommitMessageItemWidget(commit, tags.get(commit.commitid, []))
            self.setItemWidget(item, 1, w)
            w = CommitChangesItemWidget(commit)
            self.setItemWidget(item, 2, w)
            img = self.graphSlice(i + 1, width)
            w = GraphWidget(img)
            w.setFixedHeight(self.COMMIT_GRAPH_HEIGHT)
            w.setFixedWidth(self.COMMIT_GRAPH_WIDTH)
            self.setItemWidget(item, 0, w)

        for i in range(5):
            self.resizeColumnToContents(i)

        self.expandAll()

        #self.header().resizeSection(0, width)

class GraphWidget(QWidget):

    def __init__(self, img):
        QWidget.__init__(self)
        self.setFixedWidth(img.width())
        self.img = img

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.begin(self);
        painter.drawImage(0, 0, self.img)
        painter.end()

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
        layout = QVBoxLayout()
        branch = self.branch or "master"
        self.history = HistoryViewer()
        self.history.updateContent(self.repo, layername = self.layer, branch = branch)
        layout.addWidget(self.history)
        if self.showButtons:
            buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
            buttonBox.accepted.connect(self.okPressed)
            buttonBox.rejected.connect(self.cancelPressed)
            layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.resize(800, 600)
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
