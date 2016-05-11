# -*- coding: utf-8 -*-

"""
***************************************************************************
    createrepodialog.py
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


from PyQt4 import QtGui, uic
import os
import sys

sys.path.append(os.path.dirname(__file__))
pluginPath = os.path.split(os.path.dirname(os.path.dirname(__file__)))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'createrepodialog.ui'))

class CreateRepoDialog(WIDGET, BASE):

    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)

        self.buttonBox.accepted.connect(self.okPressed)
        self.buttonBox.rejected.connect(self.cancelPressed)

        self.title = None

    def okPressed(self):
        self.urlBox.setStyleSheet("QLineEdit{background: white}")
        self.titleBox.setStyleSheet("QLineEdit{background: white}")
        title = self.titleBox.text().strip()
        if title == "":
            self.titleBox.setStyleSheet("QLineEdit{background: yellow}")
            return
        self.title = title
        url = self.urlBox.text().strip()
        if url == "":
            self.urlBox.setStyleSheet("QLineEdit{background: yellow}")
            return
        self.url = url
        self.close()

    def cancelPressed(self):
        self.title = None
        self.close()

