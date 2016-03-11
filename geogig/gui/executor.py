
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

def execute(func, message = None, useThread = False):
    global _dialog
    cursor = QtGui.QApplication.overrideCursor()
    waitCursor = (cursor is not None and cursor.shape() == QtCore.Qt.WaitCursor)
    dialogCreated = False
    try:
        QtCore.QCoreApplication.processEvents()
        if not waitCursor:
            QtGui.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        if message is not None and useThread:
            t = GeoGigThread(func)
            loop = QtCore.QEventLoop()
            t.finished.connect(loop.exit, QtCore.Qt.QueuedConnection)
            if _dialog is None:
                dialogCreated = True
                _dialog = QtGui.QProgressDialog(message, "GeoGig", 0, 0, config.iface.mainWindow())
                _dialog.setWindowTitle("GeoGig")
                _dialog.setWindowModality(QtCore.Qt.WindowModal);
                _dialog.setMinimumDuration(1000)
                _dialog.setMaximum(100)
                _dialog.setValue(0)
                _dialog.setMaximum(0)
                _dialog.setCancelButton(None)
            else:
                oldText = _dialog.labelText()
                _dialog.setLabelText(message)
            QtGui.QApplication.processEvents()
            t.start()
            loop.exec_(flags = QtCore.QEventLoop.ExcludeUserInputEvents)
            if t.exception is not None:
                raise t.exception
            return t.returnValue
        else:
            return func()
    finally:
        if message is not None and useThread:
            if dialogCreated:
                _dialog.reset()
                _dialog = None
            else:
                _dialog.setLabelText(oldText)
        if not waitCursor:
            QtGui.QApplication.restoreOverrideCursor()
        QtCore.QCoreApplication.processEvents()
