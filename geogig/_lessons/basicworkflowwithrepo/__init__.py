# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from qgis.core import QgsMapLayerRegistry
from qgis.utils import iface

from lessons.lesson import Step

from geogig._lessons import GeoGigLesson, openTestProject, _openNavigator, createSimpleTestRepo
import geogig._lessons as ls
from geogig.tools.layers import hasLocalChanges


def checkVersions(n):
    log = ls._lastRepo.log()
    return len(log) == n


def checkEdited():
    layer = iface.activeLayer()
    if layer:
        return hasLocalChanges(layer)
    else:
        return False


def layerFromName(name):
    layers = list(QgsMapLayerRegistry.instance().mapLayers().values())
    for layer in layers:
        if layer.name() == name:
            return layer


def checkLayerInProject():
    layer = layerFromName("points")
    return layer is not None


lesson = GeoGigLesson("Basic GeoGig workflow with an existing repo")
lesson.addStep("Create repository", "Create repository",
               function = lambda: createSimpleTestRepo())
lesson.addStep("Open GeoGig navigator", "Open GeoGig navigator", lambda: _openNavigator())
lesson.addStep("Export layer", "export.html", endcheck=checkLayerInProject, steptype=Step.MANUALSTEP)
lesson.addStep("Edit layer", "edit.html", endcheck=checkEdited, steptype=Step.MANUALSTEP)
lesson.addStep("Sync layer with repository", "sync.html", endcheck=lambda: checkVersions(2), steptype=Step.MANUALSTEP)
