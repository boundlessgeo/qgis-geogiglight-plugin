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


from qgis.PyQt.QtWidgets import (QDialog,
                                 QVBoxLayout,
                                 QLabel,
                                 QComboBox,
                                 QPlainTextEdit,
                                 QDialogButtonBox
                                )

from datetime import datetime

suggestedMessage = ""

class CommitDialog(QDialog):



    def __init__(self, repo, layername,  _message = "", parent = None):
        super(CommitDialog, self).__init__(parent)
        self.repo = repo
        self.branch = None
        self.layername = layername
        self._message = _message or suggestedMessage
        self.message = None
        self.initGui()

    def initGui(self):
        self.resize(600, 250)
        self.setWindowTitle("Syncronize layer to repository branch")

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setMargin(5)

        self.branchLabel = QLabel("Branch")
        self.verticalLayout.addWidget(self.branchLabel)

        self.branchCombo = QComboBox()
        self.branches = []
        branches = self.repo.branches()
        for branch in branches:
            trees = self.repo.trees(branch)
            if self.layername in trees:
                self.branches.append(branch)
        self.branchCombo.addItems(self.branches)
        try:
            idx = self.branches.index("master")
        except:
            idx = 0
        self.branchCombo.setCurrentIndex(idx)
        self.verticalLayout.addWidget(self.branchCombo)

        self.msgLabel = QLabel("Message to describe this update")
        self.verticalLayout.addWidget(self.msgLabel)

        self.text = QPlainTextEdit()
        self.text.setPlainText(self._message)
        self.verticalLayout.addWidget(self.text)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)

        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(bool(self.branches))

        self.setLayout(self.verticalLayout)
        self.buttonBox.accepted.connect(self.okPressed)

        self.text.setFocus()


    def okPressed(self):
        self.branch = self.branchCombo.currentText()
        self.message = self.text.toPlainText() or datetime.now().strftime("%Y-%m-%d %H_%M_%S")
        self.close()
