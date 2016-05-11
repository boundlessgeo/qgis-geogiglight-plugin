# -*- coding: utf-8 -*-

"""
***************************************************************************
    remotesdialog.py
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class RemotesDialog(QtGui.QDialog):
    def __init__(self, parent, repo):
        QtGui.QDialog.__init__(self, parent, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.changed = False
        self.repo = repo
        self.remotes = repo.remotes
        self.setupUi()

    def setupUi(self):
        self.resize(500, 350)
        self.setWindowTitle("Remotes manager")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setMargin(0)
        self.buttonBox = QtGui.QDialogButtonBox()
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Close)
        self.table = QtGui.QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.addRowButton = QtGui.QPushButton()
        self.addRowButton.setText("Add remote")
        self.editRowButton = QtGui.QPushButton()
        self.editRowButton.setText("Edit remote")
        self.removeRowButton = QtGui.QPushButton()
        self.removeRowButton.setText("Remove remote")
        self.buttonBox.addButton(self.addRowButton, QtGui.QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.editRowButton, QtGui.QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.removeRowButton, QtGui.QDialogButtonBox.ActionRole)
        self.setTableContent()
        self.horizontalLayout.addWidget(self.table)
        self.horizontalLayout.addWidget(self.buttonBox)
        self.setLayout(self.horizontalLayout)

        self.buttonBox.rejected.connect(self.close)
        self.editRowButton.clicked.connect(self.editRow)
        self.addRowButton.clicked.connect(self.addRow)
        self.removeRowButton.clicked.connect(self.removeRow)

        QtCore.QMetaObject.connectSlotsByName(self)
        self.editRowButton.setEnabled(False)
        self.removeRowButton.setEnabled(False)

    def setTableContent(self):
        self.table.clear()
        self.table.setColumnCount(2)
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 200)
        self.table.setHorizontalHeaderLabels(["Name", "URL"])
        self.table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.table.setRowCount(len(self.remotes))
        for i, name in enumerate(self.remotes):
            url = self.remotes[name]
            self.table.setRowHeight(i, 22)
            item = QtGui.QTableWidgetItem(name, 0)
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.table.setItem(i, 0, item)
            item = QtGui.QTableWidgetItem(url, 0)
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.table.setItem(i, 1, item)

        self.table.itemSelectionChanged.connect(self.selectionChanged)

    def selectionChanged(self):
        enabled = len(self.table.selectedItems()) > 0
        self.editRowButton.setEnabled(enabled)
        self.removeRowButton.setEnabled(enabled)

    def editRow(self):
        item = self.table.item(self.table.currentRow(), 0)
        if item is not None:
            name = item.text()
            url = self.table.item(self.table.currentRow(), 1).text()
            dlg = NewRemoteDialog(name, url, self)
            dlg.exec_()
            if dlg.ok:
                self.repo.removeremote(name)
                self.repo.addremote(dlg.name, dlg.url, dlg.username, dlg.password)
                del self.remotes[name]
                self.remotes[dlg.name] = dlg.url
                self.setTableContent()
                self.changed = True



    def removeRow(self):
        item = self.table.item(self.table.currentRow(), 0)
        if item is not None:
            name = item.text()
            self.repo.removeremote(name)
            del self.remotes[name]
            self.setTableContent()
            self.changed = True

    def addRow(self):
        dlg = NewRemoteDialog(parent = self)
        dlg.exec_()
        if dlg.ok:
            self.repo.addremote(dlg.name, dlg.url, dlg.username, dlg.password)
            self.remotes[dlg.name] = dlg.url
            self.setTableContent()
            self.changed = True


class NewRemoteDialog(QtGui.QDialog):

    def __init__(self, name = None, url = None, parent = None):
        super(NewRemoteDialog, self).__init__(parent)
        self.ok = False
        self.name = name
        self.url = url
        self.initGui()

    def initGui(self):
        self.setWindowTitle('New remote')
        layout = QtGui.QVBoxLayout()
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Close)

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        nameLabel = QtGui.QLabel('Name')
        nameLabel.setMinimumWidth(120)
        nameLabel.setMaximumWidth(120)
        self.nameBox = QtGui.QLineEdit()
        if self.name is not None:
            self.nameBox.setText(self.name)
        horizontalLayout.addWidget(nameLabel)
        horizontalLayout.addWidget(self.nameBox)
        layout.addLayout(horizontalLayout)

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        urlLabel = QtGui.QLabel('URL')
        urlLabel.setMinimumWidth(120)
        urlLabel.setMaximumWidth(120)
        self.urlBox = QtGui.QLineEdit()
        if self.url is not None:
            self.urlBox.setText(self.url)
        horizontalLayout.addWidget(urlLabel)
        horizontalLayout.addWidget(self.urlBox)
        layout.addLayout(horizontalLayout)

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        usernameLabel = QtGui.QLabel('Username')
        usernameLabel.setMinimumWidth(120)
        usernameLabel.setMaximumWidth(120)
        self.usernameBox = QtGui.QLineEdit()
        horizontalLayout.addWidget(usernameLabel)
        horizontalLayout.addWidget(self.usernameBox)
        layout.addLayout(horizontalLayout)

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        passwordLabel = QtGui.QLabel('Password')
        passwordLabel.setMinimumWidth(120)
        passwordLabel.setMaximumWidth(120)
        self.passwordBox = QtGui.QLineEdit()
        self.passwordBox.setEchoMode(QtGui.QLineEdit.Password)
        horizontalLayout.addWidget(passwordLabel)
        horizontalLayout.addWidget(self.passwordBox)
        layout.addLayout(horizontalLayout)

        layout.addWidget(buttonBox)
        self.setLayout(layout)

        buttonBox.accepted.connect(self.okPressed)
        buttonBox.rejected.connect(self.cancelPressed)

        self.resize(400, 200)

    def okPressed(self):
        self.name = unicode(self.nameBox.text())
        self.url = unicode(self.urlBox.text())
        self.username = unicode(self.usernameBox.text()).strip() or None
        self.password = unicode(self.passwordBox.text()).strip() or None
        self.ok = True
        self.close()

    def cancelPressed(self):
        self.name = None
        self.url = None
        self.close()
