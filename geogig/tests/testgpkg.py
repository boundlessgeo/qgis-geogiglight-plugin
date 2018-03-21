import os
import unittest
import shutil

from osgeo import ogr

from qgis.utils import iface
from qgis.core import QgsProject, QgsFeature, QgsGeometry, QgsPoint

from geogig.extlibs.qgiscommons2.files import tempFilename
from geogig.extlibs.qgiscommons2.layers import loadLayerNoCrsDialog

class GeoPackageEditTests(unittest.TestCase):

    def _copyTestLayer(self):
        src = os.path.join(os.path.dirname(__file__), "data", "layers", "points.gpkg")
        dest = tempFilename("gpkg")
        shutil.copy(src, dest)
        return dest

    def _getQgisTestLayer(self):
        dest = self._copyTestLayer()
        iface.newProject()
        layer = loadLayerNoCrsDialog(dest, "points", "ogr")
        QgsProject.instance().addMapLayers([layer])
        return layer

    def _getOgrTestLayer(self):
        dest = self._copyTestLayer()
        driver = ogr.GetDriverByName('GPKG')
        dataSource = driver.Open(dest, 1)
        return dataSource

    def testAddingFeatureUsingQgisApi(self):
        layer =self._getQgisTestLayer()
        self.assertTrue(layer.startEditing())
        feat = QgsFeature(layer.pendingFields())
        feat.setAttributes([5, 5])
        layer.addFeatures([feat])
        iface.showAttributeTable(layer)
        feat.setGeometry(QgsGeometry.fromPoint(QgsPoint(123, 456)))
        self.assertTrue(layer.commitChanges())


    def testAddingFeatureUsingOgr(self):
        dataSource =self._getOgrTestLayer()
        layer = dataSource.GetLayer()
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(123, 456)
        featureDefn = layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        feature.SetGeometry(point)
        feature.SetField("fid", 5)
        feature.SetField("n", 5)
        layer.CreateFeature(feature)
        dataSource.Destroy()


    def testEditingGeometryUsingQgisApi(self):
        layer =self._getQgisTestLayer()
        self.assertTrue(layer.startEditing())
        features = list(layer.getFeatures())
        layer.changeGeometry(features[0].id(), QgsGeometry.fromPoint(QgsPoint(123, 456)))
        layer.changeAttributeValue(features[0].id(), 1, None)
        iface.showAttributeTable(layer)
        self.assertTrue(layer.commitChanges())
