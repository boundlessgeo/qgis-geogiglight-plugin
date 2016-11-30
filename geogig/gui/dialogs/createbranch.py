# -*- coding: utf-8 -*-

"""
***************************************************************************
    createbranch.py
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


from PyQt4.QtGui import (QDialog,
                         QVBoxLayout,
                         QDialogButtonBox,
                         QHBoxLayout,
                         QLabel,
                         QLineEdit,
                         QCheckBox
                        )


class CreateBranchDialog(QDialog):

    def __init__(self, parent = None):
        super(CreateBranchDialog, self).__init__(parent)
        self.ok = False
        self.initGui()

    def initGui(self):
        self.setWindowTitle("Create branch")
        layout = QVBoxLayout()
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setMargin(0)

        horizontalLayout = QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        nameLabel = QLabel('Branch name')
        self.nameBox = QLineEdit()
        horizontalLayout.addWidget(nameLabel)
        horizontalLayout.addWidget(self.nameBox)

        horizontalLayout2 = QHBoxLayout()
        horizontalLayout2.setSpacing(30)
        horizontalLayout2.setMargin(20)
        self.forceCheck = QCheckBox('Force')
        horizontalLayout2.addWidget(self.forceCheck)
        self.checkoutCheck = QCheckBox('Switch to branch after creating it')
        horizontalLayout2.addWidget(self.checkoutCheck)

        layout.addLayout(horizontalLayout)
        layout.addLayout(horizontalLayout2)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        buttonBox.accepted.connect(self.okPressed)
        buttonBox.rejected.connect(self.cancelPressed)

        self.resize(400, 150)

    def getName(self):
        return str(self.nameBox.text())

    def isForce(self):
        return self.force

    def isCheckout(self):
        return self.checkout

    def okPressed(self):
        self.force = self.forceCheck.isChecked()
        self.checkout = self.checkoutCheck.isChecked()
        self.ok = True
        self.close()

    def cancelPressed(self):
        self.ok = False
        self.close()
