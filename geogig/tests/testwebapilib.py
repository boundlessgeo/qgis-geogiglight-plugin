import unittest
import os
from geogig.geogigwebapi.repository import Repository
import shutil


REPOS_SERVER_URL = "http://localhost:8182/"
REPOS_FOLDER = ""
def _createTestRepo(name):
    i = len(os.listdir(REPOS_FOLDER))
    folderName = "%i_%s" % (i, name)
    destPath = os.path.join(REPOS_FOLDER, folderName)
    orgPath = os.path.join(os.path.dirname(__file__), "data", "repos", name)
    shutil.copytree(orgPath, destPath)
    repo = Repository(REPOS_SERVER_URL + "repos/%s/" % folderName)
    return repo

class WebApiTests(unittest.TestCase):

    def setUp(self):
        pass

    def testLog(self):
        pass

    def testLogInEmptyRepo(self):
        pass

    def testLogWithPath(self):
        pass

    def testBlame(self):
        pass

    def testDownload(self):
        pass

    def testDownloadNonHead(self):
        pass

    def testDescription(self):
        pass

    def testDescriptionInEmptyRepo(self):
        pass

    def testFeature(self):
        pass

    def testFeatureDiff(self):
        pass

    def testTrees(self):
        pass

    def testTreesNonHead(self):
        pass

    def testRemoveTree(self):
        pass

    def testTags(self):
        pass

    def testRemoveTags(self):
        pass

    def testDiff(self):
        pass

    def testDiffWithPath(self):
        pass

    def testExportDiff(self):
        pass

    def testRevParse(self):
        pass

    def testLastUpdated(self):
        pass

    def testBranches(self):
        pass

    def testBranchesInEmptyRepo(self):
        pass

    def testCreateBranch(self):
        pass

    def testRemoveBranch(self):
        pass



def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(WebApiTests, 'test'))
    return suite

def unitTests():
    _tests = []
    _tests.extend(suite())
    return _tests