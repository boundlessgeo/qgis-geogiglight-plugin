# -*- coding: utf-8 -*-

"""
***************************************************************************
    geometrydiffviewerdialog.py
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

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import os
import difflib

from qgis.PyQt.QtCore import Qt, QSettings, QAbstractTableModel
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QTableView, QDialog, QHBoxLayout, QCheckBox
from qgis.PyQt.QtGui import QBrush
from qgis.core import QgsFeature, QgsMapLayerRegistry, QgsGeometry, QgsPoint, QgsProject, QgsLayerTreeLayer, QgsLayerTreeGroup
from qgis.gui import QgsMapCanvas, QgsMapToolPan, QgsMapCanvasLayer

from geogig.extlibs.qgiscommons2.layers import loadLayerNoCrsDialog
from geogig.extlibs.qgiscommons2.gui import execute

resourcesPath = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "resources")
lineBeforeStyle = os.path.join(resourcesPath, "line_geomdiff_before.qml")
lineAfterStyle = os.path.join(resourcesPath, "line_geomdiff_after.qml")
polygonBeforeStyle = os.path.join(resourcesPath, "polygon_geomdiff_before.qml")
polygonAfterStyle = os.path.join(resourcesPath, "polygon_geomdiff_after.qml")
pointsStyle = os.path.join(resourcesPath, "geomdiff_points.qml")

class GeometryDiffViewerDialog(QDialog):

    def __init__(self, geoms, crs, parent = None):
        super(GeometryDiffViewerDialog, self).__init__(parent)
        self.geoms = geoms
        self.crs = crs
        self.initGui()

    def initGui(self):
        layout = QVBoxLayout()
        self.tab = QTabWidget()
        self.table = QTableView()

        self.setLayout(layout)
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(Qt.white)
        settings = QSettings()
        self.canvas.enableAntiAliasing(settings.value("/qgis/enable_anti_aliasing", False, type = bool))
        self.canvas.useImageToRender(settings.value("/qgis/use_qimage_to_render", False, type = bool))
        self.canvas.mapSettings().setDestinationCrs(self.crs)
        action = settings.value("/qgis/wheel_action", 0, type = float)
        zoomFactor = settings.value("/qgis/zoom_factor", 2, type = float)
        self.canvas.setWheelAction(QgsMapCanvas.WheelAction(action), zoomFactor)
        self.panTool = QgsMapToolPan(self.canvas)
        self.canvas.setMapTool(self.panTool)

        hlayout = QHBoxLayout()
        self.beforeLayerCheck = QCheckBox("Before layer")
        self.beforeLayerCheck.setChecked(True)
        self.beforeLayerCheck.stateChanged.connect(self.refreshLayers)
        self.afterLayerCheck = QCheckBox("After layer")
        self.afterLayerCheck.setChecked(True)
        self.afterLayerCheck.stateChanged.connect(self.refreshLayers)
        self.baseLayersCheck = QCheckBox("Project layers")
        self.baseLayersCheck.setChecked(True)
        self.baseLayersCheck.stateChanged.connect(self.refreshLayers)

        hlayout.addWidget(self.beforeLayerCheck)
        hlayout.addWidget(self.afterLayerCheck)
        hlayout.addWidget(self.baseLayersCheck)
        layout.addLayout(hlayout)

        execute(self.createLayers)

        model = GeomDiffTableModel(self.data)
        self.table.setModel(model)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.tab.addTab(self.canvas, "Map view")
        self.tab.addTab(self.table, "Table view")
        layout.addWidget(self.tab)

        self.resize(600, 500)
        self.setWindowTitle("Geometry comparison")


    def refreshLayers(self):
        layers = []
        if self.beforeLayerCheck.isChecked():
            layers.append(self.diffLayers[0])
        if self.afterLayerCheck.isChecked():
            layers.append(self.diffLayers[1])
        if len(layers) == 2:
            layers.append(self.nodesLayer)
        if self.baseLayersCheck.isChecked():
            layers.extend(self.baseLayers)

        self.mapLayers = [QgsMapCanvasLayer(lay) for lay in layers]
        self.canvas.setLayerSet(self.mapLayers)
        self.canvas.refresh()

    def createLayers(self):
        textGeometries = []
        for geom in self.geoms:
            text = geom.exportToWkt()
            valid = " -1234567890.,"
            text = "".join([c for c in text if c in valid])
            textGeometries.append(text.split(","))
        lines = difflib.Differ().compare(textGeometries[0], textGeometries[1])
        self.data = []
        for line in lines:
            if line.startswith("+"):
                self.data.append([None, line[2:]])
            if line.startswith("-"):
                self.data.append([line[2:], None])
            if line.startswith(" "):
                self.data.append([line[2:], line[2:]])
        types = [("LineString", lineBeforeStyle, lineAfterStyle),
                  ("Polygon", polygonBeforeStyle, polygonAfterStyle)]
        self.diffLayers = []
        extent = self.geoms[0].boundingBox()
        for i, geom in enumerate(self.geoms):
            geomtype = types[int(geom.type() - 1)][0]
            style = types[int(geom.type() - 1)][i + 1]
            layer = loadLayerNoCrsDialog(geomtype + "?crs=" + self.crs.authid(), "layer", "memory")
            pr = layer.dataProvider()
            feat = QgsFeature()
            feat.setGeometry(geom)
            pr.addFeatures([feat])
            layer.loadNamedStyle(style)
            layer.updateExtents()
            self.diffLayers.append(layer)
            QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            extent.combineExtentWith(geom.boundingBox())

        self.nodesLayer = loadLayerNoCrsDialog("Point?crs=%s&field=changetype:string" % self.crs.authid(), "points", "memory")
        pr = self.nodesLayer.dataProvider()
        feats = []
        for coords in self.data:
            coord = coords[0] or coords[1]
            feat = QgsFeature()
            x, y = coord.strip().split(" ")
            x, y = (float(x), float(y))
            pt = QgsGeometry.fromPoint(QgsPoint(x, y))
            feat.setGeometry(pt)
            if coords[0] is None:
                changetype = "A"
            elif coords[1] is None:
                changetype = "R"
            else:
                changetype = "U"
            feat.setAttributes([changetype])
            feats.append(feat)

        pr.addFeatures(feats)
        self.nodesLayer.loadNamedStyle(pointsStyle)
        QgsMapLayerRegistry.instance().addMapLayer(self.nodesLayer, False)

        self.baseLayers = []
        root = QgsProject.instance().layerTreeRoot()
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup):
                for subchild in child.children():
                    if isinstance(subchild, QgsLayerTreeLayer):
                        self.baseLayers.append(subchild.layer())
            elif isinstance(child, QgsLayerTreeLayer):
                self.baseLayers.append(child.layer())

        self.refreshLayers()
        self.canvas.setExtent(extent)
        self.canvas.refresh()

    def reject(self):
        QDialog.reject(self)


class GeomDiffTableModel(QAbstractTableModel):
    def __init__(self, data, parent = None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.data = data

    def rowCount(self, parent = None):
        return len(self.data)

    def columnCount(self, parent = None):
        return 2

    def data(self, index, role = Qt.DisplayRole):
        if index.isValid():
            values = self.data[index.row()]
            if role == Qt.DisplayRole:
                value = values[index.column()]
                if value is not None:
                    return "\n".join(value.split(" "))
            elif role == Qt.BackgroundRole:
                if index.column() == 0:
                    if values[1] is None:
                        return QBrush(Qt.red)
                    else:
                        return QBrush(Qt.white)
                else:
                    if values[0] is None:
                        return QBrush(Qt.green)
                    else:
                        return QBrush(Qt.white)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return ["Old geometry", "New geometry"][section]
            else:
                return str(section + 1)
