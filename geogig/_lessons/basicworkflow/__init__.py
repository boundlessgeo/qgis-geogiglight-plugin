# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from geogig._lessons import GeoGigLesson
from lessons.lesson import Step
from lessons.utils import *
from qgis.utils import iface
from geogig._lessons import checkGeoGig
from geogig.tests import _createTestRepo
from geogig.tests.testplugin import openTestProject, _openNavigator
from geogig import tests
from geogig.tools.layers import hasLocalChanges

def checkVersions(n):
    log = tests._lastRepo.log()
    return len(log) == n

def checkEdited():
    layer = iface.activeLayer()
    if layer:
        return hasLocalChanges(layer)
    else:
        return False


lesson = GeoGigLesson("Basic GeoGig workflow")
lesson.addStep("Prepare GeoGig environment", "../common/preparegeogig.html",
               endcheck=checkGeoGig, steptype=Step.MANUALSTEP)
lesson.addStep("Open test data", "Open test data", lambda: openTestProject("points"))
lesson.addStep("Create empty repository", "Create empty repository",
               function = lambda: _createTestRepo("empty", True, "Lesson repos", "repo"))
lesson.addStep("Open GeoGig navigator", "Open GeoGig navigator", lambda: _openNavigator(group = "Lesson repos"))
lesson.addStep("Import layer", "import.html", endcheck=lambda: checkVersions(1), steptype=Step.MANUALSTEP)
lesson.addStep("Edit layer", "edit.html", endcheck=checkEdited, steptype=Step.MANUALSTEP)
lesson.addStep("Sync layer with repository", "sync.html", endcheck=lambda: checkVersions(2), steptype=Step.MANUALSTEP)

