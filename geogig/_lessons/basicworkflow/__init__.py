# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from qgis.utils import iface

from lessons.lesson import Step

from geogig._lessons import GeoGigLesson, openTestProject, _openNavigator, createEmptyTestRepo
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


lesson = GeoGigLesson("Basic GeoGig workflow")
lesson.addStep("Create empty repository", "Create empty repository",
               function = lambda: createEmptyTestRepo())
lesson.addStep("Open GeoGig navigator", "Open GeoGig navigator", lambda: _openNavigator())
lesson.addStep("Import layer", "import.html", endcheck=lambda: checkVersions(1), steptype=Step.MANUALSTEP)
lesson.addStep("Edit layer", "edit.html", endcheck=checkEdited, steptype=Step.MANUALSTEP)
lesson.addStep("Sync layer with repository", "sync.html", endcheck=lambda: checkVersions(2), steptype=Step.MANUALSTEP)
