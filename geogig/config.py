import os
from PyQt4 import QtCore

iface = None
explorer = None

GENERAL = "General"

USE_MAIN_MENUBAR = "UseMainMenuBar"
REPOS_FOLDER = "ReposFolder"
USERNAME = "Username"
EMAIL = "Email"

TYPE_NUMBER, TYPE_STRING, TYPE_FOLDER, TYPE_BOOL = range(4)

def checkFolder(f):
    if os.path.isdir(f):
        return True
    try:
        os.makedirs(f)
        return True
    except:
        return False


generalParams = [(USE_MAIN_MENUBAR, "Put GeoGig menus in main menu bar (requires restart)", True, TYPE_BOOL, lambda x: True),
                 (REPOS_FOLDER, "Base folder for repository data", "", TYPE_FOLDER, checkFolder),
                 (USERNAME, "User name", "", TYPE_STRING, True),
                 (EMAIL, "User email", "", TYPE_STRING, True)]

def initConfigParams():
    folder = getConfigValue(GENERAL, REPOS_FOLDER)
    if folder.strip() == "":
        folder = os.path.join(os.path.expanduser('~'), 'geogig', 'repos')
        setConfigValue(GENERAL, REPOS_FOLDER, folder)

def getConfigValue(group, name):
    default = None
    for param in generalParams:
        if param[0] == name:
            default = param[2]

    if isinstance(default, bool):
        return QtCore.QSettings().value("/GeoGig/Settings/%s/%s" % (group, name), default, bool)
    else:
        return QtCore.QSettings().value("/GeoGig/Settings/%s/%s" % (group, name), default, str)

def setConfigValue(group, name, value):
    return QtCore.QSettings().setValue("/GeoGig/Settings/%s/%s" % (group, name), value)
