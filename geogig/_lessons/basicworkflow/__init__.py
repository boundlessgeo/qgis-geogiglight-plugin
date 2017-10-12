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
from lessons.utils import layerFromName

from geogig._lessons import GeoGigLesson, openTestProject, _openNavigator, createEmptyTestRepo
import geogig._lessons as ls
from geogig.tools.layers import hasLocalChanges


def checkVersions(n):
    log = ls._lastRepo.log()
    return len(log) == n

def checkEdited(layername):
    layer = layerFromName(layername)
    if layer:
        return len(hasLocalChanges(layer)) > 0
    else:
        return False

def unmodalWidget(objectName, repeatTimes=10, repeatInterval=500, step=0):
    """Look for a widget in the QGIS hierarchy to set it as
    not modal.
    If the widget is not found try agail after a "repeatInterval"
    and repeat no more that "repeatTimes"
    """

    if not objectName:
        return

    l = QgsApplication.instance().topLevelWidgets()

    for d in l:
        for dd in d.findChildren(QDialog):
            if dd.objectName() != objectName:
                continue

            dd.setWindowModality(False)
            return

    if repeatTimes == step:
        return

        print step
        # if here => not found
    QTimer.singleShot(repeatInterval,
                      lambda: unmodalWidget(objectName, repeatTimes, repeatInterval,
                                            step + 1))

lesson = GeoGigLesson("01. Basic GeoGig workflow")
lesson.addStep("Create empty repository", "Create empty repository",
               function = lambda: createEmptyTestRepo())
lesson.addStep("Open GeoGig navigator", "Open GeoGig navigator",
               lambda: _openNavigator())
lesson.addStep("Create new repository", "01_create_new_repository.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Import layer", "02_import_layer.md",
               prestep=lambda: unmodalWidget("CommitDialog"),
               endcheck=lambda: checkVersions(1),
               steptype=Step.MANUALSTEP)
lesson.addStep("Edit layer", "03_edit_layer.md",
               endcheck=lambda: checkEdited("Buildings"),
               steptype=Step.MANUALSTEP)
lesson.addStep("Check local changes", "04_check_local_changes.md",
               prestep=lambda: unmodalWidget("DiffViewerDialog", 300, 1000),
               steptype=Step.MANUALSTEP)
lesson.addStep("Sync layer with repository", "05_sync_layer.md",
               prestep=lambda: unmodalWidget("CommitDialog"),
               endcheck=lambda: checkVersions(2),
               steptype=Step.MANUALSTEP)