# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from qgis.utils import iface

from lessons.utils import layerFromName, unmodalWidget
from lessons.lesson import Step

from geogig._lessons import GeoGigLesson, openTestProject, _openNavigator, \
    createExampleRepo, addMoreCommits
import geogig._lessons as ls
from geogig.tools.layers import hasLocalChanges
from geogig.geogigwebapi.commit import Commit

def checkVersions(n, branch="master"):
    log = ls._lastRepo.log(until=branch)
    return len(log) == n

def checkBranches(n):
    branches = ls._lastRepo.branches()
    return len(branches) == n

def checkBranch(name):
    branches = ls._lastRepo.branches()
    return name in branches

def checkEdited(layername):
    layer = layerFromName(layername)
    if layer:
        return len(hasLocalChanges(layer)) > 0
    else:
        return False

def checkHasMerged():
    commit = Commit.fromref(ls._lastRepo, "master")
    return len(commit.parents) == 2

def checkLayerInProject(layername):
    layer = layerFromName(layername)
    return layer is not None

lesson = GeoGigLesson("02. GeoGig workflow with branching")
lesson.addStep("Create repository", "Create repository",
               function=createExampleRepo)
lesson.addStep("Open GeoGig navigator",
               "Open GeoGig navigator",
               lambda: _openNavigator())
lesson.addStep("Export layer", "01_export_layer.md",
               endcheck=lambda: checkLayerInProject("buildings"),
               steptype=Step.MANUALSTEP)
lesson.addStep("Create a branch", "02_create_branch.md",
               endcheck=lambda: checkBranch("john_edits"),
               steptype=Step.MANUALSTEP)
lesson.addStep("Edit layer", "03_edit_layer.md",
               endcheck=lambda: checkEdited( "buildings"),
               steptype=Step.MANUALSTEP)
lesson.addStep("Sync layer with repository", "04_sync_layer.md",
               prestep=lambda: unmodalWidget("CommitDialog", 300, 1000),
               endcheck=lambda: checkVersions(4, "john_edits"),
               steptype=Step.MANUALSTEP)
lesson.addStep("Add more commits", "Add more commits",
               function=addMoreCommits)
lesson.addStep("Check changes between commits",
               "05_check_changes_between_commits.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Merge branch", "06_merge_edits_branch.md",
               steptype=Step.MANUALSTEP,
               endcheck=checkHasMerged)
