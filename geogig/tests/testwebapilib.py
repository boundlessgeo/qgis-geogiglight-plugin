#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import os
from geogig.geogigwebapi.repository import Repository, createRepoAtUrl
from geogig.tools.utils import tempFilename, loadLayerNoCrsDialog
from qgis.core import *
from geogig.tools.gpkgsync import getCommitId
from geogig.gui.dialogs.conflictdialog import ConflictDialog
from geogig.tests import _createTestRepo, _layer
from geogig.tests import REPOS_SERVER_URL
from geogig.geogigwebapi.repository import repositoriesFromUrl, GeoGigException
import uuid


class WebApiTests(unittest.TestCase):

    def setUp(self):
        pass

    def testCreateRepo(self):
        repos = repositoriesFromUrl(REPOS_SERVER_URL, "test")
        n = len(repos)
        name = str(uuid.uuid4()).replace("-", "")
        createRepoAtUrl(REPOS_SERVER_URL, "test", name)
        repos = repositoriesFromUrl(REPOS_SERVER_URL, "test")
        self.assertEqual(n + 1, len(repos))
        self.assertTrue(name in [r.title for r in repos])

    def testCreateRepoWithNameThatAlreadyExists(self):
        repo = _createTestRepo("simple")
        self.assertRaises(GeoGigException, lambda: createRepoAtUrl(REPOS_SERVER_URL, "test", "original_simple"))

    def testLog(self):
        repo = _createTestRepo("simple")
        log = repo.log()
        self.assertEqual(3, len(log))
        self.assertEqual("third", log[0].message)

    def testLogInEmptyRepo(self):
        repo = _createTestRepo("empty")
        log = repo.log()
        self.assertEqual(0, len(log))

    def testLogInEmptyBranch(self):
        repo = _createTestRepo("empty")
        log = repo.log(until="master")
        self.assertEqual(0, len(log))

    def testLogWithPath(self):
        repo = _createTestRepo("simple")
        log = repo.log(path = "points/fid--678854f5_155b574742f_-8000")
        self.assertEqual(2, len(log))
        self.assertEqual("third", log[0].message)
        self.assertEqual("first", log[1].message)

    def testLogMultipleParents(self):
        repo = _createTestRepo("withmerge")
        log = repo.log()
        self.assertEqual(2, len(log[0].parents))

    def testBlame(self):
        repo = _createTestRepo("simple")
        blame = repo.blame("points/fid--678854f5_155b574742f_-8000")
        print blame

    def testDownload(self):
        repo = _createTestRepo("simple")
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points")
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(layer.isValid())

    def testDownloadNonHead(self):
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

    def testDescription(self):
        repo = _createTestRepo("simple")
        self.assertTrue("<p>LAST VERSION: <b>third" in repo.fullDescription())

    def testDescriptionInEmptyRepo(self):
        repo = _createTestRepo("empty")
        self.assertTrue("<p>LAST VERSION: <b></b></p>" in repo.fullDescription())

    def testFeature(self):
        repo = _createTestRepo("simple")
        expected = {'geometry': 'POINT (20.532220860123836 83.62989408803831)', 'n': 1}
        feature = repo.feature("points/fid--678854f5_155b574742f_-8000", repo.HEAD)
        self.assertEqual(expected, feature)

    def testFeatureDiff(self):
        pass

    def testTrees(self):
        repo = _createTestRepo("severallayers")
        self.assertEquals(["points", "lines"], repo.trees())

    def testTreesNonHead(self):
        repo = _createTestRepo("severallayers")
        log = repo.log()
        self.assertEqual(4, len(log))
        commitid = log[-1].commitid
        self.assertEquals(["points"], repo.trees(commit = commitid))

    def testRemoveTree(self):
        repo = _createTestRepo("simple", True)
        self.assertEquals(["points"], repo.trees())
        repo.removetree("points", "me", "me@email.com")
        self.assertEquals([], repo.trees())

    def testRemoveTreeFromBranch(self):
        repo = _createTestRepo("simple", True)
        self.assertEquals(["points"], repo.trees("mybranch"))
        repo.removetree("points", "me", "me@email.com", "mybranch")
        self.assertEquals([], repo.trees("mybranch"))
        self.assertEquals(["points"], repo.trees())

    def testTags(self):
        repo = _createTestRepo("simple")
        tags = repo.tags()
        log = repo.log()
        self.assertEqual({"mytag": log[0].commitid}, tags)

    def testNoTags(self):
        repo = _createTestRepo("empty")
        tags = repo.tags()
        self.assertEqual({}, tags)

    def testCreateTag(self):
        repo = _createTestRepo("simple", True)
        repo.createtag(repo.HEAD, "anothertag")
        tags = repo.tags()
        log = repo.log()
        self.assertEqual({"mytag": log[0].commitid, "anothertag": log[0].commitid}, tags)

    def testRemoveTags(self):
        repo = _createTestRepo("simple", True)
        tags = repo.tags()
        self.assertEquals(1, len(tags))
        repo.deletetag(tags.keys()[0])
        tags = repo.tags()
        self.assertEquals(0, len(tags))

    def testDiff(self):
        repo = _createTestRepo("simple")
        log = repo.log()
        self.assertEqual(3, len(log))
        diff = repo.diff(log[-1].commitid, log[0].commitid)
        self.assertEqual(2, len(diff))
        self.assertEqual({"points/fid--678854f5_155b574742f_-8000", "points/fid--678854f5_155b574742f_-7ffd"},
                         {d.path for d in diff})

    def _compareLists(self, s, t):
        t = list(t)
        try:
            for elem in s:
                t.remove(elem)
        except ValueError:
            return False
        return not t

    def testDiffWithPath(self):
        repo = _createTestRepo("simple")
        log = repo.log()
        self.assertEqual(3, len(log))
        expected = [{u'changetype': u'NO_CHANGE', u'attributename': u'n', u'oldvalue': 1},
                    {u'crs': u'EPSG:4326', u'geometry': True, u'changetype': u'MODIFIED', u'attributename': u'geometry', u'oldvalue': u'POINT (13.997099976619822 76.31340005541968)',
                      u'newvalue': u'POINT (20.532220860123836 83.62989408803831)'}]
        diff = repo.diff(log[-1].commitid, log[0].commitid, "points/fid--678854f5_155b574742f_-8000")
        self.assertTrue(1, len(diff))
        self.assertTrue(self._compareLists(expected, diff[0].featurediff()))

    def testExportDiff(self):
        repo = _createTestRepo("simple")
        filename = tempFilename("gpkg")
        repo.exportdiff("points", "HEAD", "HEAD~1", filename)
        self.assertTrue(os.path.exists(filename))
        #Check exported gpkg is correct

    def testRevParse(self):
        repo = _createTestRepo("simple")
        head = repo.log()[0].commitid
        self.assertEqual(head, repo.revparse(repo.HEAD))

    def testLastUpdated(self):
        pass

    def testBranches(self):
        repo = _createTestRepo("simple")
        self.assertEquals(["master", "mybranch"], repo.branches())

    def testBranchesInEmptyRepo(self):
        repo = _createTestRepo("empty")
        self.assertEquals(["master"], repo.branches())

    def testCreateBranch(self):
        repo = _createTestRepo("simple", True)
        self.assertEquals(["master", "mybranch"], repo.branches())
        repo.createbranch(repo.HEAD, "anotherbranch")
        self.assertEquals({"master", "mybranch", "anotherbranch"}, set(repo.branches()))
        self.assertEqual(repo.revparse(repo.HEAD), repo.revparse("anotherbranch"))

    def testRemoveBranch(self):
        repo = _createTestRepo("simple", True)
        self.assertEquals(["master", "mybranch"], repo.branches())
        repo.deletebranch("mybranch")
        self.assertEquals(["master"], repo.branches())

    def testFirstImport(self):
        repo = _createTestRepo("empty", True)
        layer = _layer("points")
        repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", False)
        log = repo.log()
        self.assertEqual(1, len(log))
        self.assertEqual("message", log[0].message)
        self.assertEqual(["points"], repo.trees())

    def testNonAsciiImport(self):
        repo = _createTestRepo("empty", True)
        layer = _layer("points")
        msg = "Покупая птицу, смотри, нет ли у нее зубов. Если есть зубы, то это не птица"
        repo.importgeopkg(layer, "master", msg, "Даниил Хармс", "daniil@kharms.com", False)
        log = repo.log()
        self.assertEqual(1, len(log))
        self.assertEqual(msg, log[0].message)
        self.assertEqual(["points"], repo.trees())

    def testImportInterchangeFormat(self):
        repo = _createTestRepo("simple", True)
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points")
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(layer.isValid())
        features = list(layer.getFeatures())
        self.assertEqual(2, len(features))
        with edit(layer):
            layer.deleteFeatures([features[0].id()])
        features = list(layer.getFeatures())
        self.assertEqual(1, len(features))
        repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        log = repo.log()
        self.assertEqual("message", log[0].message)
        self.assertEqual(["points"], repo.trees())
        filename2 = tempFilename("gpkg")
        repo.checkoutlayer(filename2, "points")
        layer2 = loadLayerNoCrsDialog(filename, "points2", "ogr")
        self.assertTrue(layer2.isValid())
        features2 = list(layer2.getFeatures())
        self.assertEqual(1, len(features2))


    def testConflictsWithDeleteAndModify(self):
        repo = _createTestRepo("simple", True)
        log = repo.log()
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = log[0].commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        filename2 = tempFilename("gpkg")
        repo.checkoutlayer(filename2, "points", ref = log[0].commitid)
        layer2 = loadLayerNoCrsDialog(filename2, "points", "ogr")
        features = list(layer.getFeatures())
        with edit(layer):
            layer.changeAttributeValue(features[0].id(), 1, 1000)
            layer.changeAttributeValue(features[1].id(), 1, 2000)
        _, _, conflicts, _ = repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        self.assertEqual(0, len(conflicts))
        features2 = list(layer2.getFeatures())
        with edit(layer2):
            layer2.deleteFeatures([features2[0].id()])
            layer2.deleteFeatures([features2[1].id()])
        _, _, conflicts, _ = repo.importgeopkg(layer2, "master", "another message", "me", "me@mysite.com", True)
        self.assertEqual(2, len(conflicts))
        self.assertEqual("points/fid--678854f5_155b574742f_-8000", conflicts[0].path)
        self.assertEqual("74c26fa429b847bc7559f4105975bc2d7b2ef80c", conflicts[0].originCommit)
        self.assertEqual("points/fid--678854f5_155b574742f_-7ffd", conflicts[1].path)

    def testResolveConflictWithLocalVersion(self):
        repo, conflicts = self._createConflict()
        conflicts[0].resolveWithLocalVersion()
        conflicts[1].resolveWithLocalVersion()
        repo.commitAndCloseMergeAndTransaction("user", "email@email.com", "conflict resolution", conflicts[0].transactionId)
        self.assertTrue("conflict resolution" in repo.log()[0].message)
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = repo.HEAD)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        features = list(layer.getFeatures())
        self.assertTrue([1, 1001], features[0].attributes())
        self.assertTrue([2, 2001], features[1].attributes())

    def testResolveConflictWithRemoteVersion(self):
        repo, conflicts = self._createConflict()
        conflicts[0].resolveWithRemoteVersion()
        conflicts[1].resolveWithRemoteVersion()
        repo.commitAndCloseMergeAndTransaction("user", "email@email.com", "conflict resolution", conflicts[0].transactionId)
        self.assertTrue("conflict resolution" in repo.log()[0].message)
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = repo.HEAD)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        features = list(layer.getFeatures())
        self.assertTrue([1, 1000], features[0].attributes())
        self.assertTrue([2, 2000], features[1].attributes())

    def testResolveConflictWithNewFeature(self):
        repo, conflicts = self._createConflict()
        conflicts[0].resolveWithNewFeature({"fid": 1, "n": 1002})
        conflicts[1].resolveWithRemoteVersion()
        repo.commitAndCloseMergeAndTransaction("user", "email@email.com", "conflict resolution", conflicts[0].transactionId)
        self.assertTrue("conflict resolution" in repo.log()[0].message)
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = repo.HEAD)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        features = list(layer.getFeatures())
        self.assertTrue([1, 1002], features[0].attributes())
        self.assertTrue([2, 2000], features[1].attributes())

    def _createConflict(self):
        repo = _createTestRepo("simple", True)
        log = repo.log()
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = log[0].commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        filename2 = tempFilename("gpkg")
        repo.checkoutlayer(filename2, "points", ref = log[0].commitid)
        layer2 = loadLayerNoCrsDialog(filename2, "points", "ogr")
        features = list(layer.getFeatures())
        with edit(layer):
            layer.changeAttributeValue(features[0].id(), 1, 1000)
            layer.changeAttributeValue(features[1].id(), 1, 2000)
        _, _, conflicts, _ = repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        self.assertEqual(0, len(conflicts))
        features2 = list(layer2.getFeatures())
        with edit(layer2):
            layer2.changeAttributeValue(features2[0].id(), 1, 1001)
            layer2.changeAttributeValue(features2[1].id(), 1, 2001)
        _, _, conflicts, _ = repo.importgeopkg(layer2, "master", "another message", "me", "me@mysite.com", True)
        self.assertEqual(2, len(conflicts))
        self.assertEqual("points/fid--678854f5_155b574742f_-8000", conflicts[0].path)
        self.assertEqual({'geometry': 'Point (20.53222086012383585 83.62989408803831282)', 'fid': 2, 'n': 1001}, conflicts[0].localFeature)
        self.assertEqual("points/fid--678854f5_155b574742f_-7ffd", conflicts[1].path)
        return repo, conflicts


    def testLayerCommitId(self):
        repo = _createTestRepo("simple", True)
        log = repo.log()
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = log[1].commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(log[1].commitid, getCommitId(layer))

    def testRemotes(self):
        repo = _createTestRepo("simple", True)
        #=======================================================================
        # remotes = repo.remotes()
        # self.assertEqual([], remotes)
        #=======================================================================
        repo.addremote("myremote", "http://myurl.com")
        remotes = repo.remotes()
        self.assertEqual(["myremote"], remotes)
        repo.removeremote("myremote")
        remotes = repo.remotes()
        self.assertEqual([], remotes)


def webapiSuite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(WebApiTests, 'test'))
    return suite

