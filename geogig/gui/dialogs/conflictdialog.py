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
from PyQt4 import QtGui, QtCore, uic
from qgis.core import *
from qgis.gui import *
from geogig.tools.utils import loadLayerNoCrsDialog
import sys

BASEMAP_NONE = 0
BASEMAP_OSM = 1
BASEMAP_GOOGLE = 2

resourcesPath = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "resources")
ptOursStyle = os.path.join(resourcesPath, "pt_ours.qml")
ptTheirsStyle = os.path.join(resourcesPath, "pt_theirs.qml")
lineOursStyle = os.path.join(resourcesPath, "line_ours.qml")
lineTheirsStyle = os.path.join(resourcesPath, "line_theirs.qml")
polygonOursStyle = os.path.join(resourcesPath, "polygon_ours.qml")
polygonTheirsStyle = os.path.join(resourcesPath, "polygon_theirs.qml")

layerIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "layer_group.gif"))
featureIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "geometry.png"))

sys.path.append(os.path.dirname(__file__))
pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'conflictdialog.ui'))

class ConflictDialog(WIDGET, BASE):

    UNSOLVED, MANUAL, OURS, THEIRS = range(4)

    def __init__(self, conflicts, layername):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.solved = self.UNSOLVED
        self.resolvedConflicts = {}
        self.layername = layername
        self.conflicts = conflicts
        self.setupUi(self)

        self.setWindowFlags(self.windowFlags() |
                              QtCore.Qt.WindowSystemMenuHint |
                              QtCore.Qt.WindowMinMaxButtonsHint)

        self.zoomButton.clicked.connect(self.zoomToFullExtent)
        self.solveButton.clicked.connect(self.solve)
        self.conflictsTree.itemClicked.connect(self.treeItemClicked)
        self.attributesTable.cellClicked.connect(self.cellClicked)
        self.solveAllOursButton.clicked.connect(self.solveOurs)
        self.solveAllTheirsButton.clicked.connect(self.solveTheirs)
        self.baseMapCombo.currentIndexChanged.connect(self.baseMapChanged)

        def refreshMap():
            self.showGeoms()
        self.showTheirsCheck.stateChanged.connect(refreshMap)
        self.showOursCheck.stateChanged.connect(refreshMap)

        self.lastSelectedItem = None
        self.currentPath = None
        self.currentConflict = None
        self.theirsLayer = None
        self.oursLayer = None
        self.baseLayer = None

        settings = QtCore.QSettings()
        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(0)
        horizontalLayout.setMargin(0)
        self.mapCanvas = QgsMapCanvas()
        self.mapCanvas.setCanvasColor(QtCore.Qt.white)
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

        self.fillConflictsTree()

    def fillConflictsTree(self):
        item = QtGui.QTreeWidgetItem([self.layername])
        item.setIcon(0, layerIcon)
        self.conflictsTree.addTopLevelItem(item)
        for path, c in self.conflicts.iteritems():
            conflictItem = ConflictItem(path, c[0], c[1])
            item.addChild(conflictItem)

    def cellClicked(self, row, col):
        if col > 1:
            return
        value = self.attributesTable.item(row, col).value
        geoms = (self.oursgeom, self.theirsgeom)
        self.attributesTable.setItem(row, 4, ValueItem(value, False, geoms));
        self.attributesTable.item(row, 0).setBackgroundColor(QtCore.Qt.white);
        self.attributesTable.item(row, 1).setBackgroundColor(QtCore.Qt.white);
        self.attributesTable.item(row, 2).setBackgroundColor(QtCore.Qt.white);
        attrib = self.attributesTable.item(row, 3).text()
        if attrib in self.conflicted:
            self.conflicted.remove(attrib)
        self.updateSolveButton()

    def baseMapChanged(self, idx):
        if idx == BASEMAP_OSM:
            baseLayerFile = os.path.join(os.path.dirname(__file__),
                                         os.pardir, os.pardir, "resources", "osm.xml")
        elif idx == BASEMAP_GOOGLE:
            baseLayerFile = os.path.join(os.path.dirname(__file__),
                                         os.pardir, os.pardir, "resources", "gmaps.xml")
        else:
            self.baseLayer = None
            self.showGeoms()
            return

        if self.baseLayer is not None:
            QgsMapLayerRegistry.instance().removeMapLayer(self.baseLayer.id())
            self.baseLayer = None
        baseLayer = QgsRasterLayer(baseLayerFile, "base", "gdal")
        if baseLayer.isValid():
            self.baseLayer = baseLayer
            QgsMapLayerRegistry.instance().addMapLayer(self.baseLayer, False)


        self.showGeoms()

    def treeItemClicked(self):
        item = self.conflictsTree.selectedItems()[0]
        if self.lastSelectedItem == item:
            return
        self.lastSelectedItem = item
        if isinstance(item, ConflictItem):
            self.currentPath = item.path
            self.updateCurrentPath()

    def updateCurrentPath(self):
        self.cleanCanvas()
        self.showFeatureAttributes()
        self.createLayers()
        self.showGeoms()
        self.zoomToFullExtent()
        self.updateSolveButton()

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
        layers = [self.oursLayer, self.theirsLayer, self.baseLayer]
        for layer in layers:
            if layer is not None:
                QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
        self.oursLayer = None
        self.theirsLayer = None
        self.baseLayer = None


    def solveTheirs(self):
        ret = QtGui.QMessageBox.warning(self, "Solve conflict",
                                "Are you sure you want to solve all conflicts using the 'To merge' version?",
                                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                QtGui.QMessageBox.Yes);
        if ret == QtGui.QMessageBox.Yes:
            self.repo.solveconflicts(self.repo.conflicts().keys(), geogig.THEIRS)
            self.solved = self.THEIRS
            self.close()

    def solveOurs(self):
        ret = QtGui.QMessageBox.warning(self, "Solve conflict",
            "Are you sure you want to solve all conflict using the 'Local' version?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.Yes);
        if ret == QtGui.QMessageBox.Yes:
            self.solved = self.OURS
            self.close()

    def solve(self):
        attribs = {}
        for i in xrange(self.attributesTable.rowCount()):
            value = self.attributesTable.item(i, 4).value
            name = unicode(self.attributesTable.item(i, 3).text())
            attribs[name] = value
        self.resolvedConflicts[self.currentPath] = attribs
        parent = self.lastSelectedItem.parent()
        parent.removeChild(self.lastSelectedItem)
        if parent.childCount() == 0:
            self.conflictsTree.invisibleRootItem().removeChild(parent)
            self.solved = self.MANUAL
            self.close()
        self.lastSelectedItem = None
        self.attributesTable.setRowCount(0)
        self.cleanCanvas()
        self.solveButton.setEnabled(False)


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
            font = QtGui.QFont()
            font.setBold(True)
            font.setWeight(75)
            item = QtGui.QTableWidgetItem(name)
            item.setFont(font)
            self.attributesTable.setItem(idx, 3, item);

            self.attributesTable.setItem(idx, 4, ValueItem(None, False));

            values = (conflictItem.origin[name], conflictItem.local[name], conflictItem.remote[name])
            try:
                geom = QgsGeometry.fromWkt(values[0])
            except:
                geom = None
            if geom is not None:
                self.oursgeom = QgsGeometry().fromWkt(values[1])
                self.theirsgeom = QgsGeometry.fromWkt(values[2])
                geoms = (self.oursgeom, self.theirsgeom)
                if self.oursgeom is not None:
                    values[1] = self.oursgeom.exportToWkt()

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

    def createLayers(self):
        types = [("Point", ptOursStyle, ptTheirsStyle),
                  ("LineString", lineOursStyle, lineTheirsStyle),
                  ("Polygon", polygonOursStyle, polygonTheirsStyle)]
        if self.oursgeom is not None:
            geomtype = types[int(self.oursgeom.type())][0]
            #===================================================================
            # if self.oursgeom.crs is not None:
            #     targetCrs = self.mapCanvas.mapRenderer().destinationCrs()
            #     crsTransform = QgsCoordinateTransform(QgsCoordinateReferenceSystem(self.oursgeom.crs), targetCrs)
            #     qgsgeom.transform(crsTransform)
            #===================================================================
            style = types[int(self.oursgeom.type())][1]
            self.oursLayer = loadLayerNoCrsDialog(geomtype + "?crs=EPSG:4326", "ours", "memory")
            pr = self.oursLayer.dataProvider()
            feat = QgsFeature()
            feat.setGeometry(self.oursgeom)
            pr.addFeatures([feat])
            self.oursLayer.loadNamedStyle(style)
            self.oursLayer.updateExtents()
            #this is to correct a problem with memory layers in qgis 2.2
            self.oursLayer.selectAll()
            self.oursLayer.setExtent(self.oursLayer.boundingBoxOfSelected())
            self.oursLayer.invertSelection()
            QgsMapLayerRegistry.instance().addMapLayer(self.oursLayer, False)
        else:
            self.oursLayer = None
        if self.theirsgeom is not None:
            geomtype = types[int(self.theirsgeom.type())][0]
            #===================================================================
            # if self.theirsgeom.crs is not None:
            #     targetCrs = self.mapCanvas.mapRenderer().destinationCrs()
            #     crsTransform = QgsCoordinateTransform(QgsCoordinateReferenceSystem(self.theirsgeom.crs), targetCrs)
            #     qgsgeom.transform(crsTransform)
            #===================================================================
            style = types[int(self.theirsgeom.type())][2]
            self.theirsLayer = loadLayerNoCrsDialog(geomtype + "?crs=EPSG:4326", "theirs", "memory")
            pr = self.theirsLayer.dataProvider()
            feat = QgsFeature()
            feat.setGeometry(self.theirsgeom)
            pr.addFeatures([feat])
            self.theirsLayer.loadNamedStyle(style)
            self.theirsLayer.updateExtents()
            #this is to correct a problem with memory layers in qgis 2.2
            self.theirsLayer.selectAll()
            self.theirsLayer.setExtent(self.theirsLayer.boundingBoxOfSelected())
            self.theirsLayer.invertSelection()
            QgsMapLayerRegistry.instance().addMapLayer(self.theirsLayer, False)
        else:
            self.theirsLayer = None

    def showGeoms(self):
        checks = [self.showOursCheck, self.showTheirsCheck]
        layers = [self.oursLayer, self.theirsLayer]
        toShow = []
        for lay, chk in zip(layers, checks):
            if lay is not None and chk.isChecked():
                toShow.append(lay)
        if len(toShow) > 0 and self.baseLayer is not None:
            toShow.append(self.baseLayer)
        self.mapCanvas.setRenderFlag(False)
        self.mapCanvas.setLayerSet([QgsMapCanvasLayer(layer) for layer in toShow])
        self.mapCanvas.setRenderFlag(True)


    def closeEvent(self, evnt):
        print self.solved
        if self.solved == self.UNSOLVED:
            ret = QtGui.QMessageBox.warning(self, "Conflict resolution",
                                  "There are unsolved conflicts.\n"
                                  "Do you really want to exit and abort the sync operation?",
                                  QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if ret == QtGui.QMessageBox.No:
                evnt.ignore()
                return

        self.cleanCanvas()

class ValueItem(QtGui.QTableWidgetItem):

    def __init__(self, value, conflicted, geoms = None):
        QtGui.QTableWidgetItem.__init__(self)
        self.value = value
        if value is None:
            s = ""
        elif isinstance(value, basestring):
            s = value
        else:
            s = str(value)
        #=======================================================================
        # try:
        #     geom = QgsGeometry.fromWkt(value)
        # except:
        #     geom = None
        # if geom is not None:
        #     if value == geoms[0]:
        #         idx = 1
        #     else:
        #         idx = 2
        #     s = value.split("(")[0] + "[" + str(idx) + "]"
        #=======================================================================
        if conflicted:
            self.setBackgroundColor(QtCore.Qt.yellow);
        self.setText(s)
        self.setFlags(QtCore.Qt.ItemIsEnabled)


class ConflictItem(QtGui.QTreeWidgetItem):

    def __init__(self, path, local, remote):
        QtGui.QTreeWidgetItem.__init__(self)
        self.setText(0, path)
        self.setIcon(0, featureIcon)
        self.setSizeHint(0, QtCore.QSize(self.sizeHint(0).width(), 25))
        self.path = path
        self.local = local
        self._remote = remote
        self._diff = None

    @property
    def remote(self):
        if self._diff is None:
            self._diff = self._remote.featurediff(allAttrs = True)
        return {d["attributename"]: d.get("newvalue", d.get("oldvalue", "")) for d in self._diff}

    @property
    def origin(self):
        if self._diff is None:
            self._diff = self._remote.featurediff(allAttrs = True)
        return {d["attributename"]: d.get("oldvalue", "") for d in self._diff}
