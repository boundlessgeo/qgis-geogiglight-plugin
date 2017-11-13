# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
import os
import traceback
import requests
import time
from distutils.dir_util import copy_tree

from geogig.extlibs.qgiscommons2.files import tempFolderInTempFolder, tempFilename
from geogig.extlibs.qgiscommons2.layers import loadLayerNoCrsDialog

from qgis.core import *
from qgis.utils import iface
from qgis.PyQt.QtCore import Qt

from geogig.geogigwebapi.repository import createRepoAtUrl, GeoGigException, Repository, readRepos
from geogig.geogigwebapi import repository
from geogig.tools import layertracking
from geogig.gui.dialogs.navigatordialog import navigatorInstance
from geogig.tools.gpkgsync import checkoutLayer

_lastRepo = None

_repos = []
_repoEndpoints = {}
_availableRepoEndpoints = {}
_tracked = []

REPOS_SERVER_URL = "http://localhost:8182/"

def cleanup():
    global _lastRepo
    if _lastRepo is not None:
        _lastRepo.delete()
    readRepos()
    navigatorInstance.updateNavigator()

def _openNavigator(empty = False, group = "Lesson repos"):
    if empty:
        repository.repos = []
        repository.repoEndpoints = {}
        repository.availableRepoEndpoints = {}
    else:
        repository.repos = [_lastRepo] if _lastRepo else []
        repository.availableRepoEndpoints = {group:REPOS_SERVER_URL}
        repository.repoEndpoints = {group:REPOS_SERVER_URL}
    action = navigatorInstance.toggleViewAction()
    if not action.isChecked():
        iface.addDockWidget(Qt.RightDockWidgetArea, navigatorInstance)
    action.trigger()
    action.trigger()
    navigatorInstance.updateNavigator()
    navigatorInstance.fillTree()



def openTestProject(name):
    orgPath = os.path.join(os.path.dirname(__file__), "data", "projects", name)
    destPath = tempFolderInTempFolder()
    copy_tree(orgPath, destPath)
    projectFile = os.path.join(destPath, name + ".qgs")
    if projectFile != QgsProject.instance().fileName():
        iface.addProject(projectFile)

def createEmptyTestRepo(modifiesRepo = True, group=None, name=None):
    repo = createRepoAtUrl(REPOS_SERVER_URL, group or "Lesson repos", name or "empty_%s" %  str(time.time()))
    global _lastRepo
    _lastRepo = repo
    return repo

def _layerPath(name):
    return os.path.join(os.path.dirname(__file__), "data", "layers", name + ".gpkg")

def _importLayerToRepo(repo, layer):
    filepath = _layerPath(layer)
    repo.importgeopkg(filepath, "master", layer, "tester", "test@test.test", False)

def createSimpleTestRepo(group=None, name=None):

    repo = createRepoAtUrl(REPOS_SERVER_URL, group or "Lesson repos", name or "simple_%s" %  str(time.time()))

    _importLayerToRepo(repo, "first")

    log = repo.log()
    filename = tempFilename("gpkg")
    repo.checkoutlayer(filename, "points", ref = log[0].commitid)
    layer = QgsVectorLayer(filename, "points", "ogr")
    with edit(layer):
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(10, 10)))
        feat.setAttributes([3, 2])
        layer.addFeatures([feat])
    repo.importgeopkg(layer, "master", "second", "tester", "test@test.test", True)
    log = repo.log()
    filename = tempFilename("gpkg")
    repo.checkoutlayer(filename, "points", ref = log[0].commitid)
    layer = QgsVectorLayer(filename, "points", "ogr")
    features = list(layer.getFeatures())
    for feature in features:
        pt = feature.geometry().asPoint()
        if pt.x() == 10 and pt.y()== 10:
            featureid = feature.id()
            break
    with edit(layer):
        layer.changeGeometry(featureid, QgsGeometry.fromPoint(QgsPoint(5, 5)))
    repo.importgeopkg(layer, "master", "third", "tester", "test@test.test", True)
    repo.createbranch(repo.HEAD, "mybranch")
    repo.createtag(repo.HEAD, "mytag")
    global _lastRepo
    _lastRepo = repo
    return _lastRepo

def createExampleRepo(group=None, name=None):

    repo = createRepoAtUrl(REPOS_SERVER_URL, group or "Lesson repos", name or "simple_%s" %  str(time.time()))

    AUTHOR = "Samuel Tarly"
    EMAIL = "tarlys@whitecastle.we"

    repo.importgeopkg(_layerPath("buildings_000_original"), "master",
                      "Adds 2016 Buildings layer",
                      AUTHOR, EMAIL, False)

    repo.importgeopkg(_layerPath("buildings_001_edits"), "master",
                      "Updates Block 1026 buildings",
                      AUTHOR, EMAIL, False)

    repo.importgeopkg(_layerPath("buildings_002_edits"), "master",
                      "Updates Block 1024 buildings",
                      AUTHOR, EMAIL, False)

    global _lastRepo
    _lastRepo = repo
    return _lastRepo

def addMoreCommits():
    global _lastRepo
    repo = _lastRepo

    AUTHOR = "John Snow"
    EMAIL = "snowj@whitecastle.we"

    repo.importgeopkg(_layerPath("buildings_003_edits"), "john_edits",
                      "Updates Block 1023 buildings",
                      AUTHOR, EMAIL, False)

    repo.importgeopkg(_layerPath("buildings_004_edits"), "john_edits",
                      "Updates Block 1055 buildings",
                      AUTHOR, EMAIL, False)

def _exportAndEditLayer():
    layer = checkoutLayer(_lastRepo, "buildings", None)
    idx = layer.dataProvider().fieldNameIndex("DESCRIPTIO")
    features = list(layer.getFeatures())
    with edit(layer):
        layer.changeAttributeValue(features[0].id(), idx, "COMMERCIAL")
        layer.deleteFeatures([features[1].id()])

try:
    from lessons.lesson import Lesson, Step
    class GeoGigLesson(Lesson):
        def __init__(self, name):
            folder = os.path.dirname(traceback.extract_stack()[-2][0])
            Lesson.__init__(self, name, "GeoGig lessons", "lesson.html", folder=folder)
            helpFile= os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                  "common",
                                                   "preparegeogig.md"))
            self.addStep("Prepare GeoGig environment", helpFile,
               endcheck=checkGeoGig, steptype=Step.MANUALSTEP)
            self.setCleanup(cleanup)
except:
    pass


def checkGeoGig():
    url = "http://localhost:8182/repos"
    try:
        r = requests.get(url)
        r.raise_for_status()
        return True
    except:
        return False
