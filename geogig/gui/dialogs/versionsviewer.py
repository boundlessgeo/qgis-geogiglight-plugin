# -*- coding: utf-8 -*-

"""
***************************************************************************
    versionviewer.py
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

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtWidgets import (QDialog,
                                 QHBoxLayout,
                                 QTableWidgetItem,
                                 QLabel,
                                 QTextEdit,
                                 QListWidgetItem
                                )
from qgis.PyQt.QtGui import QFont, QIcon
try:
    from qgis.core import  QGis
except ImportError:
    from qgis.core import  Qgis as QGis

if QGis.QGIS_VERSION_INT < 29900:
    from qgis.core import QgsSymbolV2, QgsSingleSymbolRendererV2
else:
    from qgis.core import QgsSymbol as QgsSymbolV2
    from qgis.core import QgsSingleSymbolRenderer

from qgis.core import QgsGeometry, QgsFeature, QgsMapLayerRegistry
from qgis.gui import QgsMapCanvas, QgsMapToolPan, QgsMapCanvasLayer

from geogig import config
from geogig.geogigwebapi.repository import GeoGigException
from geogig.tools.utils import loadLayerNoCrsDialog

pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'versionsviewer.ui'))


class VersionViewerDialog(BASE, WIDGET):

    def __init__(self, repo, path):
        super(VersionViewerDialog, self).__init__(config.iface.mainWindow(), Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.repo = repo
        self.path = path
        self.setupUi(self)

        self.listWidget.itemClicked.connect(self.commitClicked)

        settings = QSettings()
        horizontalLayout = QHBoxLayout()
        horizontalLayout.setSpacing(0)
        horizontalLayout.setMargin(0)
        self.mapCanvas = QgsMapCanvas()
        self.mapCanvas.setCanvasColor(Qt.white)
        self.mapCanvas.enableAntiAliasing(settings.value("/qgis/enable_anti_aliasing", False, type = bool))
        self.mapCanvas.useImageToRender(settings.value("/qgis/use_qimage_to_render", False, type = bool))
        action = settings.value("/qgis/wheel_action", 0, type = float)
        zoomFactor = settings.value("/qgis/zoom_factor", 2, type = float)
        self.mapCanvas.setWheelAction(QgsMapCanvas.WheelAction(action), zoomFactor)
        horizontalLayout.addWidget(self.mapCanvas)
        self.mapWidget.setLayout(horizontalLayout)
        self.panTool = QgsMapToolPan(self.mapCanvas)
        self.mapCanvas.setMapTool(self.panTool)

        versions = repo.log(path = path)
        if versions:
            for commit in versions:
                item = CommitListItem(commit, repo, path)
                self.listWidget.addItem(item)
                ''''w = CommitListItemWidget(commit)
                self.ui.listWidget.setItemWidget(item, w)'''
        else:
            raise GeoGigException("The selected feature is not versioned yet")


    def commitClicked(self):
        feature = self.listWidget.currentItem().feature
        geom = None
        self.attributesTable.setRowCount(len(feature))
        for idx, attrname in enumerate(feature):
            value = feature[attrname]
            font = QFont()
            font.setBold(True)
            font.setWeight(75)
            item = QTableWidgetItem(attrname)
            item.setFont(font)
            self.attributesTable.setItem(idx, 0, item);
            self.attributesTable.setItem(idx, 1, QTableWidgetItem(str(value)));
            if geom is None:
                try:
                    geom = QgsGeometry.fromWkt(value)
                except:
                    pass

        self.attributesTable.resizeRowsToContents()
        self.attributesTable.horizontalHeader().setMinimumSectionSize(150)
        self.attributesTable.horizontalHeader().setStretchLastSection(True)

        settings = QSettings()
        prjSetting = settings.value('/Projections/defaultBehaviour')
        settings.setValue('/Projections/defaultBehaviour', '')
        types = ["Point", "LineString", "Polygon"]
        layers = []
        if geom is not None:
            geomtype = types[int(geom.type())]
            layer = loadLayerNoCrsDialog(geomtype + "?crs=EPSG:4326", "temp", "memory")
            pr = layer.dataProvider()
            feat = QgsFeature()
            feat.setGeometry(geom)
            pr.addFeatures([feat])
            layer.updateExtents()
            layer.selectAll()
            layer.setExtent(layer.boundingBoxOfSelected())
            layer.invertSelection()
            symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())
            symbol.setColor(Qt.green)
            symbol.setAlpha(0.5)
            if QGis.QGIS_VERSION_INT < 29900:
                layer.setRendererV2(QgsSingleSymbolRendererV2(symbol))
            else:
                layer.setRenderer(QgsSingleSymbolRenderer(symbol))
            self.mapCanvas.setRenderFlag(False)
            self.mapCanvas.setLayerSet([QgsMapCanvasLayer(layer)])
            QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            self.mapCanvas.setExtent(layer.extent())
            self.mapCanvas.setRenderFlag(True)
            layers.append(layer)
        else:
            self.mapCanvas.setLayerSet([])
        settings.setValue('/Projections/defaultBehaviour', prjSetting)


class CommitListItemWidget(QLabel):
    def __init__(self, commit):
        QTextEdit.__init__(self)
        self.setWordWrap(False)
        self.commit = commit
        size = self.font().pointSize()
        text = ('<b><font style="font-size:%spt">%s</font></b>'
            '<br><font color="#5f6b77" style="font-size:%spt"><b>%s</b> by <b>%s</b></font> '
            '<font color="#5f6b77" style="font-size:%spt; background-color:rgb(225,225,225)"> %s </font>' %
            (str(size), self.commit.message.splitlines()[0], str(size - 1),
             self.commit.authorprettydate(), self.commit.authorname, str(size - 1), self.commit.id[:10]))
        self.setText(text)

class CommitListItem(QListWidgetItem):

    icon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "person.png"))

    def __init__(self, commit, repo, path):
        QListWidgetItem.__init__(self)
        self.commit = commit
        self._feature = None
        self.repo = repo
        self.path = path
        self.setText("%s (by %s)" % (commit.message.splitlines()[0], commit.authorname))

    @property
    def feature(self):
        if self._feature is None:
            self._feature = self.repo.feature(self.path, self.commit)
        return self._feature
