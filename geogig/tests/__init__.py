import os
import shutil
import time
from geogig.geogigwebapi.repository import createRepoAtUrl, GeoGigException, Repository
from qgis.core import *
from qgiscommons2.files import tempFilename
from qgiscommons2.layers import loadLayerNoCrsDialog

conf = dict(
        REPOS_SERVER_URL = "http://localhost:8182/",
    )

def _importLayerToRepo(repo, layer):
    filepath = _layerPath(layer)
    repo.importgeopkg(filepath, "master", layer, "tester", "test@test.test", False)

simpleTestRepo = None
def _createSimpleTestRepo(modifiesRepo = False, group=None, name=None):
    conf.update([(k, os.getenv(k)) for k in conf if k in os.environ])

    if modifiesRepo:
        repo = createRepoAtUrl(conf['REPOS_SERVER_URL'], group or "test", name or "simple_%s" %  str(time.time()))
    else:
        global simpleTestRepo
        if simpleTestRepo is not None:
            return simpleTestRepo
        try:
            simpleTestRepo = createRepoAtUrl(conf['REPOS_SERVER_URL'], group or "test", name or "original_simple")
        except GeoGigException:
            simpleTestRepo = Repository(conf['REPOS_SERVER_URL'] + "repos/original_simple/", group or "test", name or "original_simple")
            return simpleTestRepo
        repo = simpleTestRepo
    _importLayerToRepo(repo, "first")

    log = repo.log()
    filename = tempFilename("gpkg")
    repo.checkoutlayer(filename, "points", ref = log[0].commitid)
    layer = loadLayerNoCrsDialog(filename, "points", "ogr")
    with edit(layer):
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(10, 10)))
        feat.setAttributes([3, 2])
        layer.addFeatures([feat])
    repo.importgeopkg(layer, "master", "second", "tester", "test@test.test", True)
    log = repo.log()
    filename = tempFilename("gpkg")
    repo.checkoutlayer(filename, "points", ref = log[0].commitid)
    layer = loadLayerNoCrsDialog(filename, "points", "ogr")
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


withMergeTestRepo = None
def _createWithMergeTestRepo(modifiesRepo = False):
    conf.update([(k, os.getenv(k)) for k in conf if k in os.environ])

    if modifiesRepo:
        repo = createRepoAtUrl(conf['REPOS_SERVER_URL'], "test", "withmerge_%s" %  str(time.time()))
    else:
        global withMergeTestRepo
        if withMergeTestRepo is not None:
            return withMergeTestRepo
        try:
            withMergeTestRepo = createRepoAtUrl(conf['REPOS_SERVER_URL'], "test", "original_withmerge")
        except GeoGigException:
            withMergeTestRepo = Repository(conf['REPOS_SERVER_URL'] + "repos/original_withmerge/", "test", "original_withmerge")
            return withMergeTestRepo
        repo = withMergeTestRepo
    _importLayerToRepo(repo, "first")

    repo.createbranch(repo.HEAD, "mybranch")
    filename = tempFilename("gpkg")
    repo.checkoutlayer(filename, "points", ref = repo.HEAD)
    layer = loadLayerNoCrsDialog(filename, "points", "ogr")
    with edit(layer):
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(10, 10)))
        feat.setAttributes([3, 2])
        layer.addFeatures([feat])
    repo.importgeopkg(layer, "mybranch", "second", "tester", "test@test.test", True)

    filename = tempFilename("gpkg")
    repo.checkoutlayer(filename, "points", ref = repo.HEAD)
    layer = loadLayerNoCrsDialog(filename, "points", "ogr")
    with edit(layer):
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(9, 9)))
        feat.setAttributes([9, 9])
        layer.addFeatures([feat])
    repo.importgeopkg(layer, "master", "second", "tester", "test@test.test", True)

    repo.merge("mybranch", "master")
    global _lastRepo
    _lastRepo = repo
    return _lastRepo


emptyTestRepo = None
def _createEmptyTestRepo(modifiesRepo = False, group=None, name=None):
    conf.update([(k, os.getenv(k)) for k in conf if k in os.environ])

    if modifiesRepo:
        repo = createRepoAtUrl(conf['REPOS_SERVER_URL'], group or "test", name or "empty_%s" %  str(time.time()))
    else:
        global emptyTestRepo
        if emptyTestRepo is not None:
            return emptyTestRepo
        try:
            emptyTestRepo = createRepoAtUrl(conf['REPOS_SERVER_URL'], group or "test", name or "original_empty")
        except GeoGigException:
            emptyTestRepo = Repository(conf['REPOS_SERVER_URL'] + "repos/original_empty/", group or "test", name or "original_empty")
            return emptyTestRepo
        repo = emptyTestRepo
    global _lastRepo
    _lastRepo = repo
    return _lastRepo

multilayerTestRepo = None
def _createMultilayerTestRepo(modifiesRepo = False):
    conf.update([(k, os.getenv(k)) for k in conf if k in os.environ])

    if modifiesRepo:
        repo = createRepoAtUrl(conf['REPOS_SERVER_URL'], "test", "severallayers_%s" %  str(time.time()))
    else:
        global multilayerTestRepo
        if multilayerTestRepo is not None:
            return multilayerTestRepo
        try:
            multilayerTestRepo = createRepoAtUrl(conf['REPOS_SERVER_URL'], "test", "original_severallayers")
        except GeoGigException:
            multilayerTestRepo = Repository(conf['REPOS_SERVER_URL'] + "repos/original_severallayers/", "test", "original_severallayers")
            return multilayerTestRepo
        repo = multilayerTestRepo
    _importLayerToRepo(repo, "first")
    _importLayerToRepo(repo, "second")
    _importLayerToRepo(repo, "third")
    _importLayerToRepo(repo, "lines")
    repo.createbranch(repo.HEAD, "mybranch")
    global _lastRepo
    _lastRepo = repo
    return _lastRepo


def _layerPath(name):
    return os.path.join(os.path.dirname(__file__), "data", "layers", name + ".gpkg")

def _layer(name):
    return loadLayerNoCrsDialog(_layerPath(name), name, "ogr")