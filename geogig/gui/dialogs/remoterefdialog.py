# -*- coding: utf-8 -*-

"""
***************************************************************************
    remoteref.py
    ---------------------
    Date                 : August 2016
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
__date__ = 'August 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from PyQt4 import QtGui
from geogig.geogigwebapi.repository import Repository

class RemoteRefDialog(QtGui.QDialog):

    def __init__(self, repo, parent = None):
        super(RemoteRefDialog, self).__init__(parent)
        self.remote = None
        self.branch = None
        self.repo = repo
        self.initGui()

    def initGui(self):
        self.setWindowTitle('Remote reference')
        verticalLayout = QtGui.QVBoxLayout()

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        remoteLabel = QtGui.QLabel('Remote')
        self.remoteCombo = QtGui.QComboBox()
        self.remotes = self.repo.remotes()
        self.remoteCombo.addItems(self.remotes.keys())
        self.remoteCombo.currentIndexChanged.connect(self.currentRemoteChanged)
        horizontalLayout.addWidget(remoteLabel)
        horizontalLayout.addWidget(self.remoteCombo)
        verticalLayout.addLayout(horizontalLayout)

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        branchLabel = QtGui.QLabel('Branch')
        self.branchCombo = QtGui.QComboBox()
        self.branchCombo.addItems(self.repo.branches())
        horizontalLayout.addWidget(branchLabel)
        horizontalLayout.addWidget(self.branchCombo)
        verticalLayout.addLayout(horizontalLayout)

        self.groupBox = QtGui.QGroupBox()
        self.groupBox.setTitle("Remote info")
        self.groupBox.setLayout(verticalLayout)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.groupBox)

        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

        self.buttonBox.accepted.connect(self.okPressed)
        self.buttonBox.rejected.connect(self.cancelPressed)

        self.resize(400, 200)

    def currentRemoteChanged(self):
        remote = self.remoteCombo.currentText()
        repo = Repository(self.remotes[remote])
        #TODO handle case of remote not being available
        branches = repo.branches()
        self.branchesCombo.clear()
        self.branchesCombo.addItems(branches)

    def okPressed(self):
        remote = self.remoteCombo.currentText().strip()
        if remote:
            self.remote = remote
        else:
            QtGui.QMessageBox.warning(self, "Missing value", "Please select a remote")
            return
        branch = self.branchCombo.currentText().strip()
        if branch:
            self.branch = branch
        else:
            QtGui.QMessageBox.warning(self, "Missing value", "Please select a branch")
            return
        self.close()

    def cancelPressed(self):
        self.remote = None
        self.branch = None
        self.close()
