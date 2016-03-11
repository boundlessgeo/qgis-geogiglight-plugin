from PyQt4 import QtGui
from geogig import config
from geogigpy import geogig


class UserConfigDialog(QtGui.QDialog):

    def __init__(self, parent = None):
        super(UserConfigDialog, self).__init__(parent)
        self.user = None
        self.email = None
        self.initGui()

    def initGui(self):
        self.setWindowTitle('GeoGig user configuration')
        verticalLayout = QtGui.QVBoxLayout()

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        usernameLabel = QtGui.QLabel('Username')
        self.usernameBox = QtGui.QLineEdit()
        horizontalLayout.addWidget(usernameLabel)
        horizontalLayout.addWidget(self.usernameBox)
        verticalLayout.addLayout(horizontalLayout)

        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)
        emailLabel = QtGui.QLabel('User email')
        self.emailBox = QtGui.QLineEdit()
        horizontalLayout.addWidget(emailLabel)
        horizontalLayout.addWidget(self.emailBox)
        verticalLayout.addLayout(horizontalLayout)

        self.groupBox = QtGui.QGroupBox()
        self.groupBox.setTitle("User data")
        self.groupBox.setLayout(verticalLayout)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.groupBox)
        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

        self.buttonBox.accepted.connect(self.okPressed)
        self.buttonBox.rejected.connect(self.cancelPressed)

        self.resize(400, 200)

    def okPressed(self):
        self.user = unicode(self.usernameBox.text())
        self.email = unicode(self.emailBox.text())
        self.close()

    def cancelPressed(self):
        self.user = None
        self.email = None
        self.close()

def configureUser():
    user = config.getConfigValue(config.GENERAL, config.USERNAME)
    email = config.getConfigValue(config.GENERAL, config.EMAIL)
    if not (user and email):
        configdlg = UserConfigDialog(config.iface.mainWindow())
        configdlg.exec_()
        if configdlg.user is not None:
            user = configdlg.user
            email = configdlg.email
            config.setConfigValue(config.GENERAL, config.USERNAME, user)
            config.setConfigValue(config.GENERAL, config.EMAIL, email)
        else:
            return
    con = PyQtConnectorDecorator()
    con.configglobal(geogig.USER_NAME, user)
    con.configglobal(geogig.USER_EMAIL, email)