# -*- coding: utf-8 -*-

"""
***************************************************************************
    configdialog.py
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
from PyQt4.QtCore import Qt, QSettings
from PyQt4.QtGui import (QDialog,
                         QIcon,
                         QVBoxLayout,
                         QTreeWidget,
                         QDialogButtonBox,
                         QTreeWidgetItem,
                         QTreeWidgetItemIterator,
                         QHBoxLayout,
                         QLineEdit,
                         QLabel,
                         QSizePolicy,
                         QFileDialog,
                         QWidget
                        )
from qgis.gui import QgsFilterLineEdit
from geogig import config


class ConfigDialog(QDialog):

    versioIcon = QIcon(os.path.dirname(__file__) + "/../../ui/resources/geogig-16.png")

    def __init__(self):
        QDialog.__init__(self)
        self.setupUi()
        if hasattr(self.searchBox, 'setPlaceholderText'):
            self.searchBox.setPlaceholderText(self.tr("Search..."))
        self.searchBox.textChanged.connect(self.filterTree)
        self.fillTree()

    def setupUi(self):
        self.resize(640, 450)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setMargin(0)
        self.searchBox = QgsFilterLineEdit(self)
        self.verticalLayout.addWidget(self.searchBox)
        self.tree = QTreeWidget(self)
        self.tree.setAlternatingRowColors(True)
        self.verticalLayout.addWidget(self.tree)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)

        self.setWindowTitle("Configuration options")
        self.searchBox.setToolTip("Enter setting name to filter list")
        self.tree.headerItem().setText(0, "Setting")
        self.tree.headerItem().setText(1, "Value")

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.setLayout(self.verticalLayout)

    def filterTree(self):
        text = unicode(self.searchBox.text())
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            visible = False
            for j in range(item.childCount()):
                subitem = item.child(j)
                itemText = subitem.text(0)
            if (text.strip() == ""):
                subitem.setHidden(False)
                visible = True
            else:
                hidden = text not in itemText
                item.setHidden(hidden)
                visible = visible or not hidden
            item.setHidden(not visible)
            item.setExpanded(visible and text.strip() != "")

    def fillTree(self):
        self.items = {}
        self.tree.clear()

        generalItem = self._getItem(config.GENERAL, self.versioIcon, config.generalParams)
        self.tree.addTopLevelItem(generalItem)
        self.tree.setColumnWidth(0, 400)


    def _getItem(self, name, icon, params):
        item = QTreeWidgetItem()
        item.setText(0, name)
        item.setIcon(0, icon)
        for param in params:
            paramName = "/GeoGig/Settings/" + name + "/" + param[0]
            subItem = TreeSettingItem(self.tree, item, paramName, *param[1:])
            item.addChild(subItem)
        return item

    def accept(self):
        iterator = QTreeWidgetItemIterator(self.tree)
        value = iterator.value()
        while value:
            if hasattr(value, 'checkValue'):
                if value.checkValue():
                    value.setBackgroundColor(1, Qt.white)
                else:
                    value.setBackgroundColor(1, Qt.yellow)
                    return

            iterator += 1
            value = iterator.value()
        iterator = QTreeWidgetItemIterator(self.tree)
        value = iterator.value()
        while value:
            if hasattr(value, 'saveValue'):
                value.saveValue()
            iterator += 1
            value = iterator.value()
        QDialog.accept(self)


class TreeSettingItem(QTreeWidgetItem):

    def __init__(self, tree, parent, name, description, defaultValue, paramType, check):
        QTreeWidgetItem.__init__(self, parent)
        self.parent = parent
        self.name = name
        self.check = check
        self.paramType = paramType
        self.setText(0, description)
        self.tree = tree
        if paramType == config.TYPE_FOLDER:
            self.value = QSettings().value(name, defaultValue = defaultValue)
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            self.lineEdit = QLineEdit()
            self.lineEdit.setText(self.value)
            self.label = QLabel()
            self.label.setText("<a href='#'> Browse</a>")
            self.lineEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(self.lineEdit)
            layout.addWidget(self.label)
            def edit():
                folder = QFileDialog.getExistingDirectory(tree, description, self.value)
                if folder:
                    self.lineEdit.setText(folder)
            self.label.linkActivated.connect(edit)
            w = QWidget()
            w.setLayout(layout)
            self.tree.setItemWidget(self, 1, w)
        elif isinstance(defaultValue, bool):
            self.value = QSettings().value(name, defaultValue = defaultValue, type = bool)
            if self.value:
                self.setCheckState(1, Qt.Checked)
            else:
                self.setCheckState(1, Qt.Unchecked)
        else:
            self.value = QSettings().value(name, defaultValue = defaultValue)
            self.setFlags(self.flags() | Qt.ItemIsEditable)
            self.setText(1, unicode(self.value))

    def getValue(self):
        if self.paramType == config.TYPE_FOLDER:
            return self.lineEdit.text()
        elif isinstance(self.value, bool):
            return self.checkState(1) == Qt.Checked
        else:
            return self.text(1)

    def saveValue(self):
        self.value = self.getValue()
        QSettings().setValue(self.name, self.value)

    def checkValue(self):
        try:
            return self.check(self.getValue())
        except:
            return False
