# -*- coding: utf-8 -*-

"""
***************************************************************************
    importdialog.py
    ---------------------
    Date                 : March 2016
    Copyright            : (C) 2016 Boundless, http://boundlessgeo.com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from PyQt4 import QtGui
from geogig.tools.layers import *
import os
from geogig import config
from geogig.tools.layertracking import addTrackedLayer, isRepoLayer
from geogig.tools.utils import *
from geogig.geogigwebapi import repository
from geogig.geogigwebapi.repository import GeoGigException
from geogig.tools.gpkgsync import getCommitId


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
            layerLabel = QtGui.QLabel('Repository')
            verticalLayout.addWidget(layerLabel)
            self.repoCombo = QtGui.QComboBox()
            self.repoCombo.addItems(["%s - %s" % (r.group, r.title) for r in repos])
            self.repoCombo.currentIndexChanged.connect(self.updateBranches)
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

        self.branchLabel = QtGui.QLabel("Branch")
        verticalLayout.addWidget(self.branchLabel)

        self.branchCombo = QtGui.QComboBox()
        self.branches = self.repo.branches() if self.repo is not None else repos[0].branches()
        self.branchCombo.addItems(self.branches)
        verticalLayout.addWidget(self.branchCombo)

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

        self.resize(600, 300)

    def updateBranches(self):
        self.branchCombo.clear()
        repo = repository.repos[self.repoCombo.currentIndex()]
        self.branches = repo.branches()
        self.branchCombo.addItems(self.branches)

    def messageHasChanged(self):
        self.importButton.setEnabled(self.messageBox.toPlainText() != "")


    def importClicked(self):
        if self.repo is None:
            self.repo = repository.repos[self.repoCombo.currentIndex()]
        if self.layer is None:
            text = self.layerCombo.currentText()
            self.layer = resolveLayer(text)

        user, email = config.getUserInfo()
        if user is None:
            self.close()
            return
        message = self.messageBox.toPlainText()

        branch = self.branchCombo.currentText()
        try:
            self.repo.importgeopkg(self.layer, branch, message, user, email, False)
            filename, layername = namesFromLayer(self.layer)
            self.repo.checkoutlayer(filename, layername)
            self.layer.reload()
            self.layer.triggerRepaint()
        except GeoGigException, e:
            iface.messageBar().pushMessage("Error", str(e), level=QgsMessageBar.CRITICAL)
            self.close()
            return

        addTrackedLayer(self.layer, self.repo.url)

        self.ok = True
        iface.messageBar().pushMessage("Layer was correctly added to repository",
                                       level=QgsMessageBar.INFO,
                                       duration=4)
        self.close()


    def cancelPressed(self):
        self.close()
