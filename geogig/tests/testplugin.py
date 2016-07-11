# -*- coding: utf-8 -*-

"""
***************************************************************************
    testerplugin.py
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
from PyQt4 import QtCore



__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from geogig.tests.testwebapilib import webapiSuite
import os
from tests import _createTestRepo
import tests
import unittest
from geogig.tools.utils import tempFilename, loadLayerNoCrsDialog
from geogig.tools.gpkgsync import applyLayerChanges, getCommitId
from geogig.geogigwebapi import repository
from qgis.utils import iface
from gui.dialogs.navigatordialog import navigatorInstance
from qgis.core import *


try:
    from qgistester.utils import layerFromName
except:
    pass

def openTestProject(name):
    projectFile = os.path.join(os.path.dirname(__file__), "data", "layers", name + ".qgs")
    if projectFile != QgsProject.instance().fileName():
        iface.addProject(projectFile)


_repos = []
def backupConfiguration():
    global _repos
    _repos = repository.repos

def restoreConfiguration():
    global _repos
    repository.repos = _repos

def _openNavigator(empty = False):
    print tests._lastRepo
    if empty:
        repository.repos = []
    else:
        repository.repos = [tests._lastRepo]
    action = navigatorInstance.toggleViewAction()
    if not action.isChecked():
        iface.addDockWidget(QtCore.Qt.RightDockWidgetArea, navigatorInstance)
    action.trigger()
    navigatorInstance.fillTree()
    navigatorInstance.updateCurrentRepo(None, None)
    navigatorInstance.checkButtons()


def _exportAndEditLayer():
    filename = tempFilename("gpkg")
    tests._lastRepo.checkoutlayer(filename, "points")
    layer = loadLayerNoCrsDialog(filename, "points", "ogr")
    assert layer.isValid()
    feat = QgsFeature(layer.pendingFields())
    feat.setAttributes(["5", 5])
    layer.startEditing()
    feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(123, 456)))
    layer.addFeatures([feat])
    layer.commitChanges()
    QgsMapLayerRegistry.instance().addMapLayers([layer])

def _checkLayerInProject():
    layer = layerFromName("points")
    assert layer is not None

def _checkFeatureAddedInRepo():
    pass

def _checkLayerInRepo():
    assert "lines" in tests._lastRepo.trees()

def _checkLayerHasUntrackedContextMenus():
    layer = layerFromName("points")
    actions = layer.geogigActions
    assert 1 == len(actions)
    assert "add" in actions[0].text().lower()

def _checkLayerHasTrackedContextMenus():
    layer = layerFromName("points")
    actions = layer.geogigActions
    assert 2 == len(actions)
    assert "remove" in actions[0].text().lower()

def _removeRepos():
    repository.repos = []

#TESTS

def functionalTests():
    try:
        from qgistester.test import Test
        class GeoGigTest(Test):
            def __init__(self, name):
                Test.__init__(self, name)
                self.addStep("Preparing test", backupConfiguration)
                self.setCleanup(restoreConfiguration)
    except:
        return []

    tests = []


    test = GeoGigTest("Add layer without repo")
    test.addStep("Open test data", lambda: openTestProject("points"))
    test.addStep("Remove repos", _removeRepos)
    test.addStep("Right click on the layer and try to add it to a repository.\n"
                 "Verify that it shows a warning because there are no repositories defined.")
    tests.append(test)

    test = GeoGigTest("Add layer to repository")
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Open test data", lambda: openTestProject("points"))
    test.addStep("Create repository", lambda: _createTestRepo("empty", True))
    test.addStep("Open navigator", lambda: _openNavigator())
    test.addStep("Add layer 'points' to the 'empty' repository")
    test.addStep("Check layer has been added to repo", _checkLayerInRepo)
    tests.append(test)

    test = GeoGigTest("Check repository log")
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Create repository", lambda: _createTestRepo("simple"))
    test.addStep("Open navigator", lambda: _openNavigator())
    test.addStep("Check log is correctly displayed in the history tab of the GeoGig navigator")
    tests.append(test)

    test = GeoGigTest("Open repository layers in QGIS")
    test.addStep("Create repository", lambda: _createTestRepo("simple"))
    test.addStep("Open navigator", lambda: _openNavigator())
    test.addStep("New project", iface.newProject)
    test.addStep("Add layer from the 'simple' repository into QGIS")
    test.addStep("Check layer has been added to project", _checkLayerInProject)
    tests.append(test)

    test = Test("Add feature and create new version")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple"))
    test.addStep("Open navigator", lambda: _openNavigator())
    test.addStep("Export and edit repo layer", _exportAndEditLayer)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch. Sync with master branch'")
    test.addStep("Check in repo history that a new version has been created")
    tests.append(test)

    test = GeoGigTest("Add layer to repository from context menu")
    test.addStep("Open test data", lambda: openTestProject("points"))
    test.addStep("Create repository", lambda: _createTestRepo("empty"), True)
    test.addStep("Open navigator", lambda: _openNavigator())
    test.addStep("Add layer using context menu")
    test.addStep("Check layer has been added to repo", _checkLayerInRepo)
    test.addStep("Check layer context menus", _checkLayerHasTrackedContextMenus)
    tests.append(test)

    test = GeoGigTest("Show version characteristics")
    test.addStep("Create repository", lambda: _createTestRepo("simple"))
    test.addStep("Open navigator", lambda: _openNavigator())
    test.addStep("Right click on repo's last commit and select 'Show detailed description'\nVerify description is correctly shown")
    tests.append(test)

    test = GeoGigTest("Create new branch")
    test.addStep("Create repository", lambda: _createTestRepo("empty"), True)
    test.addStep("Open navigator", lambda: _openNavigator())
    test.addStep("Create new branch at current branch's HEAD and verify it is added to history tree")
    tests.append(test)

    test = GeoGigTest("Delete branch")
    test.addStep("Create repository", lambda: _createTestRepo("simple"))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Delete 'mybranch' and verify the versions tree is updated")
    tests.append(test)

    return []
    return tests

class PluginTests(unittest.TestCase):

    def setUp(self):
        pass

    def testChangeVersion(self):
        repo = _createTestRepo("simple")
        log = repo.log()
        self.assertEqual(3, len(log))
        commitid = log[-1].commitid
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(layer.isValid())
        features = list(layer.getFeatures())
        self.assertEqual(1, len(features))
        applyLayerChanges(repo, layer, commitid, repo.HEAD)
        layer.reload()
        self.assertTrue(layer.isValid())
        features = list(layer.getFeatures())
        self.assertEqual(2, len(features))
        self.assertEqual(getCommitId(layer), log[0].commitid)

def pluginSuite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(PluginTests, 'test'))
    return suite


def unitTests():
    _tests = []
    _tests.extend(webapiSuite())
    _tests.extend(pluginSuite())
    return _tests
