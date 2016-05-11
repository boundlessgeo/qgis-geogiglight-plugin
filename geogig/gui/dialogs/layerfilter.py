# -*- coding: utf-8 -*-

"""
***************************************************************************
    layerfilter.py
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


from PyQt4 import QtCore, QtGui
from PyQt4.Qt import QListWidget

class LayersFilterDialog(QtGui.QDialog):

    filterTextChanged = QtCore.pyqtSignal()
    filterLayersChanged = QtCore.pyqtSignal()

    def __init__(self, layers, widget, parent):
        super(LayersFilterDialog, self).__init__(parent)
        self.checkBox = []
        self.layers = layers
        self.widget = widget
        self.filterLayers = None
        self.filterText = ""
        self.initGui()
        self.setLayers(layers)

    def initGui(self):
        layout = QtGui.QVBoxLayout()
        self.label = QtGui.QLabel("<b>Filter by layer</b>")
        layout.addWidget(self.label)
        self.layersList = QListWidget()
        layout.addWidget(self.layersList)
        self.label = QtGui.QLabel("<b>Filter by text</b>")
        layout.addWidget(self.label)
        self.text = QtGui.QLineEdit()
        layout.addWidget(self.text)
        self.button = QtGui.QPushButton("Apply")
        self.button.clicked.connect(self.apply)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup)
        self.resize(200, 150)

    def show(self):
        self.computeLocation()
        QtGui.QDialog.show(self)

    def computeLocation(self):
        point = self.widget.rect().bottomRight()
        global_point = self.widget.mapToGlobal(point)
        self.move(global_point)


    def setLayers(self, layers):
        for layer in layers:
            item = QtGui.QListWidgetItem(layer)
            item.setCheckState(QtCore.Qt.Checked)
            self.layersList.addItem(item)
        self.filterLayers = None

    def setFilterLayers(self, layers):
        for i in xrange(self.layersList.count()):
            item = self.layersList.item(i)
            item.setCheckState(QtCore.Qt.Checked if layers is None or item.text() in layers
                                else QtCore.Qt.Unchecked)

    def setFilterText(self, text):
        self.text.setText(text)

    def apply(self):
        filterLayers = []
        for i in xrange(self.layersList.count()):
            item = self.layersList.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                filterLayers.append(item.text())
        if len(filterLayers) == self.layersList.count():
            filterLayers = None
        if filterLayers != self.filterLayers:
            self.filterLayers = filterLayers
            self.filterLayersChanged.emit()
        filterText = self.text.text()
        if filterText != self.filterText:
            self.filterText = filterText
            self.filterTextChanged.emit()
        self.hide()
