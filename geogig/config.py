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
from builtins import range

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from geogig.gui.dialogs.userconfigdialog import UserConfigDialog
from geogig.extlibs.qgiscommons2.settings import pluginSetting, setPluginSetting

iface = None
explorer = None

REPOS_FOLDER = "ReposFolder"
USERNAME = "Username"
EMAIL = "Email"
LOG_SERVER_CALLS = "LogServerCalls"


def initConfigParams():
    folder = pluginSetting(REPOS_FOLDER)
    if folder.strip() == "":
        folder = os.path.join(os.path.expanduser('~'), 'geogig', 'repos')
        setPluginSetting(REPOS_FOLDER, folder)



def getUserInfo():
    """Return user information from the settings dialog"""
    user = pluginSetting(USERNAME).strip()
    email = pluginSetting(EMAIL).strip()
    if not (user and email):
        configdlg = UserConfigDialog(iface.mainWindow())
        configdlg.exec_()
        if configdlg.user is not None:
            user = configdlg.user
            email = configdlg.email
            setPluginSetting(USERNAME, user)
            setPluginSetting(EMAIL, email)
            return user, email
        else:
            return None, None
    return user, email
