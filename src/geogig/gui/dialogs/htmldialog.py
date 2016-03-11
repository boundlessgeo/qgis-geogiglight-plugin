from PyQt4 import QtGui

class HtmlDialog(QtGui.QDialog):

    def __init__(self, title, content, parent = None):
        super(HtmlDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setMargin(10)
        self.text = QtGui.QTextBrowser()
        self.text.setHtml(content)
        self.verticalLayout.addWidget(self.text)
        self.setLayout(self.verticalLayout)
        self.resize(400, 400)


