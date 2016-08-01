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


__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import sys
import sqlite3
import tests
import unittest
import shutil
from tests import _createTestRepo, REPOS_SERVER_URL
from geogig.tests.testwebapilib import webapiSuite
from sqlite3 import OperationalError
from geogig.tools.utils import tempFilename, loadLayerNoCrsDialog
from geogig.tools.gpkgsync import applyLayerChanges, getCommitId, checkoutLayer
from geogig.geogigwebapi import repository
from qgis.utils import iface
from geogig.gui.dialogs.navigatordialog import navigatorInstance
from qgis.core import *
from PyQt4 import QtCore
from geogig.tools import layertracking
from geogig.layeractions import updateInfoActions


try:
    from qgistester.utils import layerFromName
except:
    pass

def openTestProject(name):
    projectFile = os.path.join(os.path.dirname(__file__), "data", "layers", name + ".qgs")
    if projectFile != QgsProject.instance().fileName():
        iface.addProject(projectFile)

_repos = []
_repoEndpoints = {}
_availableRepoEndpoints = {}
_tracked = []

def backupConfiguration():
    global _repos
    global _repoEndpoints
    global _availableRepoEndpoints
    _repos = repository.repos
    _repoEndpoints = repository.repoEndpoints
    _availableRepoEndpoints = repository.availableRepoEndpoints
    _tracked = layertracking.tracked

def restoreConfiguration():
    global _repos
    global _tracked
    global _repoEndpoints
    global _availableRepoEndpoints
    repository.repoEndpoints = _repoEndpoints
    repository.availableRepoEndpoints = _availableRepoEndpoints
    repository.repos = _repos
    layertracking._tracked = _tracked

def _openNavigator(empty = False):
    print tests._lastRepo
    if empty:
        repository.repos = []
        repository.repoEndpoints = {}
        repository.availableRepoEndpoints = {}
    else:
        repository.repos = [tests._lastRepo]
        repository.availableRepoEndpoints = {"test repositories":REPOS_SERVER_URL}
        repository.repoEndpoints = {"test repositories":REPOS_SERVER_URL}
    action = navigatorInstance.toggleViewAction()
    if not action.isChecked():
        iface.addDockWidget(QtCore.Qt.RightDockWidgetArea, navigatorInstance)
    action.trigger()
    action.trigger()
    navigatorInstance.fillTree()
    navigatorInstance.updateCurrentRepo(None, None)
    navigatorInstance.checkButtons()


def _exportAndEditLayer():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeAttributeValue(features[0].id(), 1, 1000)
        layer.deleteFeatures([features[1].id()])
        feat = QgsFeature(layer.pendingFields())
        feat.setAttributes(["5", 5])
        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(123, 456)))
        layer.addFeatures([feat])

def _exportAndChangeToFirstVersion():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    log = tests._lastRepo.log()
    assert len(log) == 3
    commitid = log[-1].commitid
    applyLayerChanges(tests._lastRepo, layer, tests._lastRepo.HEAD, commitid)
    updateInfoActions(layer)
    layer.reload()
    layer.triggerRepaint()

def _exportAndAddFeatureToLayer():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    log = tests._lastRepo.log()
    assert len(log) == 3
    commitid = log[-1].commitid
    applyLayerChanges(tests._lastRepo, layer, tests._lastRepo.HEAD, commitid)
    updateInfoActions(layer)
    with edit(layer):
        feat = QgsFeature(layer.pendingFields())
        feat.setAttributes(["5", 5])
        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(123, 456)))
        layer.addFeatures([feat])
    layer.reload()
    layer.triggerRepaint()

def _exportAndCreateConflictWithNulls():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeGeometry(features[0].id(), QgsGeometry.fromPoint(QgsPoint(123, 456)))
        layer.changeAttributeValue(features[0].id(), 1, None)
    filename = tempFilename("gpkg")
    tests._lastRepo.checkoutlayer(filename, "points")
    layer2 = loadLayerNoCrsDialog(filename, "points2", "ogr")
    features2 = list(layer2.getFeatures())
    with edit(layer2):
        layer2.changeGeometry(features[0].id(), QgsGeometry.fromPoint(QgsPoint(124, 457)))
        layer2.changeAttributeValue(features2[0].id(), 1, None)
    _, _, conflicts, _ = tests._lastRepo.importgeopkg(layer2, "master", "message", "me", "me@mysite.com", True)

