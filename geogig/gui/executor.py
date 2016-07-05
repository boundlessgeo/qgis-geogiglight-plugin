# -*- coding: utf-8 -*-

"""
***************************************************************************
    executor.py
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



from qgis.core import *
from geogig import config
from PyQt4 import QtGui, QtCore


class GeoGigThread(QtCore.QThread):

    finished = QtCore.pyqtSignal()

    def __init__(self, func):
        QtCore.QThread.__init__(self, config.iface.mainWindow())
        self.func = func
        self.returnValue = []
        self.exception = None

    def run (self):
        try:
            self.returnValue = self.func()
            self.finished.emit()
        except Exception, e:
            self.exception = e
            self.finished.emit()

_dialog = None

def execute(func, useThread = False):
    try:
        QtCore.QCoreApplication.processEvents()
        QtGui.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        if useThread:
            t = GeoGigThread(func)
            loop = QtCore.QEventLoop()
            t.finished.connect(loop.exit, QtCore.Qt.QueuedConnection)
            QtGui.QApplication.processEvents()
            t.start()
            loop.exec_(flags = QtCore.QEventLoop.ExcludeUserInputEvents)
            if t.exception is not None:
                raise t.exception
            return t.returnValue
        else:
            return func()
    finally:
        QtGui.QApplication.restoreOverrideCursor()
        QtCore.QCoreApplication.processEvents()
