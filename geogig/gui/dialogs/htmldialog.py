# -*- coding: utf-8 -*-

"""
***************************************************************************
    htmldialog.py
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


from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QTextBrowser

class HtmlDialog(QDialog):

    def __init__(self, title, content, parent = None):
        super(HtmlDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setMargin(10)
        self.text = QTextBrowser()
        self.text.setHtml(content)
        self.verticalLayout.addWidget(self.text)
        self.setLayout(self.verticalLayout)
        self.resize(400, 400)
