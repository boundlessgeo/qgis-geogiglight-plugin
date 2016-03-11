# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'versionsviewer.ui'
#
# Created: Wed Apr 23 08:34:03 2014
#      by: PyQt4 UI code generator 4.9.6
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_VersionViewer(object):
    def setupUi(self, VersionViewer):
        VersionViewer.setObjectName(_fromUtf8("VersionViewer"))
        VersionViewer.resize(815, 588)
        self.verticalLayout_2 = QtGui.QVBoxLayout(VersionViewer)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.splitter_2 = QtGui.QSplitter(VersionViewer)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setObjectName(_fromUtf8("splitter_2"))
        self.groupBox_2 = QtGui.QGroupBox(self.splitter_2)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_2.sizePolicy().hasHeightForWidth())
        self.groupBox_2.setSizePolicy(sizePolicy)
        self.groupBox_2.setMaximumSize(QtCore.QSize(350, 16777215))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.verticalLayout_6 = QtGui.QVBoxLayout(self.groupBox_2)
        self.verticalLayout_6.setObjectName(_fromUtf8("verticalLayout_6"))
        self.listWidget = QtGui.QListWidget(self.groupBox_2)
        self.listWidget.setMinimumSize(QtCore.QSize(250, 0))
        self.listWidget.setAlternatingRowColors(True)
        self.listWidget.setObjectName(_fromUtf8("listWidget"))
        self.verticalLayout_6.addWidget(self.listWidget)
        self.groupBox_3 = QtGui.QGroupBox(self.splitter_2)
        self.groupBox_3.setObjectName(_fromUtf8("groupBox_3"))
        self.verticalLayout = QtGui.QVBoxLayout(self.groupBox_3)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.splitter = QtGui.QSplitter(self.groupBox_3)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.attributesTable = QtGui.QTableWidget(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.attributesTable.sizePolicy().hasHeightForWidth())
        self.attributesTable.setSizePolicy(sizePolicy)
        self.attributesTable.setMinimumSize(QtCore.QSize(0, 0))
        self.attributesTable.setMaximumSize(QtCore.QSize(16777215, 200))
        self.attributesTable.setStyleSheet(_fromUtf8("#featureDetailsTableWidget::section {\n"
"    background: yellow;\n"
"    border: 2px outset yellow;\n"
"}"))
        self.attributesTable.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.attributesTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.attributesTable.setProperty("showDropIndicator", False)
        self.attributesTable.setDragDropOverwriteMode(False)
        self.attributesTable.setAlternatingRowColors(False)
        self.attributesTable.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.attributesTable.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.attributesTable.setShowGrid(True)
        self.attributesTable.setGridStyle(QtCore.Qt.DotLine)
        self.attributesTable.setWordWrap(False)
        self.attributesTable.setObjectName(_fromUtf8("attributesTable"))
        self.attributesTable.setColumnCount(2)
        self.attributesTable.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter | QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        item.setFont(font)
        self.attributesTable.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter | QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        item.setFont(font)
        self.attributesTable.setHorizontalHeaderItem(1, item)
        self.attributesTable.horizontalHeader().setCascadingSectionResizes(True)
        self.attributesTable.horizontalHeader().setDefaultSectionSize(180)
        self.attributesTable.horizontalHeader().setMinimumSectionSize(30)
        self.attributesTable.horizontalHeader().setStretchLastSection(True)
        self.attributesTable.verticalHeader().setVisible(False)
        self.attributesTable.verticalHeader().setCascadingSectionResizes(True)
        self.attributesTable.verticalHeader().setStretchLastSection(False)
        self.mapWidget = QtGui.QWidget(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.mapWidget.sizePolicy().hasHeightForWidth())
        self.mapWidget.setSizePolicy(sizePolicy)
        self.mapWidget.setObjectName(_fromUtf8("mapWidget"))
        self.verticalLayout.addWidget(self.splitter)
        self.verticalLayout_2.addWidget(self.splitter_2)

        self.retranslateUi(VersionViewer)
        QtCore.QMetaObject.connectSlotsByName(VersionViewer)

    def retranslateUi(self, VersionViewer):
        VersionViewer.setWindowTitle(_translate("VersionViewer", "Version Viewer", None))
        self.groupBox_2.setTitle(_translate("VersionViewer", "List of Versions (click on a version to see details):", None))
        self.groupBox_3.setTitle(_translate("VersionViewer", "Details of Each Version:", None))
        self.attributesTable.setSortingEnabled(True)
        item = self.attributesTable.horizontalHeaderItem(0)
        item.setText(_translate("VersionViewer", "ATTRIBUTE", None))
        item = self.attributesTable.horizontalHeaderItem(1)
        item.setText(_translate("VersionViewer", "Value", None))

import geogigclient_resources_rc
