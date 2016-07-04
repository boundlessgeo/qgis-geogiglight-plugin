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

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import sqlite3
from qgis.core import *
import os
from qgis.utils import iface

ALL_TYPES = -1

class WrongLayerNameException(BaseException) :
    pass

class WrongLayerSourceException(BaseException) :
    pass

def resolveLayer(name):
    layers = getAllLayers()
    for layer in layers:
        if layer.name() == name:
            return layer
    raise WrongLayerNameException()

def resolveLayerFromSource(source):
    layers = getAllLayers()
    for layer in layers:
        if os.path.normcase(layer.source()) == os.path.normcase(source):
            return layer
    raise WrongLayerSourceException()


def getVectorLayers(shapetype = -1):
    layers = iface.legendInterface().layers()
    vector = list()
    for layer in layers:
        if layer.type() == layer.VectorLayer:
            if shapetype == ALL_TYPES or layer.geometryType() == shapetype:
                uri = unicode(layer.source())
                if not uri.lower().endswith("csv") and not uri.lower().endswith("dbf"):
                    vector.append(layer)
    return vector

def getAllLayers():
    return getVectorLayers()

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
    geogigFid = cursor.fetchone()[0]
    cursor.close()
    return geogigFid

def formatSource(source):
    if isinstance(source, QgsVectorLayer):
        source = source.source()
    source = os.path.normcase(source)

    if "|" in source:
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
    source = formatSource(layer.source())
    filename, layername = source.split("|")
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
