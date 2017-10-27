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


from qgis.PyQt.QtWidgets import (QDialog,
                                 QVBoxLayout,
                                 QHBoxLayout,
                                 QLabel,
                                 QComboBox,
                                 QGroupBox,
                                 QDialogButtonBox,
                                 QMessageBox
                                )
from geogig.geogigwebapi.repository import Repository


class RemoteRefDialog(QDialog):

    def __init__(self, repo, parent = None):
        super(RemoteRefDialog, self).__init__(parent)
        self.remote = None
        self.branch = None
        self.repo = repo
        self.initGui()

    def initGui(self):
        self.setWindowTitle('Remote connection reference')
        verticalLayout = QVBoxLayout()

        horizontalLayout = QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        remoteLabel = QLabel('Remote connection')
        self.remoteCombo = QComboBox()
        self.remotes = self.repo.remotes()
        self.remoteCombo.addItems(list(self.remotes.keys()))
        self.remoteCombo.currentIndexChanged.connect(self.currentRemoteChanged)
        horizontalLayout.addWidget(remoteLabel)
        horizontalLayout.addWidget(self.remoteCombo)
        verticalLayout.addLayout(horizontalLayout)

        horizontalLayout = QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        branchLabel = QLabel('Branch')
        self.branchCombo = QComboBox()
        self.branchCombo.addItems(self.repo.branches())
        horizontalLayout.addWidget(branchLabel)
        horizontalLayout.addWidget(self.branchCombo)
        verticalLayout.addLayout(horizontalLayout)

        self.groupBox = QGroupBox()
        self.groupBox.setTitle("Remote connection info")
        self.groupBox.setLayout(verticalLayout)

        layout = QVBoxLayout()
        layout.addWidget(self.groupBox)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
        self.branchCombo.clear()
        self.branchCombo.addItems(branches)

    def okPressed(self):
        remote = self.remoteCombo.currentText().strip()
        if remote:
            self.remote = remote
        else:
            QMessageBox.warning(self, "Missing value", "Please select a remote connection")
            return
        branch = self.branchCombo.currentText().strip()
        if branch:
            self.branch = branch
        else:
            QMessageBox.warning(self, "Missing value", "Please select a branch")
            return
        self.close()

    def cancelPressed(self):
        self.remote = None
        self.branch = None
        self.close()
