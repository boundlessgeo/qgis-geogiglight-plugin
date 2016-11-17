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
import ogr
import sys
import sqlite3
from geogig import tests
import unittest
import shutil
from geogig.tests import _createTestRepo, conf
from geogig.tests.testwebapilib import webapiSuite
from sqlite3 import OperationalError
from geogig.tools.utils import tempFilename, loadLayerNoCrsDialog, tempSubfolder
from geogig.tools.gpkgsync import applyLayerChanges, getCommitId, checkoutLayer
from geogig.geogigwebapi import repository
from qgis.utils import iface
from geogig.gui.dialogs.navigatordialog import navigatorInstance
from qgis.core import *
from PyQt4 import QtCore
from geogig.tools import layertracking
from geogig.layeractions import updateInfoActions
from geogig.tests.testgpkg import GeoPackageEditTests

try:
    from qgistester.utils import layerFromName
except:
    pass

def openTestProject(name):
    orgPath = os.path.join(os.path.dirname(__file__), "data", "projects", name)
    destPath = tempSubfolder()
    shutil.copytree(orgPath, destPath)
    projectFile = os.path.join(destPath, name + ".qgs")
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

def _openNavigator(empty = False, group = "test repositories"):
    if empty:
        repository.repos = []
        repository.repoEndpoints = {}
        repository.availableRepoEndpoints = {}
    else:
        repository.repos = [tests._lastRepo]
        repository.availableRepoEndpoints = {group:conf['REPOS_SERVER_URL']}
        repository.repoEndpoints = {group:conf['REPOS_SERVER_URL']}
    action = navigatorInstance.toggleViewAction()
    if not action.isChecked():
        iface.addDockWidget(QtCore.Qt.RightDockWidgetArea, navigatorInstance)
    action.trigger()
    action.trigger()
    navigatorInstance.fillTree()
    navigatorInstance.updateCurrentRepo(None)
    navigatorInstance.checkButtons()


def _exportAndEditLayer():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    idx = layer.dataProvider().fieldNameIndex("n")
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeAttributeValue(features[0].id(), idx, 1000)
        layer.deleteFeatures([features[1].id()])
        feat = QgsFeature(layer.pendingFields())
        feat.setAttributes(["5", 5])
        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(123, 456)))
        layer.addFeatures([feat])
    return layer

def _addNewCommit():
    layer = _exportAndEditLayer()
    tests._lastRepo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)

def _exportAndChangeToFirstVersion():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    log = tests._lastRepo.log()
    assert len(log) == 3
    commitid = log[-1].commitid
    applyLayerChanges(tests._lastRepo, layer, tests._lastRepo.HEAD, commitid)
    updateInfoActions(layer)
    layer.reload()
    layer.triggerRepaint()

def _exportChangetoFirstVersionAndEditLayer():
    log = tests._lastRepo.log()
    assert len(log) == 3
    commitid = log[-1].commitid
    layer = checkoutLayer(tests._lastRepo, "points", None, commitid)
    idx = layer.dataProvider().fieldNameIndex("n")
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeAttributeValue(features[0].id(), idx, 1000)
        feat = QgsFeature(layer.pendingFields())
        feat.setAttributes(["5", 5])
        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(123, 456)))
        layer.addFeatures([feat])

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
    idx = layer.dataProvider().fieldNameIndex("n")
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeGeometry(features[0].id(), QgsGeometry.fromPoint(QgsPoint(123, 456)))
        layer.changeAttributeValue(features[0].id(), idx, None)
    filename = tempFilename("gpkg")
    tests._lastRepo.checkoutlayer(filename, "points")
    layer2 = loadLayerNoCrsDialog(filename, "points2", "ogr")
    features2 = list(layer2.getFeatures())
    with edit(layer2):
        layer2.changeGeometry(features[0].id(), QgsGeometry.fromPoint(QgsPoint(124, 457)))
        layer2.changeAttributeValue(features2[0].id(), idx, None)
    _, _, conflicts, _ = tests._lastRepo.importgeopkg(layer2, "master", "message", "me", "me@mysite.com", True)

def _exportAndCreateConflict():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    idx = layer.dataProvider().fieldNameIndex("n")
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeAttributeValue(features[0].id(), idx, 1000)
    filename = tempFilename("gpkg")
    tests._lastRepo.checkoutlayer(filename, "points")
    layer2 = loadLayerNoCrsDialog(filename, "points2", "ogr")
    features2 = list(layer2.getFeatures())
    with edit(layer2):
        layer2.changeAttributeValue(features2[0].id(), idx, 1001)
    _, _, conflicts, _ = tests._lastRepo.importgeopkg(layer2, "master", "message", "me", "me@mysite.com", True)

