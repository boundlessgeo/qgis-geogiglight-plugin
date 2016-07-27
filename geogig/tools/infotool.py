# -*- coding: utf-8 -*-

"""
***************************************************************************
    infotool.py
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


from PyQt4 import QtCore, QtGui
from qgis.core import *
from qgis.gui import *
from geogig.tools import layertracking
from geogig.gui.dialogs.blamedialog import BlameDialog
from geogig.gui.dialogs.versionsviewer import VersionViewerDialog
from geogig import config
from geogig.geogigwebapi.repository import Repository, GeoGigException
from geogig.tools.layers import geogigFidFromGpkgFid


class MapToolGeoGigInfo(QgsMapTool):

    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.setCursor(QtCore.Qt.CrossCursor)

    def canvasPressEvent(self, e):
        layer = config.iface.activeLayer()
        if layer is None or not isinstance(layer, QgsVectorLayer):
            config.iface.messageBar().pushMessage("No layer selected or the current active layer is not a valid vector layer",
                                                  level = QgsMessageBar.WARNING, duration = 5)
            return
        if not layertracking.isRepoLayer(layer):
            config.iface.messageBar().pushMessage("The current active layer is not being tracked as part of a GeoGig repo",
                                                  level = QgsMessageBar.WARNING, duration = 5)
            return

        trackedlayer = layertracking.getTrackingInfo(layer)
        point = self.toMapCoordinates(e.pos())
        searchRadius = self.canvas().extent().width() * .01;
        r = QgsRectangle()
        r.setXMinimum(point.x() - searchRadius);
        r.setXMaximum(point.x() + searchRadius);
        r.setYMinimum(point.y() - searchRadius);
        r.setYMaximum(point.y() + searchRadius);

        r = self.toLayerCoordinates(layer, r);

        fit = layer.getFeatures(QgsFeatureRequest().setFilterRect(r).setFlags(QgsFeatureRequest.ExactIntersect));
        fid = None
        try:
            feature = fit.next()
            fid = feature.id()
            fid = geogigFidFromGpkgFid(trackedlayer, fid)
            if fid is None:
                return
        except StopIteration, e:
            return
        repo = Repository(trackedlayer.repoUrl)

        menu = QtGui.QMenu()
        versionsAction = QtGui.QAction("Show all versions of this feature...", None)
        versionsAction.triggered.connect(lambda: self.versions(repo, trackedlayer.layername, fid))
        menu.addAction(versionsAction)
        blameAction = QtGui.QAction("Show authorship...", None)
        blameAction.triggered.connect(lambda: self.blame(repo, trackedlayer.layername, fid))
        menu.addAction(blameAction)
        point = config.iface.mapCanvas().mapToGlobal(e.pos())
        menu.exec_(point)

    def versions(self, repo, tree, fid):
        try:
            path = unicode(tree) + "/" + unicode(fid)
            dlg = VersionViewerDialog(repo, path)
            dlg.exec_()
        except GeoGigException, e:
            QtGui.QMessageBox.critical(self.parent(), "Error", "%s" % e)


    def blame(self, repo, tree, fid):
        try:
            path = "%s/%s" % (tree, fid)
            dlg = BlameDialog(repo, path)
            dlg.exec_()
        except GeoGigException, e:
            QtGui.QMessageBox.critical(self.parent(), "Error", "%s" % e)
