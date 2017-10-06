# -*- coding: utf-8 -*-

"""
***************************************************************************
    layers.py
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
import sqlite3

from qgis.core import (QgsMapLayerRegistry,
                       QgsRasterLayer,
                       QgsVectorLayer,
                       QgsFeatureRequest,
                       QgsGeometry,
                       QgsFeature
                      )
from qgis.utils import iface

from qgiscommons2.files import tempFilename
from qgiscommons2.layers import loadLayerNoCrsDialog, vectorLayers

ALL_TYPES = -1

class WrongLayerSourceException(BaseException) :
    pass

def layerFromSource(source):
    layers = vectorLayers()
    for layer in layers:
        if formatSource(layer.source()) == formatSource(source):
            return layer
    raise WrongLayerSourceException()


def getGroups():
    groups = {}
    rels = iface.legendInterface().groupLayerRelationship()
    for rel in rels:
        groupName = rel[0]
        if groupName != '':
            groupLayers = rel[1]
            groups[groupName] = [QgsMapLayerRegistry.instance().mapLayer(layerid) for layerid in groupLayers]
    return groups


def geogigFidFromGpkgFid(trackedlayer, fid):
    con = sqlite3.connect(trackedlayer.geopkg)
    tablename = trackedlayer.layername + "_fids"
    cursor = con.cursor()
    cursor.execute("SELECT geogig_fid FROM %s WHERE gpkg_fid = %s;" % (tablename, fid))
    try:
        geogigFid = cursor.fetchone()[0]
        return geogigFid
    except:
        return fid
    finally:
        cursor.close()


def formatSource(source):
    # Skip if it's a raster
    # TODO: maybe better raise a LayerNotSupported exception
    if isinstance(source, QgsRasterLayer):
        return None
    if isinstance(source, QgsVectorLayer):
        source = source.source()
    source = os.path.normcase(source)

    ext = source.split(".")[-1].lower()
    if ext not in ["geopkg", "gpkg"]:
        return source

    if "|" not in source:
        layername = layersInGpkgFile(source)[0]
        source = source + "|layername=" + layername

    return source

def layersInGpkgFile(f):
    if os.path.exists(f):
        con = sqlite3.connect(f)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        layers = [t[0] for t in cursor.fetchall()]
        layers = [lay for lay in layers if not lay.startswith("gpkg_") and not lay.startswith("tree_")]
        return layers
    else:
        return [os.path.splitext(os.path.basename(f))[0]]


def namesFromLayer(layer):
    source = formatSource(layer)
    tokens = source.split("|")
    filename = tokens[0]
    layername = tokens[1]
    layername = layername.split("=")[-1]
    return filename, layername

def hasLocalChanges(layer):
    filename, layername = namesFromLayer(layer)
    con = sqlite3.connect(filename)
    cursor = con.cursor()
    cursor.execute("SELECT * FROM %s_audit;" % layername)
    changes = cursor.fetchall()
    cursor.close()
    con.close()
    return changes

ADDED, REMOVED, MODIFIED_BEFORE, MODIFIED_AFTER = list(range(4))

resourcesPath = os.path.join(os.path.dirname(__file__), os.pardir, "resources")
diffStylePoints = os.path.join(resourcesPath, "difflayer_points.qml")
diffStyleLines = os.path.join(resourcesPath, "difflayer_lines.qml")
diffStylePolygons = os.path.join(resourcesPath, "difflayer_polygons.qml")

def gpkgfidFromGeogigfid(cursor, layername, geogigfid):
    cursor.execute("SELECT gpkg_fid FROM %s_fids WHERE geogig_fid='%s';" % (layername, geogigfid))
    gpkgfid = int(cursor.fetchone()[0])
    return gpkgfid

def addDiffLayer(repo, layername, commit, commit2):

    styles = [diffStylePoints, diffStyleLines, diffStylePolygons]
    geomTypes = ["Point","LineString","Polygon"]
    beforeFilename = tempFilename("gpkg")
    repo.exportdiff(layername, commit.commitid, commit2.commitid, beforeFilename)
    beforeLayer = loadLayerNoCrsDialog(beforeFilename, layername, "ogr")
    afterFilename = tempFilename("gpkg")
    repo.exportdiff(layername, commit2.commitid, commit.commitid, afterFilename)
    afterLayer = loadLayerNoCrsDialog(afterFilename, layername, "ogr")

    beforeCon = sqlite3.connect(beforeFilename)
    beforeCursor = beforeCon.cursor()
    afterCon = sqlite3.connect(afterFilename)
    afterCursor = afterCon.cursor()

    attributes = [v[1] for v in beforeCursor.execute("PRAGMA table_info('%s');" % layername)]
    attrnames = [f.name() for f in beforeLayer.pendingFields()]

    layerFeatures = []

    beforeCursor.execute("SELECT * FROM %s_changes WHERE audit_op=2;" % layername)
    modified = beforeCursor.fetchall()
    for m in modified:
        geogigfid = m[0]
        beforeGpkgfid = gpkgfidFromGeogigfid(beforeCursor, layername, geogigfid)
        beforeCursor.execute("SELECT * FROM %s WHERE fid='%s';" % (layername, beforeGpkgfid))
        featureRow = beforeCursor.fetchone()
        attrs = {attr: featureRow[attributes.index(attr)] for attr in attrnames}
        attrs["changetype"] = MODIFIED_BEFORE
        request = QgsFeatureRequest()
        request.setFilterFid(beforeGpkgfid)
        feature = next(beforeLayer.getFeatures(request))
        layerFeatures.append({"attrs":attrs, "geom": QgsGeometry(feature.geometry())})
        afterGpkgfid = gpkgfidFromGeogigfid(afterCursor, layername, geogigfid)
        afterCursor.execute("SELECT * FROM %s WHERE fid='%s';" % (layername,afterGpkgfid))
        featureRow = afterCursor.fetchone()
        attrs = {attr: featureRow[attributes.index(attr)] for attr in attrnames}
        attrs["changetype"] = MODIFIED_AFTER
        request = QgsFeatureRequest()
        request.setFilterFid(afterGpkgfid)
        feature = next(afterLayer.getFeatures(request))
        layerFeatures.append({"attrs":attrs, "geom": QgsGeometry(feature.geometry())})


    afterCursor.execute("SELECT * FROM %s_changes WHERE audit_op=1;" % layername)
    added = afterCursor.fetchall()
    for a in added:
        geogigfid = a[0]
        afterGpkgfid = gpkgfidFromGeogigfid(afterCursor, layername, geogigfid)
        afterCursor.execute("SELECT * FROM %s WHERE fid='%s';" % (layername, afterGpkgfid))
        featureRow = afterCursor.fetchone()
        attrs = {attr: featureRow[attributes.index(attr)] for attr in attrnames}
        attrs["changetype"] = ADDED
        request = QgsFeatureRequest()
        request.setFilterFid(afterGpkgfid)
        feature = next(afterLayer.getFeatures(request))
        layerFeatures.append({"attrs":attrs, "geom": QgsGeometry(feature.geometry())})

    beforeCursor.execute("SELECT * FROM %s_changes WHERE audit_op=1;" % layername)
    removed = beforeCursor.fetchall()
    for r in removed:
        geogigfid = r[0]
        beforeGpkgfid = gpkgfidFromGeogigfid(beforeCursor, layername, geogigfid)
        beforeCursor.execute("SELECT * FROM %s WHERE fid='%s';" % (layername, beforeGpkgfid))
        featureRow = beforeCursor.fetchone()
        attrs = {attr: featureRow[attributes.index(attr)] for attr in attrnames}
        attrs["changetype"] = REMOVED
        request = QgsFeatureRequest()
        request.setFilterFid(beforeGpkgfid)
        feature = next(beforeLayer.getFeatures(request))
        layerFeatures.append({"attrs":attrs, "geom": QgsGeometry(feature.geometry())})

    attrnames.append("changetype")
    uriFields = "&".join(["field=%s" % f for f in attrnames])
    uri = "%s?crs=%s&%s" % (geomTypes[beforeLayer.geometryType()], beforeLayer.crs().authid(), uriFields)
    layer = QgsVectorLayer(uri, "diff", "memory")
    featuresList = []
    for feature in layerFeatures:
        qgsfeature = QgsFeature()
        qgsfeature.setGeometry(feature["geom"])
        qgsfeature.setAttributes([feature["attrs"][attr] for attr in attrnames])
        featuresList.append(qgsfeature)

    layer.dataProvider().addFeatures(featuresList)
    layer.updateExtents()
    QgsMapLayerRegistry.instance().addMapLayers([layer])
    layer.loadNamedStyle(styles[layer.geometryType()])
