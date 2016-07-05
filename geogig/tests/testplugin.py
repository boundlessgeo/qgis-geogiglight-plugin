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

from geogig.tests.testwebapilib import webapiSuite




def openTestProject(name):
    projectFile = os.path.join(os.path.dirname(__file__), "data", "layers", name + ".qgs")
    if projectFile != QgsProject.instance().fileName():
        qgis.utils.iface.addProject(projectFile)

#TESTS

def functionalTests():
    try:
        from qgistester.test import Test
    except:
        return []

    tests = []
#===============================================================================
#     test = Test("Create new repository")
#     test.addStep("Set repos folder", lambda: _setReposFolder("new"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Create new repo and verify it is correctly added to the list")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Add layer without repo")
#     test.addStep("Set repos folder", lambda: _setReposFolder("new"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Open test data", lambda: openTestProject("points"))
#     test.addStep("Right click on the layer and try to add it to a repository.\n"
#                  "Verify that it shows a warning because there are no repositories defined.")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Create new repository with existing name")
#     test.addStep("Set repos folder", lambda: _setReposFolder("emptyrepo"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Create new repo named 'testrepo' and verify it cannot be created")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Change repository title")
#     test.addStep("Set repos folder", lambda: _setReposFolder("emptyrepo"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Edit repository title and check it is updated in the repo summary")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Delete repository")
#     test.addStep("Set repos folder", lambda: _setReposFolder("emptyrepo"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Delete repository and check it is removed from the list")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Add layer to repository")
#     test.addStep("Set repos folder", lambda: _setReposFolder("emptyrepo"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Open test data", lambda: openTestProject("points"))
#     test.addStep("Add layer 'points' to the 'testrepo' repository")
#     test.addStep("Check layer has been added to repo", _checkLayerInRepo)
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Add layer with unconfigured user")
#     test.addStep("Set repos folder", lambda: _setReposFolder("emptyrepo"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Open test data", lambda: openTestProject("points"))
#     test.addStep("Remove user configuration", _removeUserConfig)
#     test.addStep("Add layer 'points' to the 'testrepo' repository")
#     test.addStep("Check layer has been added to repo", _checkLayerInRepo)
#     test.setCleanup(_restoreUserConfig)
#     tests.append(test)
#
#     test = Test("Open repository layers in QGIS")
#     test.addStep("Set repos folder", lambda: _setReposFolder("pointsrepo"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Select the 'testrepo' repository and click on 'Open repository in QGIS'")
#     test.addStep("Check layer has been added to project", _checkLayerInProject)
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Update repository when there are no changes")
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Set repos folder", lambda: _setReposFolder("pointsrepo"))
#     test.addStep("Export repo layers", lambda:_exportRepoLayers("repo"))
#     test.addStep("Right click on 'points' layer and select 'GeoGig/Update repository with this version'\n"
#                  "Verify that the plugin shows that there are no changes to add")
#     test.setCleanup(_cleanRepoClone)
#     tests.append(test)
#
#     test = Test("Modify feature and create new version")
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Set repos folder", lambda: _setReposFolder("pointsrepo"))
#     test.addStep("Export repo layers", lambda:_exportRepoLayers("repo"))
#     test.addStep("Edit layer", _modifyFeature)
#     test.addStep("Right click on 'points' layer and select 'GeoGig/Update repository with this version'")
#     test.addStep("Check layer has been updated", _checkFeatureModifiedInRepo)
#     test.setCleanup(_cleanRepoClone)
#     tests.append(test)
#
#     test = Test("Add feature and create new version")
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Set repos folder", lambda: _setReposFolder("pointsrepo"))
#     test.addStep("Export repo layers", lambda:_exportRepoLayers("repo"))
#     test.addStep("Edit layer", _addFeature)
#     test.addStep("Right click on 'points' layer and select 'GeoGig/Update repository with this version'")
#     test.addStep("Check layer has been updated", _checkFeatureAddedInRepo)
#     test.setCleanup(_cleanRepoClone)
#     tests.append(test)
#
#     test = Test("Add layer to repository from context menu")
#     test.addStep("Open test data", lambda: openTestProject("points"))
#     test.addStep("Set repos folder", lambda: _setReposFolder("emptyrepo"))
#     test.addStep("Add layer using context menu")
#     test.addStep("Check layer has been added to repo", _checkLayerInRepo)
#     test.addStep("Check layer context menus", _checkLayerHasTrackedContextMenus)
#     test.setCleanup(_cleanRepoClone)
#     tests.append(test)
#
#     test = Test("Remove layer from repository")
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Set repos folder", lambda: _setReposFolder("pointsrepo"))
#     test.addStep("Export repo layers", lambda:_exportRepoLayers("repo"))
#     test.addStep("Right click on 'points' layer and select 'GeoGig/Remove layer from repository'")
#     test.addStep("Check layer has been correctly deleted", _checkLayerNotInRepo)
#     test.addStep("Check layer context menus", _checkLayerHasUntrackedContextMenus)
#     test.setCleanup(_cleanRepoClone)
#     tests.append(test)
#
#     test = Test("Show version characteristics")
#     test.addStep("Set repos folder", lambda: _setReposFolder("pointsrepo"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Right click on repo's only commit and select 'Show detailed description'\nVerify description is correctly shown")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Create new branch")
#     test.addStep("Set repos folder", lambda: _setReposFolder("pointsrepo"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Create new branch at current branch's HEAD and verify it is added to history tree")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Switch branch")
#     test.addStep("Set repos folder", lambda: _setReposFolder("twobranches"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Export repo layers", lambda:_exportRepoLayers("repo"))
#     test.addStep("Switch to 'newbranch' branch and verify the map is updated")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Merge branch")
#     test.addStep("Set repos folder", lambda: _setReposFolder("twobranches"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Export repo layers", lambda:_exportRepoLayers("repo"))
#     test.addStep("Merge 'newbranch' into 'master' and verify the map and versions tree are updated")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Merge conflicted  branch")
#     test.addStep("Set repos folder", lambda: _setReposFolder("conflicted"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Export repo layers", lambda:_exportRepoLayers("repo"))
#     test.addStep("Merge 'conflicted' into 'master' and solve the conflicts.\n"
#                  "Verify the merge is correctly finished and the tree and map are updated")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Merge conflicted  branch and abort")
#     test.addStep("Set repos folder", lambda: _setReposFolder("conflicted"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Export repo layers", lambda:_exportRepoLayers("repo"))
#     test.addStep("Merge 'conflicted' into 'master' and abort.\n"
#                  "Verify the merge is correctly aborted.")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Delete branch")
#     test.addStep("Set repos folder", lambda: _setReposFolder("twobranches"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Delete 'newbranch' and verify the versions tree is updated")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Pull from remote")
#     test.addStep("Set repos folder", lambda: _setReposFolder("remote"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Add remote", _addRemote)
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Export repo layers", lambda:_exportRepoLayers("local"))
#     test.addStep("Sync local repo pulling from remote.\n"
#                  "Verify the repo and the map are correctly updated.")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#
#     test = Test("Pull from remote with conflicts")
#     test.addStep("Set repos folder", lambda: _setReposFolder("conflictedremote"))
#     test.addStep("Open navigator", _openNavigator)
#     test.addStep("Add remote", _addRemote)
#     test.addStep("New project", qgis.utils.iface.newProject)
#     test.addStep("Sync local repo pulling from remote.\n"
#                  "Verify the conflict is detected.")
#     test.setCleanup(_removeTempRepoFolder)
#     tests.append(test)
#===============================================================================

    return tests

def unitTests():
    _tests = []
    _tests.extend(webapiSuite())
    return _tests
