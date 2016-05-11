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

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from PyQt4 import QtGui, QtCore
from qgis.core import *
from qgis.gui import *
import difflib
from geogig.tools.utils import loadLayerNoCrsDialog
import os
from geogig.gui.executor import execute

resourcesPath = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "resources")
lineBeforeStyle = os.path.join(resourcesPath, "line_geomdiff_before.qml")
lineAfterStyle = os.path.join(resourcesPath, "line_geomdiff_after.qml")
polygonBeforeStyle = os.path.join(resourcesPath, "polygon_geomdiff_before.qml")
polygonAfterStyle = os.path.join(resourcesPath, "polygon_geomdiff_after.qml")
pointsStyle = os.path.join(resourcesPath, "geomdiff_points.qml")

class GeometryDiffViewerDialog(QtGui.QDialog):

    def __init__(self, geoms, crs, parent = None):
        super(GeometryDiffViewerDialog, self).__init__(parent)
        self.geoms = geoms
        self.crs = crs
        self.initGui()

    def initGui(self):
        layout = QtGui.QVBoxLayout()
        self.tab = QtGui.QTabWidget()
        self.table = QtGui.QTableView()

        self.setLayout(layout)
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(QtCore.Qt.white)
        settings = QtCore.QSettings()
        self.canvas.enableAntiAliasing(settings.value("/qgis/enable_anti_aliasing", False, type = bool))
        self.canvas.useImageToRender(settings.value("/qgis/use_qimage_to_render", False, type = bool))
        self.canvas.mapSettings().setDestinationCrs(self.crs)
        action = settings.value("/qgis/wheel_action", 0, type = float)
        zoomFactor = settings.value("/qgis/zoom_factor", 2, type = float)
        self.canvas.setWheelAction(QgsMapCanvas.WheelAction(action), zoomFactor)
        self.panTool = QgsMapToolPan(self.canvas)
        self.canvas.setMapTool(self.panTool)

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
        layers = []
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
            layers.append(layer)
            QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            extent.combineExtentWith(geom.boundingBox())

        layer = loadLayerNoCrsDialog("Point?crs=%s&field=changetype:string" % self.crs.authid(), "points", "memory")
        pr = layer.dataProvider()
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
        layer.loadNamedStyle(pointsStyle)
        QgsMapLayerRegistry.instance().addMapLayer(layer, False)
        layers.append(layer)

        self.mapLayers = [QgsMapCanvasLayer(lay) for lay in layers]
        self.canvas.setLayerSet(self.mapLayers)
        self.canvas.setExtent(extent)
        self.canvas.refresh()

    def reject(self):
        QtGui.QDialog.reject(self)
        self.unloadLayers()

    def unloadLayers(self):
        return
        for layer in self.mapLayers:
            QgsMapLayerRegistry.instance().removeMapLayer(layer.layer().id())


class GeomDiffTableModel(QtCore.QAbstractTableModel):
    def __init__(self, data, parent = None, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.data = data

    def rowCount(self, parent = None):
        return len(self.data)

    def columnCount(self, parent = None):
        return 2

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if index.isValid():
            values = self.data[index.row()]
            if role == QtCore.Qt.DisplayRole:
                value = values[index.column()]
                if value is not None:
                    return "\n".join(value.split(" "))
            elif role == QtCore.Qt.BackgroundRole:
                if index.column() == 0:
                    if values[1] is None:
                        return QtGui.QBrush(QtCore.Qt.red)
                    else:
                        return QtGui.QBrush(QtCore.Qt.white)
                else:
                    if values[0] is None:
                        return QtGui.QBrush(QtCore.Qt.green)
                    else:
                        return QtGui.QBrush(QtCore.Qt.white)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return ["Base geometry", "Compare geometry"][section]
            else:
                return str(section + 1)
