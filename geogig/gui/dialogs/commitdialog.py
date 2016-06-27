# -*- coding: utf-8 -*-

"""
***************************************************************************
    commitdialog.py
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

class CommitDialog(QtGui.QDialog):

    def __init__(self, repo, parent = None):
        super(CommitDialog, self).__init__(parent)
        self.repo = repo
        self.message = None
        self._closing = False
        self.initGui()

    def initGui(self):
        self.resize(600, 250)
        self.setWindowTitle('GeoGig')

        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setMargin(5)

        self.msgLabel = QtGui.QLabel("Message to describe this update")
        self.verticalLayout.addWidget(self.msgLabel)

        self.text = QtGui.QPlainTextEdit()
        self.verticalLayout.addWidget(self.text)

        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(False)
        self.setLayout(self.verticalLayout)

        self.buttonBox.accepted.connect(self.okPressed)

        self.text.textChanged.connect(self.textHasChanged)
        if self.repo.ismerging():
            self.text.setPlainText(self.repo.mergemessage())

    def textHasChanged(self):
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(self.text.toPlainText() != "")

    def okPressed(self):
        self.message = self.text.toPlainText()
        self.close()



