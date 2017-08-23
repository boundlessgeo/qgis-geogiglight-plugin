# -*- coding: utf-8 -*-

"""
***************************************************************************
    localdiffviewerdialog.py
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
import sqlite3

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import (QTableWidgetItem,
                                 QHeaderView,
                                 QMenu,
                                 QAction,
                                 QTreeWidgetItem,
                                 QDialog
                                )
from qgis.core import QgsGeometry, QgsCoordinateReferenceSystem, QgsFeatureRequest

from geogig import config
from qgiscommons2.gui import execute
from geogig.gui.dialogs.geogigref import RefPanel
from geogig.gui.dialogs.geometrydiffviewerdialog import GeometryDiffViewerDialog
from geogig.geogigwebapi.commit import Commit
from geogig.geogigwebapi.repository import Repository
from geogig.geogigwebapi.diff import LocalDiff, LOCAL_FEATURE_ADDED, LOCAL_FEATURE_MODIFIED, LOCAL_FEATURE_REMOVED
from geogig.tools.layers import namesFromLayer, geogigFidFromGpkgFid
from geogig.tools.layertracking import getTrackingInfo

MODIFIED, ADDED, REMOVED = "M", "A", "R"

layerIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "layer_group.svg"))
featureIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "geometry.png"))
addedIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "added.png"))
removedIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "removed.png"))
modifiedIcon = QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "modified.gif"))

sys.path.append(os.path.dirname(__file__))
pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'localdiffviewerdialog.ui'))

class LocalDiffViewerDialog(WIDGET, BASE):

    def __init__(self, parent, layer):
        super(LocalDiffViewerDialog, self).__init__(parent,
                               Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.layer = layer
        self.setupUi(self)

        self.setWindowFlags(self.windowFlags() |
                            Qt.WindowSystemMenuHint)

        self.attributesTable.customContextMenuRequested.connect(self.showContextMenu)
        self.featuresTree.itemClicked.connect(self.treeItemClicked)

        self.featuresTree.header().hide()

        self.computeDiffs()

    def treeItemClicked(self, item):
        if item.childCount():
            return
        color = {"MODIFIED": QColor(255, 170, 0), "ADDED":Qt.green,
                 "REMOVED":Qt.red , "NO_CHANGE":Qt.white}
        changeTypeName = ["", "ADDED", "MODIFIED", "REMOVED"]
        path = item.text(0)
        if path not in self.changes:
            return
        oldfeature = self.changes[path].oldfeature
        newfeature = self.changes[path].newfeature
        changetype = self.changes[path].changetype
        self.attributesTable.clear()
        self.attributesTable.verticalHeader().show()
        self.attributesTable.horizontalHeader().show()
        self.attributesTable.setRowCount(len(newfeature))
        self.attributesTable.setVerticalHeaderLabels([a for a in newfeature])
        self.attributesTable.setHorizontalHeaderLabels(["Old value", "New value", "Change type"])
        for i, attrib in enumerate(newfeature):
            self.attributesTable.setItem(i, 0, DiffItem(oldfeature.get(attrib, None)))
            self.attributesTable.setItem(i, 1, DiffItem(newfeature.get(attrib, None)))
            attribChangeType = changeTypeName[changetype]
            if changetype == LOCAL_FEATURE_MODIFIED:
                oldvalue = oldfeature.get(attrib, None)
                newvalue = newfeature.get(attrib, None)
                try:# to avoid false change detection due to different precisions
                    oldvalue = QgsGeometry.fromWkt(oldvalue).exportToWkt(7)
                    newvalue = QgsGeometry.fromWkt(newvalue).exportToWkt(7)
                except:
                    pass
                if oldvalue == newvalue:
                    attribChangeType = "NO_CHANGE"
            self.attributesTable.setItem(i, 2, QTableWidgetItem(attribChangeType))
            for col in range(3):
                self.attributesTable.item(i, col).setBackgroundColor(color[attribChangeType]);
        self.attributesTable.resizeColumnsToContents()
        self.attributesTable.horizontalHeader().setResizeMode(QHeaderView.Stretch)

    def showContextMenu(self, point):
        row = self.attributesTable.selectionModel().currentIndex().row()
        geom1 = self.attributesTable.item(row, 0).value
        geom2 = self.attributesTable.item(row, 1).value
        try:
            qgsgeom1 = QgsGeometry.fromWkt(geom1)
            qgsgeom2 = QgsGeometry.fromWkt(geom2)
        except:
            return
        if qgsgeom1 is not None and qgsgeom2 is not None:
            menu = QMenu()
            viewAction = QAction("View geometry changes...", None)
            viewAction.triggered.connect(lambda: self.viewGeometryChanges(qgsgeom1, qgsgeom2))
            menu.addAction(viewAction)
            globalPoint = self.attributesTable.mapToGlobal(point)
            menu.exec_(globalPoint)

    def viewGeometryChanges(self, g1, g2):
        dlg = GeometryDiffViewerDialog([g1, g2], QgsCoordinateReferenceSystem("EPSG:4326")) #TODO set CRS correctly
        dlg.exec_()


    def computeDiffs(self):
        self.featuresTree.clear()
        self.changes = self.localChanges(self.layer)
        layerItem = QTreeWidgetItem()
        layerItem.setText(0, self.layer.name())
        layerItem.setIcon(0, layerIcon)
        self.featuresTree.addTopLevelItem(layerItem)
        addedItem = QTreeWidgetItem()
        addedItem.setText(0, "Added")
        addedItem.setIcon(0, addedIcon)
        removedItem = QTreeWidgetItem()
        removedItem.setText(0, "Removed")
        removedItem.setIcon(0, removedIcon)
        modifiedItem = QTreeWidgetItem()
        modifiedItem.setText(0, "Modified")
        modifiedItem.setIcon(0, modifiedIcon)
        layerSubItems = {LOCAL_FEATURE_ADDED: addedItem,
                         LOCAL_FEATURE_REMOVED: removedItem,
                         LOCAL_FEATURE_MODIFIED: modifiedItem}

        for c in list(self.changes.values()):
            item = QTreeWidgetItem()
            item.setText(0, c.fid)
            item.setIcon(0, featureIcon)
            layerSubItems[c.changetype].addChild(item)

        for i in [LOCAL_FEATURE_ADDED, LOCAL_FEATURE_REMOVED, LOCAL_FEATURE_MODIFIED]:
            layerItem.addChild(layerSubItems[i])
            layerSubItems[i].setText(0, "%s [%i features]" % (layerSubItems[i].text(0), layerSubItems[i].childCount()))

        self.attributesTable.clear()
        self.attributesTable.verticalHeader().hide()
        self.attributesTable.horizontalHeader().hide()


    def reject(self):
        QDialog.reject(self)

    def localChanges(self, layer):
        filename, layername = namesFromLayer(layer)
        con = sqlite3.connect(filename)
        cursor = con.cursor()
        attributes = [v[1] for v in cursor.execute("PRAGMA table_info('%s');" % layername)]
        attrnames = [a for a in attributes if a != "fid"]
        cursor.execute("SELECT * FROM %s_audit;" % layername)
        changes = cursor.fetchall()
        changesdict = {}
        tracking = getTrackingInfo(layer)
        repo = Repository(tracking.repoUrl)
        commitid = cursor.execute("SELECT commit_id FROM geogig_audited_tables WHERE table_name='%s';" % layername).fetchone()[0]
        geomField = cursor.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name='%s';" % layername).fetchone()[0]
        for c in changes:
            featurechanges = {}
            path = str(c[attributes.index("fid")])
            for attr in attrnames:
                if c[-1] == LOCAL_FEATURE_REMOVED:
                    value = None
                else:
                    if attr != geomField:
                        value = c[attributes.index(attr)]
                    else:
                        request = QgsFeatureRequest().setFilterExpression("fid=%s" % path)
                        features = list(layer.getFeatures(request))
                        if len(features) == 0:
                            continue
                        value = features[0].geometry().exportToWkt().upper()
                featurechanges[attr] = value
            path = geogigFidFromGpkgFid(tracking, path)
            changesdict[path] = LocalDiff(layername, path, repo, featurechanges, commitid, c[-1])
        return changesdict


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
