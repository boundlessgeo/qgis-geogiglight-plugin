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

suggestedMessage = ""

class CommitDialog(QtGui.QDialog):

    def __init__(self, repo, _message = "", parent = None):
        super(CommitDialog, self).__init__(parent)
        self.repo = repo
        self.branch = None
        self._message = _message or suggestedMessage
        self.message = None
        self.initGui()

    def initGui(self):
        self.resize(600, 250)
        self.setWindowTitle('GeoGig')

        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setMargin(5)

        self.branchLabel = QtGui.QLabel("Branch (select a branch or type a name to create a new branch)")
        self.verticalLayout.addWidget(self.branchLabel)

        self.branchCombo = QtGui.QComboBox()
        self.branches = self.repo.branches()
        self.branchCombo.addItems(self.branches)
        self.branchCombo.setEditable(True)
        self.verticalLayout.addWidget(self.branchCombo)

        self.msgLabel = QtGui.QLabel("Message to describe this update")
        self.verticalLayout.addWidget(self.msgLabel)

        self.text = QtGui.QPlainTextEdit()
        self.text.setPlainText(self._message)
        self.text.textChanged.connect(self.textHasChanged)
        self.verticalLayout.addWidget(self.text)

        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)

        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(bool(self._message))

        self.setLayout(self.verticalLayout)
        self.buttonBox.accepted.connect(self.okPressed)


    def textHasChanged(self):
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(self.text.toPlainText() != "")

    def okPressed(self):
        self.branch = self.branchCombo.currentText()
        self.message = self.text.toPlainText()
        self.close()



