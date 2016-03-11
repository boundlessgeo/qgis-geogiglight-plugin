from qgis.core import *
from qgis.gui import *
from PyQt4 import QtGui, QtCore
from geogig.tools.layers import *
import os
from geogigpy.geogigexception import GeoGigException, UnconfiguredUserException
from geogigpy import geogig
from geogig.gui.dialogs.userconfigdialog import configureUser
from geogig.tools.layertracking import addTrackedLayer, isRepoLayer
from geogig.tools.utils import *
from geogig.tools.gpkgsync import addGeoGigTablesAndTriggers
from geogig.geogigwebapi import repository

class ImportDialog(QtGui.QDialog):

    def __init__(self, parent, repo = None, layer = None):
        super(ImportDialog, self).__init__(parent)
        self.repo = repo
        self.layer = layer
        self.ok = False
        self.initGui()

    def initGui(self):
        self.setWindowTitle('Add layer to GeoGig repository')
        verticalLayout = QtGui.QVBoxLayout()

        if self.repo is None:
            repos = repository.repos
            self.repos = {r.title:r.url for r in repos.values()}
            layerLabel = QtGui.QLabel('Repository')
            verticalLayout.addWidget(layerLabel)
            self.repoCombo = QtGui.QComboBox()
            self.repoCombo.addItems(self.repos.keys())
            verticalLayout.addWidget(self.repoCombo)
        if self.layer is None:
            layerLabel = QtGui.QLabel('Layer')
            verticalLayout.addWidget(layerLabel)
            self.layerCombo = QtGui.QComboBox()
            layerNames = [layer.name() for layer in getVectorLayers()
                          if layer.source().lower().split("|")[0].split(".")[-1] in["gpkg", "geopkg"]
                          and not isRepoLayer(layer)]
            self.layerCombo.addItems(layerNames)
            verticalLayout.addWidget(self.layerCombo)

        messageLabel = QtGui.QLabel('Message to describe this update')
        verticalLayout.addWidget(messageLabel)

        self.messageBox = QtGui.QPlainTextEdit()
        self.messageBox.textChanged.connect(self.messageHasChanged)
        verticalLayout.addWidget(self.messageBox)

        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
        self.importButton = QtGui.QPushButton("Add layer")
        self.importButton.clicked.connect(self.importClicked)
        self.importButton.setEnabled(False)
        self.buttonBox.addButton(self.importButton, QtGui.QDialogButtonBox.ApplyRole)
        self.buttonBox.rejected.connect(self.cancelPressed)
        verticalLayout.addWidget(self.buttonBox)

        self.setLayout(verticalLayout)

        self.resize(400, 200)

    def messageHasChanged(self):
        self.importButton.setEnabled(self.messageBox.toPlainText() != "")


    def importClicked(self):
        if self.repo is None:
            connector = PyQtConnectorDecorator()
            connector.checkIsAlive()
            self.repo = Repository(self.repos[self.repoCombo.currentText()], connector)
        if self.layer is None:
            text = self.layerCombo.currentText()
            self.layer = resolveLayer(text)

        addGeoGigTablesAndTriggers(self.layer)
        source = self.layer.source()
        filename, layername = source.split("|")
        layername = layername.split("=")[-1]
        self.repo.importgeopkg(filename, layername, layername)
        message = self.messageBox.toPlainText()
        self.repo.add()
        try:
            self.repo.commit(message)
        except UnconfiguredUserException, e:
            configureUser()
            self.repo.commit(message)
        except GeoGigException, e:
            if "Nothing to commit" in e.args[0]:
                    config.iface.messageBar().pushMessage("No version has been created. Repository is already up to date",
                                                          level = QgsMessageBar.INFO, duration = 4)
            self.close()
            return
        except:
            self.close()
            raise

        self.repo.exportgeopkg(geogig.HEAD, layername, filename, overwrite = True)

        ref = self.repo.revparse(geogig.HEAD)
        addTrackedLayer(source, self.repo.url, self.layer.name(), ref)
        self.ok = True
        config.iface.messageBar().pushMessage("Layer was correctly added to repository",
                                                  level = QgsMessageBar.INFO, duration = 4)
        self.close()


    def cancelPressed(self):
        self.close()
