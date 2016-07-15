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

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from PyQt4 import QtGui

class UserConfigDialog(QtGui.QDialog):

    def __init__(self, parent = None):
        super(UserConfigDialog, self).__init__(parent)
        self.user = None
        self.email = None
        self.initGui()

    def initGui(self):
        self.setWindowTitle('GeoGig user configuration')
        verticalLayout = QtGui.QVBoxLayout()

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        usernameLabel = QtGui.QLabel('Username')
        self.usernameBox = QtGui.QLineEdit()
        horizontalLayout.addWidget(usernameLabel)
        horizontalLayout.addWidget(self.usernameBox)
        verticalLayout.addLayout(horizontalLayout)

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        emailLabel = QtGui.QLabel('User email')
        self.emailBox = QtGui.QLineEdit()
        horizontalLayout.addWidget(emailLabel)
        horizontalLayout.addWidget(self.emailBox)
        verticalLayout.addLayout(horizontalLayout)

        self.groupBox = QtGui.QGroupBox()
        self.groupBox.setTitle("User data")
        self.groupBox.setLayout(verticalLayout)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.groupBox)

        self.debugGroupBox = QtGui.QGroupBox()
        self.debugGroupBox.setTitle("Debug")
        logLabel = QtGui.QLabel('Log all server calls')
        self.debugGroupBox.addWidget(logLabel)
        self.logCheckBox = QtGui.QCheckBox()
        self.debugGroupBox.addWidget(self.logCheckBox)
        self.debugGroupBox.setLayout(verticalLayout)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.groupBox)


        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

        self.buttonBox.accepted.connect(self.okPressed)
        self.buttonBox.rejected.connect(self.cancelPressed)

        self.resize(400, 200)

    def okPressed(self):
        self.user = unicode(self.usernameBox.text())
        self.email = unicode(self.emailBox.text())
        self.logCalls = self.logCheckBox.isChecked()
        self.close()

    def cancelPressed(self):
        self.user = None
        self.email = None
        self.logCalls = None
        self.close()
