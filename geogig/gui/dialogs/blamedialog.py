# -*- coding: utf-8 -*-

"""
***************************************************************************
    blamedialog.py
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

from geogig.geogigwebapi.repository import GeoGigException
from PyQt4 import QtCore, QtGui

class BlameDialog(QtGui.QDialog):
    def __init__(self, repo, path):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        versions = repo.log(path = path, limit = 1)
        if not versions:
            raise GeoGigException("The selected feature is not versioned yet")
        self.blamedata = repo.blame(path)
        self.repo = repo
        self.commitText = {}
        self.setupUi()

    def setupUi(self):
        self.resize(800, 600)
        self.setWindowTitle("Authorship")
        layout = QtGui.QVBoxLayout()
        splitter = QtGui.QSplitter(self)
        splitter.setOrientation(QtCore.Qt.Vertical)
        self.table = QtGui.QTableWidget(splitter)
        self.table.setColumnCount(3)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.setHorizontalHeaderLabels(["Attribute", "Author", "Value"])
        self.table.setRowCount(len(self.blamedata))
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection);
        self.table.selectionModel().selectionChanged.connect(self.selectionChanged)
        for i, name in enumerate(self.blamedata.keys()):
            values = self.blamedata[name]
            self.table.setItem(i, 0, QtGui.QTableWidgetItem(name));
            self.table.setItem(i, 1, QtGui.QTableWidgetItem(values[1].authorname));
            self.table.setItem(i, 2, QtGui.QTableWidgetItem(values[0]));
        self.table.resizeRowsToContents()
        self.table.horizontalHeader().setMinimumSectionSize(250)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.text = QtGui.QTextBrowser(splitter)
        layout.addWidget(splitter)
        self.setLayout(layout)
        QtCore.QMetaObject.connectSlotsByName(self)

    def selectionChanged(self):
        idx = self.table.currentRow()
        commit = self.blamedata[self.table.item(idx, 0).text()][1]
        self.text.setText(str(commit))


