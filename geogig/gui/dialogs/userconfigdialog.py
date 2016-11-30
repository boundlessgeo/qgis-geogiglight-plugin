# -*- coding: utf-8 -*-

"""
***************************************************************************
    userconfigdialog.py
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
from builtins import str

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from qgis.PyQt.QtWidgets import (QDialog,
                                 QVBoxLayout,
                                 QHBoxLayout,
                                 QLabel,
                                 QLineEdit,
                                 QGroupBox,
                                 QDialogButtonBox
                                )


class UserConfigDialog(QDialog):

    def __init__(self, parent = None):
        super(UserConfigDialog, self).__init__(parent)
        self.user = None
        self.email = None
        self.initGui()

    def initGui(self):
        self.setWindowTitle('GeoGig user configuration')
        verticalLayout = QVBoxLayout()

        horizontalLayout = QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        usernameLabel = QLabel('Username')
        self.usernameBox = QLineEdit()
        horizontalLayout.addWidget(usernameLabel)
        horizontalLayout.addWidget(self.usernameBox)
        verticalLayout.addLayout(horizontalLayout)

        horizontalLayout = QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        emailLabel = QLabel('User email')
        self.emailBox = QLineEdit()
        horizontalLayout.addWidget(emailLabel)
        horizontalLayout.addWidget(self.emailBox)
        verticalLayout.addLayout(horizontalLayout)

        self.groupBox = QGroupBox()
        self.groupBox.setTitle("User data")
        self.groupBox.setLayout(verticalLayout)

        layout = QVBoxLayout()
        layout.addWidget(self.groupBox)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

        self.buttonBox.accepted.connect(self.okPressed)
        self.buttonBox.rejected.connect(self.cancelPressed)

        self.resize(400, 200)

    def okPressed(self):
        self.user = str(self.usernameBox.text())
        self.email = str(self.emailBox.text())
        self.close()

    def cancelPressed(self):
        self.user = None
        self.email = None
        self.close()
