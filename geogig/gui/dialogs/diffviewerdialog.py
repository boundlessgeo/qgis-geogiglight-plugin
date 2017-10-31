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
from builtins import str
from builtins import range

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import os
import sys

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import (QHBoxLayout,
                                 QTableWidgetItem,
                                 QWidget,
                                 QPushButton,
                                 QLabel,
                                 QHeaderView,
                                 QTreeWidgetItem,
                                 QDialog
                                )
from qgis.core import QgsGeometry, QgsCoordinateReferenceSystem

from geogig import config
from geogig.gui.dialogs.geogigref import RefPanel
from qgiscommons2.gui import execute
from geogig.gui.dialogs.geometrydiffviewerdialog import GeometryDiffViewerDialog
from geogig.geogigwebapi.diff import FEATURE_MODIFIED, FEATURE_ADDED, FEATURE_REMOVED
from geogig.geogigwebapi.commit import Commit

MODIFIED, ADDED, REMOVED = "M", "A", "R"

layerIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "layer_group.svg"))
featureIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "geometry.png"))
addedIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "added.png"))
removedIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "removed.png"))
modifiedIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "modified.gif"))

sys.path.append(os.path.dirname(__file__))
pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'diffviewerdialog.ui'))

class DiffViewerDialog(WIDGET, BASE):

    def __init__(self, parent, repo, refa, refb):
        super(DiffViewerDialog, self).__init__(parent,
                               Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.repo = repo

        self.setupUi(self)

        self.setWindowFlags(self.windowFlags() |
                            Qt.WindowSystemMenuHint)

        self.commit1 = refa
        self.commit1Panel = RefPanel(self.repo, refa)
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.addWidget(self.commit1Panel)
        self.commit1Widget.setLayout(layout)
        self.commit2 = refb
        self.commit2Panel = RefPanel(self.repo, refb)
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.addWidget(self.commit2Panel)
        self.commit2Widget.setLayout(layout)
        self.commit1Panel.refChanged.connect(self.refsHaveChanged)
        self.commit2Panel.refChanged.connect(self.refsHaveChanged)

        self.featuresTree.currentItemChanged.connect(self.treeItemChanged)

        self.featuresTree.header().hide()

        self.computeDiffs()
        self.groupBox.adjustSize()


    def refsHaveChanged(self):
        self.computeDiffs()

    def treeItemChanged(self, current, previous):
        qgsgeom1 = None
        qgsgeom2 = None
        crs = "EPSG:4326"
        if not isinstance(current, FeatureItem):
            self.attributesTable.clear()
            self.attributesTable.setRowCount(0)
            return
        color = {"MODIFIED": QColor(255, 170, 0), "ADDED":Qt.green,
                 "REMOVED":Qt.red , "NO_CHANGE":Qt.white}
        path = current.layername + "/" + current.featureid
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
                self.attributesTable.setItem(i, 2, QTableWidgetItem(""))
                if qgsgeom1 is None or qgsgeom2 is None:
                    if "crs" in attrib:
                        crs = attrib["crs"]
                    qgsgeom1 = QgsGeometry.fromWkt(oldvalue)
                    qgsgeom2 = QgsGeometry.fromWkt(newvalue)
                    if qgsgeom1 is not None and qgsgeom2 is not None:
                        widget = QWidget()
                        btn = QPushButton()
                        btn.setText("View detail")
                        btn.clicked.connect(lambda: self.viewGeometryChanges(qgsgeom1, qgsgeom2, crs))
                        label = QLabel()
                        label.setText(attrib["changetype"])
                        layout = QHBoxLayout(widget)
                        layout.addWidget(label);
                        layout.addWidget(btn);
                        layout.setContentsMargins(0, 0, 0, 0)
                        widget.setLayout(layout)
                        self.attributesTable.setCellWidget(i, 2, widget)
                    else:
                        self.attributesTable.setItem(i, 2, QTableWidgetItem(attrib["changetype"]))
                else:
                    self.attributesTable.setItem(i, 2, QTableWidgetItem(attrib["changetype"]))
            except:
                self.attributesTable.setItem(i, 2, QTableWidgetItem(attrib["changetype"]))
            for col in range(3):
                self.attributesTable.item(i, col).setBackgroundColor(color[attrib["changetype"]]);
        self.attributesTable.resizeColumnsToContents()
        self.attributesTable.horizontalHeader().setResizeMode(QHeaderView.Stretch)

    def viewGeometryChanges(self, g1, g2, crs):
        dlg = GeometryDiffViewerDialog([g1, g2], QgsCoordinateReferenceSystem(crs))
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
                item = QTreeWidgetItem()
                item.setText(0, layername)
                item.setIcon(0, layerIcon)
                layerItems[layername] = item
                addedItem = QTreeWidgetItem()
                addedItem.setText(0, "Added")
                addedItem.setIcon(0, addedIcon)
                removedItem = QTreeWidgetItem()
                removedItem.setText(0, "Removed")
                removedItem.setIcon(0, removedIcon)
                modifiedItem = QTreeWidgetItem()
                modifiedItem.setText(0, "Modified")
                modifiedItem.setIcon(0, modifiedIcon)
                layerSubItems[layername] = {FEATURE_ADDED: addedItem,
                                            FEATURE_REMOVED: removedItem,
                                            FEATURE_MODIFIED:modifiedItem}
            item = FeatureItem(layername, featureid)
            layerSubItems[layername][c.changetype].addChild(item)
        for layername, item in layerItems.iteritems():
            for i in [FEATURE_ADDED, FEATURE_REMOVED, FEATURE_MODIFIED]:
                subItem = layerSubItems[layername][i]
                item.addChild(subItem)
                subItem.setText(0, "%s [%i features]" %
                                                    (subItem.text(0),
                                                     subItem.childCount()))

            self.featuresTree.addTopLevelItem(item)
        self.attributesTable.clear()
        self.attributesTable.verticalHeader().hide()
        self.attributesTable.horizontalHeader().hide()
        
        self.featuresTree.expandAll()

    def reject(self):
        QDialog.reject(self)

class FeatureItem(QTreeWidgetItem):
    def __init__(self, layername, featureid):
        QTreeWidgetItem.__init__(self)
        self.setIcon(0, featureIcon)
        self.layername = layername
        self.featureid = featureid
        self.setText(0, featureid)

class DiffItem(QTableWidgetItem):

    def __init__(self, value):
        self.value = value
        if value is None:
            s = ""
        elif isinstance(value, str):
            s = value
        else:
            s = str(value)
        try:
            geom = QgsGeometry.fromWkt(value)
            if geom is not None:
                s = value.split("(")[0]
        except:
            pass
        QTableWidgetItem.__init__(self, s)