def _exportAndCreateConflictWithRemoveAndModify():
    layer = checkoutLayer(tests._lastRepo, "points", None)
    idx = layer.dataProvider().fieldNameIndex("n")
    features = list(layer.getFeatures())
    with edit(layer):
        layer.deleteFeatures([features[0].id()])
    filename = tempFilename("gpkg")
    tests._lastRepo.checkoutlayer(filename, "points")
    layer2 = loadLayerNoCrsDialog(filename, "points2", "ogr")
    features2 = list(layer2.getFeatures())
    with edit(layer2):
        layer2.changeAttributeValue(features[0].id(), idx, 1000)
    _, _, conflicts, _ = tests._lastRepo.importgeopkg(layer2, "master", "message", "me", "me@mysite.com", True)

def _deleteLayerFromBranch():
    tests._lastRepo.removetree("points", "me", "me@mysite.com", "mybranch")

def _createMergeScenario(layername = "points"):
    filename = tempFilename("gpkg")
    tests._lastRepo.checkoutlayer(filename, layername)
    layer = loadLayerNoCrsDialog(filename, layername, "ogr")
    idx = layer.dataProvider().fieldNameIndex("n")
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeAttributeValue(features[0].id(), idx, 1000)
    tests._lastRepo.importgeopkg(layer, "mybranch", "changed_%s_1" % layername, "me", "me@mysite.com", True)

def _doConflictImport(layername = "points"):
    filename = tempFilename("gpkg")
    tests._lastRepo.checkoutlayer(filename, layername)
    layer = loadLayerNoCrsDialog(filename, layername, "ogr")
    idx = layer.dataProvider().fieldNameIndex("n")
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeAttributeValue(features[0].id(), idx, 1001)
    tests._lastRepo.importgeopkg(layer, "master", "changed_%s_2" % layername, "me", "me@mysite.com", True)

def _createMergeConflict():
    _createMergeScenario("points")
    _doConflictImport("points")

def _createMergeConflictInSeveralLayers():
    _createMergeScenario("points")
    _createMergeScenario("lines")
    _doConflictImport("points")
    _doConflictImport("lines")

_localRepo = None
_remoteRepo = None
def _createConflictedPullScenario():
    global _localRepo
    _localRepo = _createTestRepo("simple", True)
    global _remoteRepo
    _remoteRepo = _createTestRepo("simple", True)
    filename = tempFilename("gpkg")
    _localRepo.checkoutlayer(filename, "points")
    layer = loadLayerNoCrsDialog(filename, "points", "ogr")
    features = list(layer.getFeatures())
    idx = layer.dataProvider().fieldNameIndex("n")
    with edit(layer):
        layer.changeAttributeValue(features[0].id(), idx, 1000)
    filename2 = tempFilename("gpkg")
    _remoteRepo.checkoutlayer(filename2, "points")
    layer2 = loadLayerNoCrsDialog(filename2, "points2", "ogr")
    features2 = list(layer2.getFeatures())
    with edit(layer2):
        layer2.changeAttributeValue(features2[0].id(), idx, 1001)
    _localRepo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
    _remoteRepo.importgeopkg(layer2, "master", "message", "me", "me@mysite.com", True)
    _localRepo.addremote("myremote", _remoteRepo.url)
    _remoteRepo.addremote("myremote", _localRepo.url)


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

