from PyQt4 import QtCore, QtGui

class BlameDialog(QtGui.QDialog):
    def __init__(self, repo, path):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.blamedata = repo.blame(path)
        self.repo = repo
        self.commitText = {}
        self.setupUi()

    def setupUi(self):
        self.resize(800, 600)
        self.setWindowTitle("Authorship")
        layout = QtGui.QVBoxLayout()
        splitter = QtGui.QSplitter(self)
        splitter.setOrientation(QtCore.Qt.Vertical)
        self.table = QtGui.QTableWidget(splitter)
        self.table.setColumnCount(3)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.setHorizontalHeaderLabels(["Attribute", "Author", "Value"])
        self.table.setRowCount(len(self.blamedata))
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection);
        self.table.selectionModel().selectionChanged.connect(self.selectionChanged)
        idx = 0
        for name in self.blamedata:
            values = self.blamedata[name]
            self.table.setItem(idx, 0, QtGui.QTableWidgetItem(name));
            self.table.setItem(idx, 2, QtGui.QTableWidgetItem(values[0]));
            self.table.setItem(idx, 1, QtGui.QTableWidgetItem(values[2]));
            idx += 1
        self.table.resizeRowsToContents()
        self.table.horizontalHeader().setMinimumSectionSize(250)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.text = QtGui.QTextBrowser(splitter)
        layout.addWidget(splitter)
        self.setLayout(layout)
        QtCore.QMetaObject.connectSlotsByName(self)

    def selectionChanged(self):
        idx = self.table.currentRow()
        commitid = self.blamedata[self.table.item(idx, 0).text()][1]
        if commitid in self.commitText:
            text = self.commitText[commitid]
        else:
            text = self.repo.show(commitid)
        self.text.setText(text)
        self.commitText[commitid] = text


