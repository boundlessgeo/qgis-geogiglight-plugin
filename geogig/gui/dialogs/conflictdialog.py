# -*- coding: utf-8 -*-

"""
***************************************************************************
    conflictdialog.py
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

from PyQt4 import uic
from PyQt4.QtCore import Qt, QSettings, QSize
from PyQt4.QtGui import (QIcon,
                         QHBoxLayout,
                         QTreeWidgetItem,
                         QMessageBox,
                         QFont,
                         QTableWidgetItem,
                         QPushButton,
                        )

from qgis.core import QgsMapLayerRegistry, QgsGeometry, QgsFeature
from qgis.gui import QgsMapCanvas, QgsMapToolPan, QgsMapCanvasLayer

from geogig.tools.utils import loadLayerNoCrsDialog
from geogig.gui.executor import execute

resourcesPath = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "resources")
ptOursStyle = os.path.join(resourcesPath, "pt_ours.qml")
ptTheirsStyle = os.path.join(resourcesPath, "pt_theirs.qml")
lineOursStyle = os.path.join(resourcesPath, "line_ours.qml")
lineTheirsStyle = os.path.join(resourcesPath, "line_theirs.qml")
polygonOursStyle = os.path.join(resourcesPath, "polygon_ours.qml")
polygonTheirsStyle = os.path.join(resourcesPath, "polygon_theirs.qml")

layerIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "layer_group.gif"))
featureIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "geometry.png"))

sys.path.append(os.path.dirname(__file__))
pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'conflictdialog.ui'))


class ConflictDialog(WIDGET, BASE):

    LOCAL, REMOTE, DELETE = 1,2, 3

    def __init__(self, conflicts):
        super(ConflictDialog).__init__(self, None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.solved = False
        self.resolvedConflicts = {}
        self.conflicts = conflicts
        self.setupUi(self)

        self.setWindowFlags(self.windowFlags() |
                              Qt.WindowSystemMenuHint |
                              Qt.WindowMinMaxButtonsHint)

        self.zoomButton.clicked.connect(self.zoomToFullExtent)
        self.solveButton.clicked.connect(self.solve)
        self.conflictsTree.itemClicked.connect(self.treeItemClicked)
        self.attributesTable.cellClicked.connect(self.cellClicked)
        self.solveAllLocalButton.clicked.connect(self.solveAllLocal)
        self.solveAllRemoteButton.clicked.connect(self.solveAllRemote)
        self.solveLocalButton.clicked.connect(self.solveLocal)
        self.solveRemoteButton.clicked.connect(self.solveRemote)

        self.showRemoteCheck.stateChanged.connect(self.showGeoms)
        self.showLocalCheck.stateChanged.connect(self.showGeoms)

        self.lastSelectedItem = None
        self.currentPath = None
        self.currentConflict = None
        self.theirsLayer = None
        self.oursLayer = None

        settings = QSettings()
        horizontalLayout = QHBoxLayout()
        horizontalLayout.setSpacing(0)
        horizontalLayout.setMargin(0)
        self.mapCanvas = QgsMapCanvas()
        self.mapCanvas.setCanvasColor(Qt.white)
        self.mapCanvas.enableAntiAliasing(settings.value("/qgis/enable_anti_aliasing", False, type = bool))
        self.mapCanvas.useImageToRender(settings.value("/qgis/use_qimage_to_render", False, type = bool))
        self.mapCanvas.mapRenderer().setProjectionsEnabled(True)
        action = settings.value("/qgis/wheel_action", 0, type = float)
        zoomFactor = settings.value("/qgis/zoom_factor", 2, type = float)
        self.mapCanvas.setWheelAction(QgsMapCanvas.WheelAction(action), zoomFactor)
        horizontalLayout.addWidget(self.mapCanvas)
        self.canvasWidget.setLayout(horizontalLayout)
        self.panTool = QgsMapToolPan(self.mapCanvas)
        self.mapCanvas.setMapTool(self.panTool)

        self.solveButton.setEnabled(False)
        self.solveLocalButton.setEnabled(False)
        self.solveRemoteButton.setEnabled(False)

        self.fillConflictsTree()

    def fillConflictsTree(self):
        topTreeItems = {}
        for c in self.conflicts:
            path = os.path.dirname(c.path)
            if path in topTreeItems:
                topItem = topTreeItems[path]
            else:
                topItem = QTreeWidgetItem()
                topItem.setText(0, path)
                topItem.setIcon(0, layerIcon)
                topTreeItems[path] = topItem
            conflictItem = ConflictItem(c)
            topItem.addChild(conflictItem)
        for item in topTreeItems.values():
            self.conflictsTree.addTopLevelItem(item)

    def cellClicked(self, row, col):
        if col > 2:
            return
        value = self.attributesTable.item(row, col).value
        geoms = (self.oursgeom, self.theirsgeom)
        self.attributesTable.setItem(row, 4, ValueItem(value, False, geoms));
        self.attributesTable.item(row, 0).setBackgroundColor(Qt.white);
        self.attributesTable.item(row, 1).setBackgroundColor(Qt.white);
        self.attributesTable.item(row, 2).setBackgroundColor(Qt.white);
        attrib = self.attributesTable.item(row, 3).text()
        if attrib in self.conflicted:
            self.conflicted.remove(attrib)
        self.updateSolveButton()

        self.showGeoms()

    def treeItemClicked(self):
        item = self.conflictsTree.selectedItems()[0]
        if self.lastSelectedItem == item:
            return
        if isinstance(item, ConflictItem):
            self.lastSelectedItem = item
            self.currentPath = item.conflict.path
            self.updateCurrentPath()
            self.solveLocalButton.setEnabled(True)
            self.solveRemoteButton.setEnabled(True)
            self.solveButton.setEnabled(False)

    def updateCurrentPath(self):
        self.solveButton.setEnabled(False)
        self.solveLocalButton.setEnabled(False)
        self.solveRemoteButton.setEnabled(False)
        self.cleanCanvas()
        self.showFeatureAttributes()
        self.createLayers()
        self.showGeoms()
        self.zoomToFullExtent()

    def zoomToFullExtent(self):
        layers = [lay.extent() for lay in self.mapCanvas.layers() if lay.type() == lay.VectorLayer]
        if layers:
            ext = layers[0]
            for layer in  layers[1:]:
                ext.combineExtentWith(layer)
            self.mapCanvas.setExtent(ext)
            self.mapCanvas.refresh()

    def cleanCanvas(self):
        self.mapCanvas.setLayerSet([])
        layers = [self.oursLayer, self.theirsLayer]
        for layer in layers:
            if layer is not None:
                QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
        self.oursLayer = None
        self.theirsLayer = None

    def solveAllRemote(self):
        ret = QMessageBox.warning(self, "Solve conflict",
                                "Are you sure you want to solve all conflicts using the 'To merge' version?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.Yes);
        if ret == QMessageBox.Yes:
            self.solved = True
            self.resolvedConflicts = {c.path:self.REMOTE for c in self.conflicts}
            self.close()

    def solveAllLocal(self):
        ret = QMessageBox.warning(self, "Solve conflict",
            "Are you sure you want to solve all conflict using the 'Local' version?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes);
        if ret == QMessageBox.Yes:
            self.solved = True
            self.resolvedConflicts = {c.path:self.LOCAL for c in self.conflicts}
            self.close()


    def _afterSolve(self, remove = True):
        if remove:
            parent = self.lastSelectedItem.parent()
            parent.removeChild(self.lastSelectedItem)
            self.lastSelectedItem = None
            if parent.childCount() == 0:
                self.conflictsTree.invisibleRootItem().removeChild(parent)
                if self.conflictsTree.topLevelItemCount() == 0:
                    self.solved = True
                    self.close()

        self.attributesTable.setRowCount(0)
        self.cleanCanvas()
        self.solveButton.setEnabled(False)
        self.solveLocalButton.setEnabled(False)
        self.solveRemoteButton.setEnabled(False)

    def solveLocal(self):
        self.resolvedConflicts[self.currentPath] = self.LOCAL
        self._afterSolve()

    def solveRemote(self):
        self.resolvedConflicts[self.currentPath] = self.REMOTE
        self._afterSolve()

    def solve(self):
        attribs = {}
        for i in xrange(self.attributesTable.rowCount()):
            value = self.attributesTable.item(i, 4).value
            name = unicode(self.attributesTable.item(i, 3).text())
            attribs[name] = value
        self.resolvedConflicts[self.currentPath] = attribs
        self._afterSolve()


    def updateSolveButton(self):
        self.solveButton.setEnabled(len(self.conflicted) == 0)

    def showFeatureAttributes(self):
        conflictItem = self.lastSelectedItem
        self.oursgeom = None
        self.theirsgeom = None
        geoms = (self.oursgeom, self.theirsgeom)
        self.currentConflictedAttributes = []
        attribs = conflictItem.origin.keys()
        self.attributesTable.setRowCount(len(attribs))

        self.conflicted = []
        for idx, name in enumerate(attribs):
            font = QFont()
            font.setBold(True)
            font.setWeight(75)
            item = QTableWidgetItem(name)
            item.setFont(font)
            self.attributesTable.setItem(idx, 3, item);

            self.attributesTable.setItem(idx, 4, ValueItem(None, False));

            try:
                values = (conflictItem.origin[name], conflictItem.local[name], conflictItem.remote[name])
            except TypeError: #Local has been deleted
                self._afterSolve(False)
                self.solveModifyAndDelete(conflictItem.conflict.path, self.REMOTE)
                return
            except GeoGigException: #Remote has been deleted
                self._afterSolve(False)
                self.solveModifyAndDelete(conflictItem.conflict.path,self.LOCAL)
                return
            try:
                geom = QgsGeometry.fromWkt(values[0])
            except:
                geom = None
            if geom is not None:
                self.theirsgeom = QgsGeometry().fromWkt(values[1])
                self.oursgeom = QgsGeometry.fromWkt(values[2])
                geoms = (self.oursgeom, self.theirsgeom)

            ok = values[0] == values[1] or values[1] == values[2] or values[0] == values[2]

            for i, v in enumerate(values):
                self.attributesTable.setItem(idx, i, ValueItem(v, not ok, geoms));

            if not ok:
                self.conflicted.append(name)
            else:
                if values[0] == values[1]:
                    newvalue = values[2]
                else:
                    newvalue = values[1]
                self.attributesTable.setItem(idx, 4, ValueItem(newvalue, False, geoms));

        self.attributesTable.resizeRowsToContents()
        self.attributesTable.horizontalHeader().setMinimumSectionSize(150)
        self.attributesTable.horizontalHeader().setStretchLastSection(True)


    def solveModifyAndDelete(self, path, modified):
        msgBox = QMessageBox()
        msgBox.setText("The feature has been modified in one version and deleted in the other one.\n"
                       "How do you want to solve the conflict?")
        msgBox.addButton(QPushButton('Modify'), QMessageBox.YesRole)
        msgBox.addButton(QPushButton('Delete'), QMessageBox.NoRole)
        msgBox.addButton(QPushButton('Cancel'), QMessageBox.RejectRole)
        ret = msgBox.exec_()
        if ret == 0:
            self.resolvedConflicts[path] = modified
            self._afterSolve()
        elif ret == 1:
            self.resolvedConflicts[path] = self.DELETE
            self._afterSolve()
        else:
            pass

    def createLayers(self):
        types = [("Point", ptOursStyle, ptTheirsStyle),
                  ("LineString", lineOursStyle, lineTheirsStyle),
                  ("Polygon", polygonOursStyle, polygonTheirsStyle)]
        if self.oursgeom is not None:
            geomtype = types[int(self.oursgeom.type())][0]
            style = types[int(self.oursgeom.type())][1]
            self.oursLayer = loadLayerNoCrsDialog(geomtype + "?crs=EPSG:4326", "ours", "memory")
            pr = self.oursLayer.dataProvider()
            feat = QgsFeature()
            feat.setGeometry(self.oursgeom)
            pr.addFeatures([feat])
            self.oursLayer.loadNamedStyle(style)
            self.oursLayer.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayer(self.oursLayer, False)
        else:
            self.oursLayer = None
        if self.theirsgeom is not None:
            geomtype = types[int(self.theirsgeom.type())][0]
            style = types[int(self.theirsgeom.type())][2]
            self.theirsLayer = loadLayerNoCrsDialog(geomtype + "?crs=EPSG:4326", "theirs", "memory")
            pr = self.theirsLayer.dataProvider()
            feat = QgsFeature()
            feat.setGeometry(self.theirsgeom)
            pr.addFeatures([feat])
            self.theirsLayer.loadNamedStyle(style)
            self.theirsLayer.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayer(self.theirsLayer, False)
        else:
            self.theirsLayer = None

    def showGeoms(self):
        checks = [self.showRemoteCheck, self.showLocalCheck]
        layers = [self.oursLayer, self.theirsLayer]
        toShow = []
        for lay, chk in zip(layers, checks):
            if lay is not None and chk.isChecked():
                toShow.append(lay)
        self.mapCanvas.setRenderFlag(False)
        self.mapCanvas.setLayerSet([QgsMapCanvasLayer(layer) for layer in toShow])
        self.mapCanvas.setRenderFlag(True)


    def closeEvent(self, evnt):
        if not self.solved:
            ret = QMessageBox.warning(self, "Conflict resolution",
                                  "There are unsolved conflicts.\n"
                                  "Do you really want to exit and abort the sync operation?",
                                  QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                evnt.ignore()
                return

        self.cleanCanvas()

class ValueItem(QTableWidgetItem):

    def __init__(self, value, conflicted, geoms = None):
        QTableWidgetItem.__init__(self)
        self.value = value
        if value is None:
            s = ""
        elif isinstance(value, basestring):
            s = value
        else:
            s = str(value)
        if conflicted:
            self.setBackgroundColor(Qt.yellow);
        self.setText(s)
        self.setFlags(Qt.ItemIsEnabled)


class ConflictItem(QTreeWidgetItem):

    def __init__(self, conflict):
        QTreeWidgetItem.__init__(self)
        self.setText(0, conflict.path)
        self.setIcon(0, featureIcon)
        self.setSizeHint(0, QSize(self.sizeHint(0).width(), 25))
        self.conflict = conflict
        self._local = None
        self._remote = None
        self._origin = None

    @property
    def local(self):
        if self.conflict.localFeature is None:
            if self._local is None:
                self._local = execute(lambda: self.conflict.repo.feature(self.conflict.path, self.conflict.localCommit))
            return self._local
        else:
            return self.conflict.localFeature

    @property
    def remote(self):
        if self._remote is None:
            self._remote = execute(lambda: self.conflict.repo.feature(self.conflict.path, self.conflict.remoteCommit))
        return self._remote

    @property
    def origin(self):
        if self._origin is None:
            self._origin = execute(lambda: self.conflict.repo.feature(self.conflict.path, self.conflict.originCommit))
        return self._origin