def _exportAndCreateConflict():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeAttributeValue(features[0].id(), 1, 1000)
    filename = tempFilename("gpkg")
    tests._lastRepo.checkoutlayer(filename, "points")
    layer2 = loadLayerNoCrsDialog(filename, "points2", "ogr")
    features2 = list(layer2.getFeatures())
    with edit(layer2):
        layer2.changeAttributeValue(features2[0].id(), 1, 1001)
    _, _, conflicts, _ = tests._lastRepo.importgeopkg(layer2, "master", "message", "me", "me@mysite.com", True)

def _exportAndCreateConflictWithRemoveAndModify():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    features = list(layer.getFeatures())
    with edit(layer):
        layer.deleteFeatures([features[0].id()])
    filename = tempFilename("gpkg")
    tests._lastRepo.checkoutlayer(filename, "points")
    layer2 = loadLayerNoCrsDialog(filename, "points2", "ogr")
    features2 = list(layer2.getFeatures())
    with edit(layer2):
        layer2.changeAttributeValue(features[0].id(), 1, 1000)
    _, _, conflicts, _ = tests._lastRepo.importgeopkg(layer2, "master", "message", "me", "me@mysite.com", True)


def _exportLayer():
    checkoutLayer(tests._lastRepo, "points", None)

def _selectLayer():
    layer = layerFromName("points")
    iface.setActiveLayer(layer)

def _checkLayerInProject():
    layer = layerFromName("points")
    assert layer is not None

def _checkLayerInRepo():
    assert "points" in tests._lastRepo.trees()

def _checkLayerHasUntrackedContextMenus():
    layer = layerFromName("points")
    actions = layer.geogigActions
    assert 1 == len(actions)
    assert "add" in actions[0].text().lower()

def _checkLayerHasTrackedContextMenus():
    layer = layerFromName("points")
    actions = layer.geogigActions
    assert 1 < len(actions)
    assert "remove" in actions[0].text().lower()

