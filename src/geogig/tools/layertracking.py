import os
from qgis.core import *
from geogig.tools.utils import userFolder, repoFolder
import json
from json.decoder import JSONDecoder
from json.encoder import JSONEncoder
from geogig.tools.layers import  resolveLayerFromSource, \
    WrongLayerSourceException
from geogigpy.repo import Repository
from geogigpy import geogig
from PyQt4 import QtGui
from geogig import config
from geogig.tools.utils import loadLayerNoCrsDialog


tracked = []

class Encoder(JSONEncoder):
    def default(self, o):
        return o.__dict__

def decoder(jsonobj):
    if 'source' in jsonobj:
        return TrackedLayer(jsonobj['source'],
                            jsonobj['repoUrl'],
                            jsonobj['ref'])
    else:
        return jsonobj

class TrackedLayer(object):
    def __init__(self, source, repoUrl, ref):
        self.repoUrl = repoUrl
        self.ref = ref
        self.source = source
        self.geopkg, self.layername = source.split("|")
        self.layername = self.layername.split("=")[-1]


def setRef(layer, ref):
    source = formatSource(layer)
    for obj in tracked:
        if obj.source == source:
            obj.ref = ref
    saveTracked()


def addTrackedLayer(source, repoFolder, ref):
    global tracked
    source = formatSource(source)
    layer = TrackedLayer(source, repoFolder, ref)
    if layer not in tracked:
        for lay in tracked:
            if lay.source == source:
                tracked.remove(lay)
        tracked.append(layer)
        saveTracked()


def removeTrackedLayer(layer):
    global tracked
    source = formatSource(layer)
    for i, obj in enumerate(tracked):
        if obj.source == source:
            del tracked[i]
            saveTracked()
            return

def removeTrackedForRepo(repo):
    global tracked

    for i in xrange(len(tracked) - 1, -1, -1):
        layer = tracked[i]
        if layer.repoUrl == repo.url:
            del tracked[i]
    saveTracked()

def removeNonexistentTrackedLayers():
    global tracked
    for i in xrange(len(tracked) - 1, -1, -1):
        layer = tracked[i]
        if not os.path.exists(layer.geopkg):
            del tracked[i]
    saveTracked()

def saveTracked():
    filename = os.path.join(userFolder(), "trackedlayers")
    with open(filename, "w") as f:
        f.write(json.dumps(tracked, cls = Encoder))

def readTrackedLayers():
    try:
        global tracked
        filename = os.path.join(userFolder(), "trackedlayers")
        if os.path.exists(filename):
            with open(filename) as f:
                lines = f.readlines()
            jsonstring = "\n".join(lines)
            if jsonstring:
                tracked = JSONDecoder(object_hook = decoder).decode(jsonstring)
    except KeyError:
        pass

def isRepoLayer(layer):
    return getTrackingInfo(layer) is not None

def getTrackingInfo(layer):
    source = formatSource(layer)
    for obj in tracked:
        if obj.source == source:
            return obj

def getTrackingInfoForGeogigLayer(repoUrl, layername):
    for t in tracked:
        if (t.repoUrl == repoUrl and t.layername == layername):
            return t

def getTrackedPathsForRepo(repo):
    repoLayers = repo.trees()
    trackedPaths = [layer.source for layer in tracked
                if repo.url == layer.repoUrl and layer.layername in repoLayers]
    return trackedPaths

def updateTrackedLayers(repo):
    head = repo.revparse(geogig.HEAD)
    repoLayers = [tree.path for tree in repo.trees]
    repoLayersInProject = False
    notLoaded = []
    toUnload = []
    for trackedlayer in tracked:
        if trackedlayer.repoUrl == repo.url:
            if trackedlayer.layername in repoLayers:
                if (trackedlayer.ref != head
                            or not os.path.exists(trackedlayer.source)):
                    repo.exportgeopkg(geogig.HEAD, trackedlayer.layername, trackedlayer.geopkg)
                    try:
                        layer = resolveLayerFromSource(trackedlayer.source)
                        layer.reload()
                        layer.triggerRepaint()
                        repoLayersInProject = True
                    except WrongLayerSourceException:
                        notLoaded.append(trackedlayer)
                    trackedlayer.ref = head
                else:
                    try:
                        layer = resolveLayerFromSource(trackedlayer.source)
                        repoLayersInProject = True
                    except WrongLayerSourceException:
                        notLoaded.append(trackedlayer)
            else:
                try:
                    layer = resolveLayerFromSource(trackedlayer.source)
                    toUnload.append(layer)
                except WrongLayerSourceException:
                    pass
    saveTracked()
    if repoLayersInProject:
        if notLoaded:
            ret = QtGui.QMessageBox.warning(config.iface.mainWindow(), "Update layers",
                        "The current QGIS project only contains certain layers from the\n"
                        "current version of the repository.\n"
                        "Do you want to load the remaining ones?",
                        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                        QtGui.QMessageBox.Yes);
            if ret == QtGui.QMessageBox.Yes:
                layersToLoad = []
                for layer in notLoaded:
                    layersToLoad.append(loadLayerNoCrsDialog(layer.source, layer.layername, "ogr"))
                QgsMapLayerRegistry.instance().addMapLayers(layersToLoad)
        if toUnload:
            ret = QtGui.QMessageBox.warning(config.iface.mainWindow(), "Update layers",
                        "The following layers are not present anymore in the repository:\n"
                        "\t- " + "\n\t- ".join([layer.name() for layer in toUnload]) +
                        "\nDo you want to remove them from the current QGIS project?",
                        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                        QtGui.QMessageBox.Yes);
            if ret == QtGui.QMessageBox.Yes:
                for layer in toUnload:
                    QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
        config.iface.mapCanvas().refresh()

def formatSource(obj):
    if isinstance(obj, QgsVectorLayer):
        if obj.dataProvider().name() == "postgres":
            uri = QgsDataSourceURI(obj.dataProvider().dataSourceUri())
            return " ".join([uri.database(), uri.schema(), uri.table()])
        else:
            return os.path.normcase(obj.source())
    else:
        return os.path.normcase(unicode(obj))



