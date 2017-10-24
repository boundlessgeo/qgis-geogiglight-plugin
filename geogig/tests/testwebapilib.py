#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from builtins import str

import os
import uuid
import unittest
import time


from qgis.core import QgsFeatureRequest, edit, QgsGeometry, QgsPoint

from geogig.gui.dialogs.conflictdialog import ConflictDialog

from geogig.geogigwebapi.repository import (Repository,
                                            createRepoAtUrl,
                                            repositoriesFromUrl,
                                            GeoGigException,
                                            CannotPushException
                                           )

from geogig.tools.gpkgsync import getCommitId

from geogig.tests import (_layer, _createSimpleTestRepo, _createEmptyTestRepo,
                        _createMultilayerTestRepo, _createWithMergeTestRepo)
from geogig.tests import conf

from qgiscommons2.files import tempFilename
from qgiscommons2.layers import loadLayerNoCrsDialog

class WebApiTests(unittest.TestCase):

    def setUp(self):
        pass

    def testCreateRepo(self):
        repos = repositoriesFromUrl(conf['REPOS_SERVER_URL'], "test")
        n = len(repos)
        name = str(uuid.uuid4()).replace("-", "")
        createRepoAtUrl(conf['REPOS_SERVER_URL'], "test", name)
        repos = repositoriesFromUrl(conf['REPOS_SERVER_URL'], "test")
        self.assertEqual(n + 1, len(repos))
        self.assertTrue(name in [r.title for r in repos])

    def testCreateRepoWithNameThatAlreadyExists(self):
        repo_name =  "test-repo-same-name-%s" %  str(time.time())
        repo = _createSimpleTestRepo(group="test",name=repo_name)
        self.assertRaises(GeoGigException, lambda: createRepoAtUrl(conf['REPOS_SERVER_URL'], "test", repo_name))

    def testLog(self):
        repo = _createSimpleTestRepo()
        log = repo.log()
        self.assertEqual(3, len(log))
        self.assertEqual("third", log[0].message)

    def testLogInEmptyRepo(self):
        repo = _createEmptyTestRepo()
        log = repo.log()
        self.assertEqual(0, len(log))

    def testLogInEmptyBranch(self):
        repo = _createEmptyTestRepo()
        log = repo.log(until="master")
        self.assertEqual(0, len(log))

    def testLogWithPath(self):
        repo = _createSimpleTestRepo()
        diff = repo.diff(repo.log()[1].commitid, repo.log()[0].commitid)
        path = diff[0].path
        log = repo.log(path = path)
        self.assertEqual(2, len(log))
        self.assertEqual("third", log[0].message)
        self.assertEqual("second", log[1].message)

    def testLogMultipleParents(self):
        repo = _createWithMergeTestRepo("withmerge")
        log = repo.log()
        self.assertEqual(2, len(log[0].parents))

    def testBlame(self):
        repo = _createSimpleTestRepo()
        #blame = repo.blame("points/fid--678854f5_155b574742f_-8000")
        # fix_print_with_import

    def testDownload(self):
        repo = _createSimpleTestRepo()
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points")
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(layer.isValid())

    def testDownloadNonHead(self):
        repo = _createSimpleTestRepo()
        log = repo.log()
        self.assertEqual(3, len(log))
        commitid = log[-1].commitid
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(layer.isValid())
        features = list(layer.getFeatures())
        self.assertEqual(1, len(features))

    def testFeature(self):
        repo = _createSimpleTestRepo()
        expected = {u'geometry': u'POINT (5 5)', u'n': 2}
        diff = repo.diff(repo.log()[2].commitid, repo.log()[1].commitid)
        path = diff[0].path
        feature = repo.feature(path, repo.HEAD)
        self.assertEqual(expected, feature)

    def testTrees(self):
        repo = _createMultilayerTestRepo()
        self.assertEquals(["points", "lines"], repo.trees())

    def testTreesNonHead(self):
        repo = _createMultilayerTestRepo()
        log = repo.log()
        self.assertEqual(4, len(log))
        commitid = log[-1].commitid
        self.assertEquals(["points"], repo.trees(commit = commitid))

    def testRemoveTree(self):
        repo = _createSimpleTestRepo(True)
        self.assertEquals(["points"], repo.trees())
        repo.removetree("points", "me", "me@email.com")
        self.assertEquals([], repo.trees())

    def testRemoveTreeFromBranch(self):
        repo = _createSimpleTestRepo(True)
        self.assertEquals(["points"], repo.trees("mybranch"))
        repo.removetree("points", "me", "me@email.com", "mybranch")
        self.assertEquals([], repo.trees("mybranch"))
        self.assertEquals(["points"], repo.trees())

    def testTags(self):
        repo = _createSimpleTestRepo()
        tags = repo.tags()
        log = repo.log()
        self.assertEqual(1, len(tags))
        self.assertEqual(tags["mytag"], log[0].commitid)

    def testNoTags(self):
        repo = _createEmptyTestRepo()
        tags = repo.tags()
        self.assertEqual({}, tags)

    def testCreateTag(self):
        repo = _createSimpleTestRepo(True)
        repo.createtag(repo.HEAD, "anothertag")
        tags = repo.tags()
        log = repo.log()
        self.assertEqual(2, len(tags))
        self.assertTrue("mytag" in tags)
        self.assertEqual(tags["mytag"], log[0].commitid)
        self.assertTrue("anothertag" in tags)
        self.assertEqual(tags["anothertag"], log[0].commitid)

    def testRemoveTags(self):
        repo = _createSimpleTestRepo(True)
        tags = repo.tags()
        self.assertEquals(1, len(tags))
        repo.deletetag(list(tags.keys())[0])
        tags = repo.tags()
        self.assertEquals(0, len(tags))

    def testDiff(self):
        repo = _createSimpleTestRepo()
        log = repo.log()
        self.assertEqual(3, len(log))
        diff = {d.path for d in repo.diff(log[0].commitid, log[1].commitid)}
        self.assertEqual(1, len(diff))

    def _compareLists(self, s, t):
        t = list(t)
        try:
            for elem in s:
                t.remove(elem)
        except ValueError:
            return False
        return not t

    def testDiffWithPath(self):
        repo =_createSimpleTestRepo()
        log = repo.log()
        self.assertEqual(3, len(log))
        expected = [{u'changetype': u'ADDED', u'attributename': u'n', u'newvalue': 2},
                    {u'geometry': True, u'crs': u'EPSG:4326', u'changetype': u'ADDED',
                     u'attributename': u'geometry', u'newvalue': u'POINT (5 5)'}]
        diff = repo.diff(repo.log()[2].commitid, repo.log()[1].commitid)
        path = diff[0].path
        diff = repo.diff(log[-1].commitid, log[0].commitid, path)
        self.assertTrue(1, len(diff))
        self.assertTrue(self._compareLists(expected, diff[0].featurediff()))

    def testExportDiff(self):
        repo = _createSimpleTestRepo()
        filename = tempFilename("gpkg")
        repo.exportdiff("HEAD", "HEAD~1", filename)
        self.assertTrue(os.path.exists(filename))
        #Check exported gpkg is correct

    def testRevParse(self):
        repo = _createSimpleTestRepo()
        head = repo.log()[0].commitid
        self.assertEqual(head, repo.revparse(repo.HEAD))

    def testLastUpdated(self):
        pass

    def testBranches(self):
        repo = _createSimpleTestRepo()
        self.assertEquals(["master", "mybranch"], repo.branches())

    def testBranchesInEmptyRepo(self):
        repo = _createEmptyTestRepo()
        self.assertEquals(["master"], repo.branches())

    def testCreateBranch(self):
        repo = _createSimpleTestRepo(True)
        self.assertEquals(["master", "mybranch"], repo.branches())
        repo.createbranch(repo.HEAD, "anotherbranch")
        self.assertEquals({"master", "mybranch", "anotherbranch"}, set(repo.branches()))
        self.assertEqual(repo.revparse(repo.HEAD), repo.revparse("anotherbranch"))

    def testRemoveBranch(self):
        repo = _createSimpleTestRepo(True)
        self.assertEquals(["master", "mybranch"], repo.branches())
        repo.deletebranch("mybranch")
        self.assertEquals(["master"], repo.branches())

    def testFirstImport(self):
        repo = _createEmptyTestRepo(True)
        layer = _layer("points")
        repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", False)
        log = repo.log()
        self.assertEqual(1, len(log))
        self.assertEqual("message", log[0].message)
        self.assertEqual(["points"], repo.trees())

    def testNonAsciiImport(self):
        repo = _createEmptyTestRepo(True)
        layer = _layer("points")
        msg = "Покупая птицу, смотри, нет ли у нее зубов. Если есть зубы, то это не птица"
        repo.importgeopkg(layer, "master", msg, "Даниил Хармс", "daniil@kharms.com", False)
        log = repo.log()
        self.assertEqual(1, len(log))
        self.assertEqual(msg.decode("utf-8"), log[0].message)
        self.assertEqual(["points"], repo.trees())

    def testImportInterchangeFormat(self):
        repo = _createSimpleTestRepo(True)
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

    def testImportWithNullValue(self):
        repo = _createSimpleTestRepo(True)
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points")
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(layer.isValid())
        features = list(layer.getFeatures())
        self.assertEqual(2, len(features))
        idx = layer.dataProvider().fieldNameIndex("n")
        features = list(layer.getFeatures())
        with edit(layer):
            layer.changeGeometry(features[0].id(), QgsGeometry.fromPoint(QgsPoint(123, 456)))
            layer.changeAttributeValue(features[0].id(), idx, None)
        repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        log = repo.log()
        self.assertEqual("message", log[0].message)

    def testConflictsWithDeleteAndModify(self):
        repo = _createSimpleTestRepo(True)
        log = repo.log()
        origCommit = log[0].commitid
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = log[0].commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        idx = layer.dataProvider().fieldNameIndex("n")
        filename2 = tempFilename("gpkg")
        repo.checkoutlayer(filename2, "points", ref = log[0].commitid)
        layer2 = loadLayerNoCrsDialog(filename2, "points", "ogr")
        features = list(layer.getFeatures())
        with edit(layer):
            layer.changeAttributeValue(features[0].id(), idx, 1000)
            layer.changeAttributeValue(features[1].id(), idx, 2000)
        _, _, conflicts, _ = repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        self.assertEqual(0, len(conflicts))
        features2 = list(layer2.getFeatures())
        with edit(layer2):
            layer2.deleteFeatures([features2[0].id()])
            layer2.deleteFeatures([features2[1].id()])
        _, _, conflicts, _ = repo.importgeopkg(layer2, "master", "another message", "me", "me@mysite.com", True)
        self.assertEqual(2, len(conflicts))
        diff = repo.diff(repo.log()[0].commitid, repo.log()[1].commitid)
        self.assertEqual(diff[0].path, conflicts[0].path)
        self.assertEqual(origCommit, conflicts[0].originCommit)
        self.assertEqual(diff[1].path, conflicts[1].path)

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
        repo = _createSimpleTestRepo(True)
        log = repo.log()
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = log[0].commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        idx = layer.dataProvider().fieldNameIndex("n")
        filename2 = tempFilename("gpkg")
        repo.checkoutlayer(filename2, "points", ref = log[0].commitid)
        layer2 = loadLayerNoCrsDialog(filename2, "points", "ogr")
        features = list(layer.getFeatures())
        with edit(layer):
            layer.changeAttributeValue(features[0].id(), idx, 1000)
            layer.changeAttributeValue(features[1].id(), idx, 2000)
        _, _, conflicts, _ = repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        self.assertEqual(0, len(conflicts))
        features2 = list(layer2.getFeatures())
        with edit(layer2):
            layer2.changeAttributeValue(features2[0].id(), idx, 1001)
            layer2.changeAttributeValue(features2[1].id(), idx, 2001)
        layer3 = loadLayerNoCrsDialog(filename2, "points", "ogr")
        feature = next(layer3.getFeatures(QgsFeatureRequest(features2[0].id())))
        self.assertEquals(1001, feature["n"])
        _, _, conflicts, _ = repo.importgeopkg(layer2, "master", "another message", "me", "me@mysite.com", True)
        self.assertEqual(2, len(conflicts))
        self.assertEqual(conflicts[0].localFeature['n'], 1001)
        return repo, conflicts


    def testLayerCommitId(self):
        repo = _createSimpleTestRepo(True)
        log = repo.log()
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = log[1].commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(log[1].commitid, getCommitId(layer))

    def testRemotes(self):
        repo = _createSimpleTestRepo(True)
        remotes = repo.remotes()
        self.assertEqual({}, remotes)
        repo.addremote("myremote", "http://myurl.com")
        remotes = repo.remotes()
        self.assertEqual({"myremote": "http://myurl.com"}, remotes)
        repo.removeremote("myremote")
        remotes = repo.remotes()
        self.assertEqual({}, remotes)

    def testPush(self):
        repo = _createSimpleTestRepo(True)
        repo2 = _createEmptyTestRepo(True)
        repo.addremote("myremote", repo2.url)
        repo2.addremote("myremote", repo.url)
        repo.push("myremote", "master")
        log = repo.log()
        log2 = repo2.log()
        self.assertEqual(log[0].message, log2[0].message)
        self.assertEqual(len(log), len(log2))
        self.assertRaises(CannotPushException, lambda: repo2.push("myremote", "master"))

    def testPullWithoutConflicts(self):
        repo = _createSimpleTestRepo(True)
        repo2 = _createEmptyTestRepo(True)
        repo.addremote("myremote", repo2.url)
        repo2.addremote("myremote", repo.url)
        repo.push("myremote", "master")
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = repo.HEAD)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        idx = layer.dataProvider().fieldNameIndex("n")
        features = list(layer.getFeatures())
        with edit(layer):
            layer.changeAttributeValue(features[0].id(), idx, 1000)
            layer.changeAttributeValue(features[1].id(), idx, 2000)
        _, _, conflicts, _ = repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        conflicts = repo2.pull("myremote", "master")
        self.assertEqual([], conflicts)
        log = repo.log()
        log2 = repo2.log()
        self.assertEqual(len(log), len(log2))
        self.assertEqual("message", log2[0].message)

    def testPullWithConflicts(self):
        repo = _createSimpleTestRepo(True)
        repo2 = _createEmptyTestRepo(True)
        repo.addremote("myremote", repo2.url)
        repo2.addremote("myremote", repo.url)
        repo.push("myremote", "master")
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = repo.HEAD)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        idx = layer.dataProvider().fieldNameIndex("n")
        features = list(layer.getFeatures())
        with edit(layer):
            layer.changeAttributeValue(features[0].id(), idx, 1000)
            layer.changeAttributeValue(features[1].id(), idx, 2000)
        _, _, conflicts, _ = repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        filename2 = tempFilename("gpkg")
        repo2.checkoutlayer(filename2, "points", ref = repo.HEAD)
        layer2 = loadLayerNoCrsDialog(filename2, "points", "ogr")
        features = list(layer2.getFeatures())
        with edit(layer2):
            layer2.changeAttributeValue(features[0].id(), idx, 1001)
            layer2.changeAttributeValue(features[1].id(), idx, 2001)
        _, _, conflicts, _ = repo2.importgeopkg(layer2, "master", "message2", "me", "me@mysite.com", True)
        conflicts = repo2.pull("myremote", "master")
        self.assertEqual(2, len(conflicts))


def webapiSuite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(WebApiTests, 'test'))
    return suite