def _checkContextMenuInfo(text):
    layer = layerFromName("points")
    actions = layer.infoActions
    assert 2 == len(actions)
    assert text in actions[0].text().lower()

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
    test.addStep("Open navigator", lambda:  _openNavigator(True))
    test.addStep("Right click on the layer and try to add it to a repository.\n"
                 "Verify that it shows a warning because there are no repositories defined.")
    tests.append(test)

    test = GeoGigTest("Add layer to repository")
    test.addStep("Open test data", lambda: openTestProject("points"))
    test.addStep("Create repository", lambda: _createTestRepo("empty", True))
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Add layer 'points' to the 'empty' repository using navigator button 'Add layer")
    test.addStep("Check layer has been added to repo", _checkLayerInRepo)
    tests.append(test)

    test = GeoGigTest("Check repository log")
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Create repository", lambda: _createTestRepo("simple"))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Check log is correctly displayed in the history tab of the GeoGig navigator")
    tests.append(test)

    test = GeoGigTest("Open repository layers in QGIS")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("New project", iface.newProject)
    test.addStep("Add layer from the 'simple' repository into QGIS")
    test.addStep("Check layer has been added to project", _checkLayerInProject)
    tests.append(test)

    test = Test("Sync with only local changes")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Export and edit repo layer", _exportAndEditLayer)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Sync with master branch'")
    test.addStep("Check in repo history that a new version has been created")
    tests.append(test)

    test = Test("Sync to new branch")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Export and edit repo layer", _exportAndEditLayer)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Type 'newbranch' in the branch box and sync'")
    test.addStep("Check in repo history that a branch called 'newbranch' has been created with the changes")
    tests.append(test)

    test = Test("Sync with only upstream changes")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export repo layer", _exportAndChangeToFirstVersion)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Sync with master branch'")
    test.addStep("Check context menu info", lambda: _checkContextMenuInfo("third"))
    test.addStep("Check that layer has been modified")
    tests.append(test)

    test = Test("Sync with no changes at all")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export repo layer", _exportLayer)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Sync with master branch'")
    test.addStep("Check context menu info", lambda: _checkContextMenuInfo("third"))
    test.addStep("Check that no changes are made in the layer or the history")
    tests.append(test)

    test = Test("Sync with conflicts")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export and edit repo layer", _exportAndCreateConflict)
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Sync with master branch. Solve conflict'")
    test.addStep("Check that new version has been created in the repo history")
    tests.append(test)

    test = Test("Sync with conflict, with remove and modify")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export and edit repo layer", _exportAndCreateConflictWithRemoveAndModify)
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Sync with master branch. Solve conflict'")
    test.addStep("Check that new version has been created in the repo history")
    tests.append(test)

    test = Test("Sync with conflicts and null values")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export and edit repo layer", _exportAndCreateConflictWithNulls)
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Sync with master branch. Solve conflict with a new feature'")
    test.addStep("Check that new version has been created in the repo history")
    tests.append(test)

    test = Test("Sync with conflicts, without resolving them")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export and edit repo layer", _exportAndCreateConflict)
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Sync with master branch. Exit conflict dialog without solving'")
    test.addStep("Check that no new version has been created in the repo history, and the layer hasn't been modified")
    tests.append(test)

    test = Test("Sync with both local and upstream changes, without conflict")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Export and edit repo layer", _exportAndAddFeatureToLayer)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch. Sync with master branch'")
    test.addStep("Check that layer has been modified and a new version has been created in the repo history")
    tests.append(test)

    test = Test("Check diff viewer")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple"))
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Click on latest version and select 'View changes'. Check that diff viewer works correctly")
    tests.append(test)

    test = Test("Check local diff viewer")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export and edit repo layer", _exportAndEditLayer)
    test.addStep("Right click on 'points' layer and select 'GeoGig/view local changes'. Check that diff viewer works correctly")
    tests.append(test)

    test = GeoGigTest("Add layer to repository from context menu")
    test.addStep("Open test data", lambda: openTestProject("points"))
    test.addStep("Create repository", lambda: _createTestRepo("empty", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Add layer using context menu")
    test.addStep("Check layer has been added to repo", _checkLayerInRepo)
    test.addStep("Check layer context menus", _checkLayerHasTrackedContextMenus)
    tests.append(test)

    test = GeoGigTest("Show version characteristics")
    test.addStep("Create repository", lambda: _createTestRepo("simple"))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Right click on repo's last commit and select 'Show detailed description'\nVerify description is correctly shown")
    tests.append(test)

    test = GeoGigTest("Create new branch")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Create new branch at master branch's last commit and verify it is added to history tree")
    tests.append(test)

    test = GeoGigTest("Delete branch")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Delete 'mybranch' and verify the versions tree is updated")
    tests.append(test)

    test = GeoGigTest("Create new tag")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Create new tag at current branch's last commit and verify it is added to history tree")
    tests.append(test)

    test = GeoGigTest("Delete tag")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Delete 'mytag' tag and verify the versions tree is updated")
    tests.append(test)

    test = Test("Check map tools viewer")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export layer", _exportLayer)
    test.addStep("Select the 'GeoGig/Info Tool' menu")
    test.addStep("Select layer", _selectLayer)
    test.addStep("Click on a feature and select 'View authorship'. Verify it shows authorship correctly", isVerifyStep = True)
    test.addStep("Click on a feature and select 'View versions'. Verify it shows feature versions correctly")
    tests.append(test)

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

    def testCanCleanAuditTableAfterEdit(self):
        src = os.path.join(os.path.dirname(__file__), "data", "layers", "points.gpkg")
        dest = tempFilename("gpkg")
        shutil.copy(src, dest)
        layer = loadLayerNoCrsDialog(dest, "points", "ogr")
        self.assertTrue(layer.isValid())
        features = list(layer.getFeatures())
        geom = QgsGeometry.fromPoint(QgsPoint(12,12))
        self.assertTrue(layer.startEditing())
        self.assertTrue(layer.changeGeometry(features[0].id(), geom))
        self.assertTrue(layer.commitChanges())
        con = sqlite3.connect(dest)
        cursor = con.cursor()
        cursor.execute("DELETE FROM points_audit;")
        self.assertRaises(OperationalError, con.commit)
        con.close()
        layer.reload()
        con = sqlite3.connect(dest)
        cursor = con.cursor()
        cursor.execute("DELETE FROM points_audit;")
        con.commit()

def pluginSuite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(PluginTests, 'test'))
    return suite


def unitTests():
    _tests = []
    _tests.extend(webapiSuite())
    _tests.extend(pluginSuite())
    return _tests


def run_tests():
    unittest.TextTestRunner(verbosity=3, stream=sys.stdout).run(pluginSuite())
