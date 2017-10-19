# -*- coding: utf-8 -*-

"""
***************************************************************************
    geogigref.py
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
from builtins import range

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import datetime
import os
import time

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget,
                                 QVBoxLayout,
                                 QHBoxLayout,
                                 QRadioButton,
                                 QComboBox,
                                 QGroupBox,
                                 QDialog,
                                 QDialogButtonBox,
                                 QMessageBox,
                                 QListWidgetItem,
                                 QLineEdit,
                                 QListWidget,
                                 QAbstractItemView,
                                 QSizePolicy,
                                 QToolButton
                                )
from qgis.PyQt.QtGui import QIcon
from qgis.utils import iface

from geogig.geogigwebapi.commitish import Commitish
from geogig.geogigwebapi.commit import Commit


class RefPanel(QWidget):

    refChanged = pyqtSignal()

    def __init__(self, repo, ref = None):
        super(RefPanel, self).__init__(None)
        self.repo = repo
        self.ref = ref
        self.horizontalLayout = QHBoxLayout(self)
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setMargin(0)
        self.text = QLineEdit()
        self.text.setEnabled(False)
        if ref is not None:
            self.text.setText(ref.humantext())
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.horizontalLayout.addWidget(self.text)
        self.pushButton = QToolButton()
        self.pushButton.setText("...")
        self.pushButton.clicked.connect(self.showSelectionDialog)
        self.pushButton.setEnabled(self.repo is not None)
        self.horizontalLayout.addWidget(self.pushButton)
        self.setLayout(self.horizontalLayout)

    def showSelectionDialog(self):
        from geogig.gui.dialogs.historyviewer import HistoryViewerDialog
        dialog = HistoryViewerDialog(self.repo)
        dialog.exec_()
        ref = dialog.ref
        if ref:
            commit = Commit.fromref(self.repo, ref)
            self.setRef(commit)

    def setRepo(self, repo):
        self.repo = repo
        self.pushButton.setEnabled(True)
        self.setRef(Commitish(repo, repo.HEAD))

    def setRef(self, ref):
        self.ref = ref
        self.text.setText(ref.humantext())
        self.refChanged.emit()

    def getRef(self):
        return self.ref