def settings():
    return {"REPOS_SERVER_URL": "http://localhost:8182/",
            "REPOS_FOLDER": os.path.expanduser("~/geogig/server")}

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


    test = GeoGigTest("Connect to endpoint")
    test.addStep("Open navigator", lambda:  _openNavigator(True))
    test.addStep("Add a new geogig server at the repositories server url")
    test.addStep("Verify the endpoint item has been correctly added (might contain child repos or not)")
    tests.append(test)

    test = GeoGigTest("Connect to wrong endpoint")
    test.addStep("Open navigator", lambda:  _openNavigator(True))
    test.addStep("Add a new geogig server at 'http://wrong.url'")
    test.addStep("Verify a warning indicating that the url is wrong is shown. Verify endpoint item is added to tree and grayed out.")
    tests.append(test)

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
    test.addStep("Add layer from the 'simple' repository into QGIS. Use the links in the repository description panel")
    test.addStep("Check layer has been added to project", _checkLayerInProject)
    tests.append(test)

    test = GeoGigTest("Open repository layers in QGIS from tree")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("New project", iface.newProject)
    test.addStep("Add layer from the 'simple' repository into QGIS. Use the links in the layer items of the repository tree")
    test.addStep("Check layer has been added to project", _checkLayerInProject)
    tests.append(test)

    test = GeoGigTest("Open already exported layers in QGIS from tree")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export repo layer", _exportAndChangeToFirstVersion)
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Add layer from the 'simple' repository into QGIS. Use the links in the layer items of the repository tree (which should be in orange color). "
                 "Verify that is asks you for confirmation. Select 'Use branch version'", isVerifyStep = True)
    test.addStep("Check context menu info", lambda: _checkContextMenuInfo("third"))
    tests.append(test)

    test = GeoGigTest("Open already exported layers in QGIS when there are local changes")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export repo layer", _exportAndEditLayer)
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Add layer from the 'simple' repository into QGIS. Use the links in the layer items of the repository tree. "
                 "Verify it show a message in the message bar saying that the layer was already loaded", isVerifyStep = True)
    tests.append(test)

    test = GeoGigTest("Open already exported layers in QGIS to an older version, with local changes")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export repo layer", _exportChangetoFirstVersionAndEditLayer)
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Add layer from the 'simple' repository into QGIS. Use the links in the layer items of the repository tree (which should be in orange color).  "
                 "Verify that is asks you for confirmation. Select 'Use branch version'. Check it is not permitted due to local changes in the layer",
                 isVerifyStep = True)
    tests.append(test)

    test = GeoGigTest("Change layer version")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export repo layer", _exportAndChangeToFirstVersion)
    test.addStep("Change version to 'third' using the 'Change version' menu entry in the layer context menu")
    test.addStep("Check layer has been added to project", _checkLayerInProject)
    test.addStep("Check context menu info", lambda: _checkContextMenuInfo("third"))
    tests.append(test)

    test = GeoGigTest("Change layer version when there are local changes")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export repo layer", _exportAndEditLayer)
    test.addStep("Try to change version using the 'Change version' menu entry in the layer context menu."
                 "Check it is not permitted due to local changes in the layer", isVerifyStep = True)
    tests.append(test)

    test = Test("Sync with only local changes")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Export and edit repo layer", _exportAndEditLayer)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Sync with master branch'")
    test.addStep("Check in repo history that a new version has been created")
    tests.append(test)

    test = Test("Sync to non-master branch")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Export and edit repo layer", _exportAndEditLayer)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch'. Select 'mybranch' in the branch box and sync'")
    test.addStep("Check in repo history that the 'mybranch' branch has been updated with the changes")
    tests.append(test)


    test = Test("Sync with only upstream changes")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator",  _openNavigator)
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

    test = Test("Merge without conflicts")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Create merge conflict", _createMergeScenario)
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Merge 'mybranch' branch into 'master' branch")
    test.addStep("Check that the merge was correctly completed")
    tests.append(test)

    test = Test("Merge with conflicts")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Create merge conflict", _createMergeConflict)
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Merge 'mybranch' branch into 'master' branch. Solve conflict")
    test.addStep("Check that the merge was correctly completed")
    tests.append(test)

    test = Test("Merge with conflicts in several layers")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("severallayers", True))
    test.addStep("Create merge conflict", _createMergeConflictInSeveralLayers)
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Merge 'mybranch' branch into 'master' branch. Solve conflict")
    test.addStep("Check that the merge was correctly completed")
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

    test = Test("Sync with layer only in one branch")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Export repo layer", _exportLayer)
    test.addStep("Delete layer from branch", _deleteLayerFromBranch)
    test.addStep("Right click on 'points' layer and select 'GeoGig/Sync with repository branch. Verify that only 'master'branch is available")
    tests.append(test)

    test = Test("Pull with conflicts")
    test.addStep("New project", iface.newProject)
    test.addStep("Prepare test", _createConflictedPullScenario)
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Pull from remote and solve conflicts. Verify it solves them correctly")
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

    test = Test("Check export diff layer")
    test.addStep("New project", iface.newProject)
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Add commit", _addNewCommit)
    test.addStep("Open navigator",  _openNavigator)
    test.addStep("Click on latest version in master branch and select 'Export diff as layer'. Check that layer is exported correctly")
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
    test.addStep("Verify that 'master' branch cannot be deleted from history tree", isVerifyStep = True)
    test.addStep("Delete 'mybranch' using repo history panel and verify the versions tree is updated")
    tests.append(test)

    test = GeoGigTest("Delete branch in repositories tree")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Verify that 'master' branch cannot be deleted from repositories tree", isVerifyStep = True)
    test.addStep("Delete 'mybranch' from the versions tree and verify the repositories tree is updated")
    tests.append(test)

    test = GeoGigTest("Delete layer in repositories tree, in 'master' branch")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Delete 'points' layer in 'master' branch in repositories tree, and verify the repositories tree is updated correctly")
    tests.append(test)

    test = GeoGigTest("Delete layer in tree, in non-master branch")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Delete 'points' layer in 'mybranch' branch in repositories tree, and verify the versions tree is updated correctly")
    tests.append(test)

    test = GeoGigTest("Delete layer in tree, in all branches")
    test.addStep("Create repository", lambda: _createTestRepo("simple", True))
    test.addStep("Export repo layer", _exportLayer)
    test.addStep("Open navigator", _openNavigator)
    test.addStep("Delete 'points' layer in 'mybranch' branch in repositories tree, and verify the versions tree is updated correctly."
                 "Verify that the context menu of the layer still shows the tracked layer menus")
    test.addStep("Delete 'points' layer in 'master' branch in repositories tree, and verify the versions tree is updated correctly."
                 "Verify that the context menu of the layer shows the layer as untracked")
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
