import os
from PyQt4 import QtGui, QtCore
from qgis.gui import QgsFilterLineEdit
from geogig import config

class ConfigDialog(QtGui.QDialog):

    versioIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../../ui/resources/geogig-16.png")

    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi()
        if hasattr(self.searchBox, 'setPlaceholderText'):
            self.searchBox.setPlaceholderText(self.tr("Search..."))
        self.searchBox.textChanged.connect(self.filterTree)
        self.fillTree()

    def setupUi(self):
        self.resize(640, 450)

        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setMargin(0)
        self.searchBox = QgsFilterLineEdit(self)
        self.verticalLayout.addWidget(self.searchBox)
        self.tree = QtGui.QTreeWidget(self)
        self.tree.setAlternatingRowColors(True)
        self.verticalLayout.addWidget(self.tree)
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel | QtGui.QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)

        self.setWindowTitle("Configuration options")
        self.searchBox.setToolTip("Enter setting name to filter list")
        self.tree.headerItem().setText(0, "Setting")
        self.tree.headerItem().setText(1, "Value")

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.setLayout(self.verticalLayout)

    def filterTree(self):
        text = unicode(self.searchBox.text())
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            visible = False
            for j in range(item.childCount()):
                subitem = item.child(j)
                itemText = subitem.text(0)
            if (text.strip() == ""):
                subitem.setHidden(False)
                visible = True
            else:
                hidden = text not in itemText
                item.setHidden(hidden)
                visible = visible or not hidden
            item.setHidden(not visible)
            item.setExpanded(visible and text.strip() != "")

    def fillTree(self):
        self.items = {}
        self.tree.clear()

        generalItem = self._getItem(config.GENERAL, self.versioIcon, config.generalParams)
        self.tree.addTopLevelItem(generalItem)
        self.tree.setColumnWidth(0, 400)


    def _getItem(self, name, icon, params):
        item = QtGui.QTreeWidgetItem()
        item.setText(0, name)
        item.setIcon(0, icon)
        for param in params:
            paramName = "/GeoGig/Settings/" + name + "/" + param[0]
            subItem = TreeSettingItem(self.tree, item, paramName, *param[1:])
            item.addChild(subItem)
        return item

    def accept(self):
        iterator = QtGui.QTreeWidgetItemIterator(self.tree)
        value = iterator.value()
        while value:
            if hasattr(value, 'checkValue'):
                if value.checkValue():
                    value.setBackgroundColor(1, QtCore.Qt.white)
                else:
                    value.setBackgroundColor(1, QtCore.Qt.yellow)
                    return

            iterator += 1
            value = iterator.value()
        iterator = QtGui.QTreeWidgetItemIterator(self.tree)
        value = iterator.value()
        while value:
            if hasattr(value, 'saveValue'):
                value.saveValue()
            iterator += 1
            value = iterator.value()
        QtGui.QDialog.accept(self)


class TreeSettingItem(QtGui.QTreeWidgetItem):

    def __init__(self, tree, parent, name, description, defaultValue, paramType, check):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        self.parent = parent
        self.name = name
        self.check = check
        self.paramType = paramType
        self.setText(0, description)
        self.tree = tree
        if paramType == config.TYPE_FOLDER:
            self.value = QtCore.QSettings().value(name, defaultValue = defaultValue)
            layout = QtGui.QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            self.lineEdit = QtGui.QLineEdit()
            self.lineEdit.setText(self.value)
            self.label = QtGui.QLabel()
            self.label.setText("<a href='#'> Browse</a>")
            self.lineEdit.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
            layout.addWidget(self.lineEdit)
            layout.addWidget(self.label)
            def edit():
                folder =  QtGui.QFileDialog.getExistingDirectory(tree, description, self.value)
                if folder:
                    self.lineEdit.setText(folder)
            self.label.linkActivated.connect(edit)
            w = QtGui.QWidget()
            w.setLayout(layout)
            self.tree.setItemWidget(self, 1, w)
        elif isinstance(defaultValue, bool):
            self.value = QtCore.QSettings().value(name, defaultValue = defaultValue, type = bool)
            if self.value:
                self.setCheckState(1, QtCore.Qt.Checked)
            else:
                self.setCheckState(1, QtCore.Qt.Unchecked)
        else:
            self.value = QtCore.QSettings().value(name, defaultValue = defaultValue)
            self.setFlags(self.flags() | QtCore.Qt.ItemIsEditable)
            self.setText(1, unicode(self.value))

    def getValue(self):
        if self.paramType == config.TYPE_FOLDER:
            return self.lineEdit.text()
        elif isinstance(self.value, bool):
            return self.checkState(1) == QtCore.Qt.Checked
        else:
            return self.text(1)

    def saveValue(self):
        self.value = self.getValue()
        QtCore.QSettings().setValue(self.name, self.value)

    def checkValue(self):
        try:
            return self.check(self.getValue())
        except:
            return False
