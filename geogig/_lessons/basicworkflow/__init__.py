# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from qgis.utils import iface

from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QDialog
from qgis.PyQt.QtCore import QTimer

from lessons.lesson import Step
from lessons.utils import layerFromName, unmodalWidget

from geogig._lessons import GeoGigLesson, _openNavigator, cleanLessonRepo
import geogig._lessons as ls
from geogig.tools.layers import hasLocalChanges
from geogig.geogigwebapi import repository

def checkVersions(n):
    log = ls._lastRepo.log()
    return len(log) == n

def checkEdited(layername):
    layer = layerFromName(layername)
    if layer:
        return len(hasLocalChanges(layer)) > 0
    else:
        return False

def checkRepoCreated():
    if len(repository.repos) == 1:
        ls._lastRepo = repository.repos[0]
        return True
    else:
        return False

lesson = GeoGigLesson("01. Basic GeoGig workflow")
lesson.addStep("Open GeoGig navigator", "Open GeoGig navigator",
               lambda: _openNavigator())
lesson.addStep("Create new repository", "01_create_new_repository.md",
               steptype=Step.MANUALSTEP, endcheck=checkRepoCreated)
lesson.addStep("Import layer", "02_import_layer.md",
               prestep=lambda: unmodalWidget("ImportDialog", 300, 1000),
               endcheck=lambda: checkVersions(1),
               steptype=Step.MANUALSTEP)
lesson.addStep("Edit layer", "03_edit_layer.md",
               endcheck=lambda: checkEdited("Buildings"),
               steptype=Step.MANUALSTEP)
lesson.addStep("Check local changes", "04_check_local_changes.md",
               prestep=lambda: unmodalWidget("DiffViewerDialog", 300, 1000),
               steptype=Step.MANUALSTEP)
lesson.addStep("Sync layer with repository", "05_sync_layer.md",
               prestep=lambda: unmodalWidget("CommitDialog", 300, 1000),
               endcheck=lambda: checkVersions(2),
               steptype=Step.MANUALSTEP)
lesson.setCleanup(cleanLessonRepo)