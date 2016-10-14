import os
import shutil
from geogig.geogigwebapi.repository import Repository
from geogig.tools.utils import loadLayerNoCrsDialog

conf = dict(
        REPOS_SERVER_URL = "http://localhost:8182/",
        REPOS_FOLDER = os.path.expanduser("~/geogig/server")
    )

def _createTestRepo(name, modifiesRepo = False, group = None , title = None):

    conf.update([(k, os.getenv(k)) for k in conf if k in os.environ])

    i = len(os.listdir(conf['REPOS_FOLDER']))
    if modifiesRepo:
        folderName = "%i_%s" % (i, name)
    else:
        folderName = "original_%s" % name
    destPath = os.path.join(conf['REPOS_FOLDER'], folderName)
    if not os.path.exists(destPath):
        orgPath = os.path.join(os.path.dirname(__file__), "data", "repos", name)
        shutil.copytree(orgPath, destPath)
    global _lastRepo
    _lastRepo = Repository(conf['REPOS_SERVER_URL'] + "repos/%s/" % folderName, group or "test repositories",
                           title or ("%s [%i]" % (name, i)))
    return _lastRepo

def _layer(name):
    path = os.path.join(os.path.dirname(__file__), "data", "layers", name + ".gpkg")
    return loadLayerNoCrsDialog(path, name, "ogr")