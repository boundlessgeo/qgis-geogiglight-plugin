from PyQt4 import QtGui, QtCore
from qgis.core import *
from qgis.gui import *
from geogig.ui.versionsviewer import Ui_VersionViewer
from geogig.gui.dialogs.geogigref import CommitListItem
from geogigpy.geogigexception import GeoGigException
from geogigpy.geometry import Geometry
from geogig import config
from geogig.tools.utils import loadLayerNoCrsDialog
import os

class VersionViewerDialog(QtGui.QDialog):

    def __init__(self, repo, path):
        QtGui.QDialog.__init__(self, config.iface.mainWindow(), QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.repo = repo
        self.path = path
        self.ui = Ui_VersionViewer()
        self.ui.setupUi(self)

        self.ui.listWidget.itemClicked.connect(self.commitClicked)

        settings = QtCore.QSettings()
        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(0)
        horizontalLayout.setMargin(0)
        self.mapCanvas = QgsMapCanvas()
        self.mapCanvas.setCanvasColor(QtCore.Qt.white)
        self.mapCanvas.enableAntiAliasing(settings.value("/qgis/enable_anti_aliasing", False, type = bool))
        self.mapCanvas.useImageToRender(settings.value("/qgis/use_qimage_to_render", False, type = bool))
        action = settings.value("/qgis/wheel_action", 0, type = float)
        zoomFactor = settings.value("/qgis/zoom_factor", 2, type = float)
        self.mapCanvas.setWheelAction(QgsMapCanvas.WheelAction(action), zoomFactor)
        horizontalLayout.addWidget(self.mapCanvas)
        self.ui.mapWidget.setLayout(horizontalLayout)
        self.panTool = QgsMapToolPan(self.mapCanvas)
        self.mapCanvas.setMapTool(self.panTool)

        versions = repo.log(path = path)
        if versions:
            for commit in versions:
                item = CommitListItem(commit, repo, path)
                self.ui.listWidget.addItem(item)
                ''''w = CommitListItemWidget(commit)
                self.ui.listWidget.setItemWidget(item, w)'''
        else:
            raise GeoGigException("The feature id (%s) cannot be found in the repository" % (path))


    def commitClicked(self):
        feature = self.ui.listWidget.currentItem().feature
        geom = None
        self.ui.attributesTable.setRowCount(len(feature))
        for idx, attrname in enumerate(feature):
            value = feature[attrname]
            font = QtGui.QFont()
            font.setBold(True)
            font.setWeight(75)
            item = QtGui.QTableWidgetItem(attrname)
            item.setFont(font)
            self.ui.attributesTable.setItem(idx, 0, item);
            self.ui.attributesTable.setItem(idx, 1, QtGui.QTableWidgetItem(unicode(value)));
            if geom is None:
                try:
                    geom = QgsGeometry.fromWkt(value)
                except:
                    pass

        self.ui.attributesTable.resizeRowsToContents()
        self.ui.attributesTable.horizontalHeader().setMinimumSectionSize(150)
        self.ui.attributesTable.horizontalHeader().setStretchLastSection(True)

        settings = QtCore.QSettings()
        prjSetting = settings.value('/Projections/defaultBehaviour')
        settings.setValue('/Projections/defaultBehaviour', '')
        types = ["Point", "LineString", "Polygon"]
        layers = []
        if geom is not None:
            geomtype = types[int(geom.type())]
            layer = loadLayerNoCrsDialog(geomtype + "?crs=EPSG:4326", "temp", "memory")
            pr = layer.dataProvider()
            feat = QgsFeature()
            feat.setGeometry(geom)
            pr.addFeatures([feat])
            layer.updateExtents()
            layer.selectAll()
            layer.setExtent(layer.boundingBoxOfSelected())
            layer.invertSelection()
            symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())
            symbol.setColor(QtCore.Qt.green)
            symbol.setAlpha(0.5)
            layer.setRendererV2(QgsSingleSymbolRendererV2(symbol))
            self.mapCanvas.setRenderFlag(False)
            self.mapCanvas.setLayerSet([QgsMapCanvasLayer(layer)])
            QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            self.mapCanvas.setExtent(layer.extent())
            self.mapCanvas.setRenderFlag(True)
            layers.append(layer)
        else:
            self.mapCanvas.setLayerSet([])
        settings.setValue('/Projections/defaultBehaviour', prjSetting)

class CommitListItemWidget(QtGui.QLabel):
    def __init__(self, commit):
        QtGui.QTextEdit.__init__(self)
        self.setWordWrap(False)
        self.commit = commit
        size = self.font().pointSize()
        text = ('<b><font style="font-size:%spt">%s</font></b>'
            '<br><font color="#5f6b77" style="font-size:%spt"><b>%s</b> by <b>%s</b></font> '
            '<font color="#5f6b77" style="font-size:%spt; background-color:rgb(225,225,225)"> %s </font>' %
            (str(size), self.commit.message.splitlines()[0], str(size - 1),
             self.commit.authorprettydate(), self.commit.authorname, str(size - 1), self.commit.id[:10]))
        self.setText(text)

class CommitListItem(QtGui.QListWidgetItem):

    icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "ui", "resources", "person.png"))

    def __init__(self, commit, repo, path):
        QtGui.QListWidgetItem.__init__(self)
        self.commit = commit
        self._feature = None
        self.repo = repo
        self.path = path
        self.setText("%s (by %s)" % (commit.message.splitlines()[0], commit.authorname))

    @property
    def feature(self):
        if self._feature is None:
            self._feature = self.repo.feature(self.path, self.commit)
        return self._feature


