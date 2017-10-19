# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from geogig._lessons import GeoGigLesson
from lessons.lesson import Step
from lessons.utils import *
from qgis.utils import iface
from geogig._lessons import GeoGigLesson, openTestProject, _openNavigator, \
    createExampleRepo, _exportAndEditLayer
import geogig._lessons as ls

lesson = GeoGigLesson("03. Visualizing differences between versions")
lesson.addStep("New Project", "New Project", iface.newProject)
lesson.addStep("Create repository", "Create repository",
               function = createExampleRepo)
lesson.addStep("Open GeoGig navigator", "Open GeoGig navigator", lambda: _openNavigator(group = "Lesson repos"))
lesson.addStep("Visualize changes between versions", "repodiff.md", steptype=Step.MANUALSTEP)
lesson.addStep("Export changes between versions as layers", "difflayers.md", steptype=Step.MANUALSTEP)
lesson.addStep("Create local changes", "Create local changes", _exportAndEditLayer)
lesson.addStep("Visualize local changes", "localdiff.md", steptype=Step.MANUALSTEP)


