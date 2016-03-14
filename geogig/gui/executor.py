
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
    cursor = QtGui.QApplication.overrideCursor()
    waitCursor = (cursor is not None and cursor.shape() == QtCore.Qt.WaitCursor)
    try:
        QtCore.QCoreApplication.processEvents()
        if not waitCursor:
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
        if not waitCursor:
            QtGui.QApplication.restoreOverrideCursor()
        QtCore.QCoreApplication.processEvents()
