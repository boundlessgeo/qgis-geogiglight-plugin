# -*- coding: utf-8 -*-

"""
***************************************************************************
    geogigerrordialog.py
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


import os
from PyQt4 import QtGui
from qgis.utils import pluginMetadata

class GeoGigErrorDialog(QtGui.QDialog):

    def __init__(self, trace, parent = None):
        super(GeoGigErrorDialog, self).__init__(parent)
        pluginVersion = "Plugin version: " + pluginMetadata("geogig", "version")
        self.trace = "\n".join([pluginVersion, trace])
        QtGui.QApplication.restoreOverrideCursor()
        self.initGui()

    def initGui(self):
        self.resize(400, 100)
        self.setWindowTitle('Error')

        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setMargin(10)

        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setMargin(10)

        self.msgLabel = QtGui.QLabel(
                                     "An unexpected error has occurred while executing the GeoGig client plugin.")
        self.imgLabel = QtGui.QLabel()
        self.imgLabel.setPixmap(QtGui.QPixmap(os.path.join(os.path.dirname(__file__), "..", "..", "ui", "resources", "error.png")))
        self.horizontalLayout.addWidget(self.imgLabel)
        self.horizontalLayout.addWidget(self.msgLabel)

        self.verticalLayout.addLayout(self.horizontalLayout)
        self.text = QtGui.QPlainTextEdit()
        self.text.setVisible(False)
        self.text.setPlainText(self.trace)
        self.verticalLayout.addWidget(self.text)
        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        self.showTraceButton = QtGui.QPushButton()
        self.showTraceButton.setText("Show error trace")
        self.showTraceButton.clicked.connect(self.showTracePressed)
        self.buttonBox.addButton(self.showTraceButton, QtGui.QDialogButtonBox.ActionRole)

        self.verticalLayout.addWidget(self.buttonBox)
        self.setLayout(self.verticalLayout)

        self.buttonBox.rejected.connect(self.closePressed)

    def closePressed(self):
        self.close()

    def showTracePressed(self):
        if self.text.isVisible():
            self.showTraceButton.setText("Show error trace")
            self.text.setVisible(False)
            self.resize(400, 100)
        else:
            self.resize(400, 400)
            self.text.setVisible(True)
            self.showTraceButton.setText("Hide error trace")

