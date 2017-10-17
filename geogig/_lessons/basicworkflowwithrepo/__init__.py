# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from qgis.core import QgsMapLayerRegistry
from qgis.utils import iface

from lessons.utils import layerFromName

from lessons.lesson import Step

from geogig._lessons import GeoGigLesson, openTestProject, _openNavigator, \
    createExampleRepo, add_more_commits
import geogig._lessons as ls
from geogig.tools.layers import hasLocalChanges


def checkVersions(n):
    log = ls._lastRepo.log()
    return len(log) == n

def checkBranches(n):
    branches = ls._lastRepo.branches()
    return len(branches) == n

def checkEdited(layername):
    layer = layerFromName(layername)
    if layer:
        return len(hasLocalChanges(layer)) > 0
    else:
        return False

def checkLayerInProject(layername):
    layer = layerFromName(layername)
    return layer is not None


lesson = GeoGigLesson("02. GeoGig workflow with branching")
lesson.addStep("Create repository", "Create repository",
               function=lambda: createExampleRepo())
lesson.addStep("Open GeoGig navigator",
               "Open GeoGig navigator",
               lambda: _openNavigator())
lesson.addStep("Export layer", "01_export_layer.md",
               endcheck=lambda: checkLayerInProject("buildings"),
               steptype=Step.MANUALSTEP)
lesson.addStep("Create a branch", "02_create_branch.md",
               endcheck=lambda: checkBranches(2),
               steptype=Step.MANUALSTEP)
lesson.addStep("Edit layer", "03_edit_layer.md",
               endcheck=lambda: checkEdited( "buildings"),
               steptype=Step.MANUALSTEP)
lesson.addStep("Sync layer with repository", "04_sync_layer.md",
               #endcheck=lambda: checkVersions(2),
               steptype=Step.MANUALSTEP)
lesson.addStep("Add more commits", "Add more commits",
               function=lambda: add_more_commits())
lesson.addStep("Check changes between commits",
               "05_check_changes_between_commits.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Merge branch", "06_merge_edits_branch.md",
               steptype=Step.MANUALSTEP)