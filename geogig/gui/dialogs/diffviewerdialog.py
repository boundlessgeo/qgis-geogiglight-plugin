# -*- coding: utf-8 -*-

"""
***************************************************************************
    diffviewerdialog.py
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
from PyQt4 import QtGui, QtCore, uic
from qgis.core import *
from qgis.gui import *
from geogig.gui.dialogs.geogigref import RefPanel
from geogig import config
from geogig.gui.executor import execute
from geogig.gui.dialogs.geometrydiffviewerdialog import GeometryDiffViewerDialog
import sys
from geogig.geogigwebapi.diff import *
from geogig.geogigwebapi.commit import Commit

MODIFIED, ADDED, REMOVED = "M", "A", "R"

layerIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "layer_group.gif"))
featureIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "geometry.png"))
addedIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "added.png"))
removedIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "removed.png"))
modifiedIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "modified.gif"))

sys.path.append(os.path.dirname(__file__))
pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'diffviewerdialog.ui'))

class DiffViewerDialog(WIDGET, BASE):

    def __init__(self, parent, repo, refa, refb):
        QtGui.QDialog.__init__(self, parent,
                               QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.repo = repo

        self.setupUi(self)

        self.setWindowFlags(self.windowFlags() |
                            QtCore.Qt.WindowSystemMenuHint)

        self.commit1 = refa
        self.commit1Panel = RefPanel(self.repo, refa, onlyCommits = False)
        layout = QtGui.QHBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.addWidget(self.commit1Panel)
        self.commit1Widget.setLayout(layout)
        self.commit2 = refb
        self.commit2Panel = RefPanel(self.repo, refb, onlyCommits = False)
        layout = QtGui.QHBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.addWidget(self.commit2Panel)
        self.commit2Widget.setLayout(layout)
        self.commit1Panel.refChanged.connect(self.refsHaveChanged)
        self.commit2Panel.refChanged.connect(self.refsHaveChanged)

        self.attributesTable.customContextMenuRequested.connect(self.showContextMenu)
        self.featuresTree.itemClicked.connect(self.treeItemClicked)

        self.featuresTree.header().hide()

        self.computeDiffs()
        self.groupBox.adjustSize()

        #self.showMaximized()

    def refsHaveChanged(self):
        self.computeDiffs()

    def treeItemClicked(self, item):
        if item.childCount():
            return
        parent = item.parent().parent()
        if parent is None:
            return
        color = {"MODIFIED": QtGui.QColor(255, 170, 0), "ADDED":QtCore.Qt.green,
                 "REMOVED":QtCore.Qt.red , "NO_CHANGE":QtCore.Qt.white}
        path = parent.text(0) + "/" + item.text(0)
        featurediff = self.changes[path].featurediff()
        self.attributesTable.clear()
        self.attributesTable.verticalHeader().show()
        self.attributesTable.horizontalHeader().show()
        self.attributesTable.setRowCount(len(featurediff))
        self.attributesTable.setVerticalHeaderLabels([a["attributename"] for a in featurediff])
        self.attributesTable.setHorizontalHeaderLabels(["Old value", "New value", "Change type"])
        for i, attrib in enumerate(featurediff):
            try:
                if attrib["changetype"] == "MODIFIED":
                    oldvalue = attrib["oldvalue"]
                    newvalue = attrib["newvalue"]
                elif attrib["changetype"] == "ADDED":
                    newvalue = attrib["newvalue"]
                    oldvalue = ""
                elif attrib["changetype"] == "REMOVED":
                    oldvalue = attrib["oldvalue"]
                    newvalue = ""
                else:
                    oldvalue = newvalue = attrib["oldvalue"]
            except:
                oldvalue = newvalue = ""
            self.attributesTable.setItem(i, 0, DiffItem(oldvalue))
            self.attributesTable.setItem(i, 1, DiffItem(newvalue))
            try:
                qgsgeom1 = QgsGeometry.fromWkt(oldvalue)
                qgsgeom2 = QgsGeometry.fromWkt(newvalue)
                if qgsgeom1 is not None and qgsgeom2 is not None:
                    widget = QtGui.QWidget()
                    btn = QtGui.QPushButton()
                    btn.setText("View detail")
                    btn.clicked.connect(lambda: self.viewGeometryChanges(qgsgeom1, qgsgeom2))
                    label = QtGui.QLabel()
                    label.setText(attrib["changetype"])
                    layout = QtGui.QHBoxLayout(widget)
                    layout.addWidget(label);
                    layout.addWidget(btn);
                    layout.setContentsMargins(0, 0, 0, 0)
                    widget.setLayout(layout)
                    self.attributesTable.setCellWidget(i, 2, widget)
                    self.attributesTable.setItem(i, 2, QtGui.QTableWidgetItem(""))
            except:
                self.attributesTable.setItem(i, 2, QtGui.QTableWidgetItem(attrib["changetype"]))
            for col in range(3):
                self.attributesTable.item(i, col).setBackgroundColor(color[attrib["changetype"]]);
        self.attributesTable.resizeColumnsToContents()
        self.attributesTable.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)

    def viewGeometryChanges(self, g1, g2):
        dlg = GeometryDiffViewerDialog([g1, g2], QgsCoordinateReferenceSystem("EPSG:4326")) #TODO set CRS correctly
        dlg.exec_()


    def computeDiffs(self):
        self.commit1 = self.commit1Panel.getRef()
        self.commit2 = self.commit2Panel.getRef()

        self.featuresTree.clear()
        changes = execute(lambda: self.repo.diff(self.commit1.commitid, self.commit2.commitid))
        layerItems = {}
        layerSubItems = {}
        self.changes = {}
        for c in changes:
            self.changes[c.path] = c
            layername = c.path.split("/")[0]
            featureid = c.path.split("/")[-1]
            if layername not in layerItems:
                item = QtGui.QTreeWidgetItem()
                item.setText(0, layername)
                item.setIcon(0, layerIcon)
                layerItems[layername] = item
                addedItem = QtGui.QTreeWidgetItem()
                addedItem.setText(0, "Added")
                addedItem.setIcon(0, addedIcon)
                removedItem = QtGui.QTreeWidgetItem()
                removedItem.setText(0, "Removed")
                removedItem.setIcon(0, removedIcon)
                modifiedItem = QtGui.QTreeWidgetItem()
                modifiedItem.setText(0, "Modified")
                modifiedItem.setIcon(0, modifiedIcon)
                layerSubItems[layername] = {FEATURE_ADDED: addedItem,
                                            FEATURE_REMOVED: removedItem,
                                            FEATURE_MODIFIED:modifiedItem}
            item = QtGui.QTreeWidgetItem()
            item.setText(0, featureid)
            item.setIcon(0, featureIcon)
            layerSubItems[layername][c.changetype].addChild(item)
        for item in layerItems.values():
            for i in [FEATURE_ADDED, FEATURE_REMOVED, FEATURE_MODIFIED]:
                item.addChild(layerSubItems[layername][i])
                layerSubItems[layername][i].setText(0, "%s [%i features]" %
                                                    (layerSubItems[layername][i].text(0),
                                                     layerSubItems[layername][i].childCount()))

            self.featuresTree.addTopLevelItem(item)
        self.attributesTable.clear()
        self.attributesTable.verticalHeader().hide()
        self.attributesTable.horizontalHeader().hide()


    def reject(self):
        QtGui.QDialog.reject(self)


class DiffItem(QtGui.QTableWidgetItem):

    def __init__(self, value):
        self.value = value
        if value is None:
            s = ""
        elif isinstance(value, basestring):
            s = value
        else:
            s = str(value)
        try:
            geom = QgsGeometry.fromWkt(value)
            if geom is not None:
                s = value.split("(")[0]
        except:
            pass
        QtGui.QTableWidgetItem.__init__(self, s)
