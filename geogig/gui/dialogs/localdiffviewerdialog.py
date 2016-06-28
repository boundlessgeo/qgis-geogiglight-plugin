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
from geogig.tools.layers import namesFromLayer
import sqlite3
from geogig.tools.layertracking import getTrackingInfo
from geogig.geogigwebapi.repository import Repository
from geogig.geogigwebapi.diff import LocalDiff

MODIFIED, ADDED, REMOVED = "M", "A", "R"

layerIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "layer_group.gif"))
featureIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "geometry.png"))
addedIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "added.png"))
removedIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "removed.png"))
modifiedIcon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "modified.gif"))

sys.path.append(os.path.dirname(__file__))
pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'localdiffviewerdialog.ui'))

class LocalDiffViewerDialog(WIDGET, BASE):

    def __init__(self, parent, layer):
        QtGui.QDialog.__init__(self, parent,
                               QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.layer = layer
        self.setupUi(self)

        self.setWindowFlags(self.windowFlags() |
                              QtCore.Qt.WindowSystemMenuHint |
                              QtCore.Qt.WindowMinMaxButtonsHint)

        self.attributesTable.customContextMenuRequested.connect(self.showContextMenu)
        self.featuresTree.itemClicked.connect(self.treeItemClicked)

        self.featuresTree.header().hide()

        self.computeDiffs()

    def treeItemClicked(self, item):
        if item.childCount():
            return
        color = {"MODIFIED": QtGui.QColor(255, 170, 0), "ADDED":QtCore.Qt.green,
                 "REMOVED":QtCore.Qt.red , "NO_CHANGE":QtCore.Qt.white}
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
            self.attributesTable.setItem(i, 0, DiffItem(oldfeature[attrib]))
            self.attributesTable.setItem(i, 1, DiffItem(newfeature[attrib]))
            attribChangeType = changeTypeName[changetype]
            if changetype == LOCAL_FEATURE_MODIFIED and oldfeature[attrib] == newfeature[attrib]:
                attribChangeType = "NO_CHANGE"
            self.attributesTable.setItem(i, 2, QtGui.QTableWidgetItem(attribChangeType))
            for col in range(3):
                self.attributesTable.item(i, col).setBackgroundColor(color[attribChangeType]);
        self.attributesTable.resizeColumnsToContents()
        self.attributesTable.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)

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
            menu = QtGui.QMenu()
            viewAction = QtGui.QAction("View geometry changes...", None)
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
        layerItem = QtGui.QTreeWidgetItem()
        layerItem.setText(0, self.layer.name())
        layerItem.setIcon(0, layerIcon)
        self.featuresTree.addTopLevelItem(layerItem)
        addedItem = QtGui.QTreeWidgetItem()
        addedItem.setText(0, "Added")
        addedItem.setIcon(0, addedIcon)
        removedItem = QtGui.QTreeWidgetItem()
        removedItem.setText(0, "Removed")
        removedItem.setIcon(0, removedIcon)
        modifiedItem = QtGui.QTreeWidgetItem()
        modifiedItem.setText(0, "Modified")
        modifiedItem.setIcon(0, modifiedIcon)
        layerSubItems = {LOCAL_FEATURE_ADDED: addedItem,
                                    LOCAL_FEATURE_REMOVED: removedItem,
                                    LOCAL_FEATURE_MODIFIED: modifiedItem}

        for c in self.changes.values():
            item = QtGui.QTreeWidgetItem()
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
        QtGui.QDialog.reject(self)

    def localChanges(self, layer):
        filename, layername = namesFromLayer(layer)
        con = sqlite3.connect(filename)
        cursor = con.cursor()
        attributes = [v[1] for v in cursor.execute("PRAGMA table_info('%s');" % layername)]
        cursor.execute("SELECT * FROM %s_audit;" % layername)
        changes = cursor.fetchall()
        changesdict = {}
        tracking = getTrackingInfo(layer)
        repo = Repository(tracking.repoUrl)
        cursor.execute("SELECT commit_id FROM geogig_audited_tables WHERE table_name='%s';" % layername)
        commitid = cursor.fetchone()[0]
        for c in changes:
            featurechanges = {attr: c[attributes.index(attr)] for attr in [f.name() for f in layer.pendingFields()]}
            path = str(c[attributes.index("fid")])
            try:
                request = QgsFeatureRequest()
                request.setFilterFid(int(path.split("/")[-1]))
                feature = layer.getFeatures(request).next()
                featurechanges["the_geom"] = feature.geometry().exportToWkt()
            except:
                featurechanges["the_geom"] = None
            changesdict[path] = LocalDiff(layername, path, repo, featurechanges, commitid, c[-1])
        return changesdict


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

