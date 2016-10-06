# -*- coding: utf-8 -*-

"""
***************************************************************************
    py
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

import os
from qgis.core import NULL
from PyQt4 import QtCore
from geogig.gui.dialogs.userconfigdialog import UserConfigDialog

iface = None
explorer = None

GENERAL = "General"

USE_MAIN_MENUBAR = "UseMainMenuBar"
REPOS_FOLDER = "ReposFolder"
USERNAME = "Username"
EMAIL = "Email"
LOG_SERVER_CALLS = "LogServerCalls"

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
                 (USERNAME, "User name", "", TYPE_STRING, lambda x: True),
                 (EMAIL, "User email", "", TYPE_STRING, lambda x: True),
                 (LOG_SERVER_CALLS, "Log server calls", False, TYPE_BOOL, lambda x: True)]


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
        v = QtCore.QSettings().value("/GeoGig/Settings/%s/%s" % (group, name), default, str)
        if v == NULL:
            v = None
        return v


def setConfigValue(group, name, value):
    return QtCore.QSettings().setValue("/GeoGig/Settings/%s/%s" % (group, name), value)


def getUserInfo():
    """Return user information from the settings dialog"""
    user = getConfigValue(GENERAL, USERNAME).strip()
    email = getConfigValue(GENERAL, EMAIL).strip()
    if not (user and email):
        configdlg = UserConfigDialog(iface.mainWindow())
        configdlg.exec_()
        if configdlg.user is not None:
            user = configdlg.user
            email = configdlg.email
            setConfigValue(GENERAL, USERNAME, user)
            setConfigValue(GENERAL, EMAIL, email)
            return user, email
        else:
            return None, None
    return user, email
