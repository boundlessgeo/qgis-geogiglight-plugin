from PyQt4.QtCore import pyqtSignal, QObject

class RepoWatcher(QObject):

    repoChanged = pyqtSignal(object)
    layerUpdated = pyqtSignal(object)

repoWatcher = RepoWatcher()