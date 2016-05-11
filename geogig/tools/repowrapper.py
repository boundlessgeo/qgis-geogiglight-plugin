# -*- coding: utf-8 -*-

"""
***************************************************************************
    repowrapper.py
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
from geogig.tools.utils import *
import time
from datetime import datetime
import json
from geogig.geogigwebapi.repository import Repository



class RepositoryWrapper(object):
    def __init__(self, path):
        self._repo = None
        self.name = nameFromRepoPath(path)
        self.path = path
        titlefile = os.path.join(path, "title")
        if os.path.exists(titlefile):
            with open(titlefile) as f:
                self._title = f.readline()
        else:
            self._title = self.name
        self.description = ""
        self.updated = datetime.fromtimestamp(os.path.getmtime(path + "/.geogig")).isoformat()
        self.created = None

    def repo(self):
        if self._repo is None:
            connector = PyQtConnectorDecorator()
            connector.checkIsAlive()
            self._repo = Repository(self.path, connector)
        return self._repo

    def getTitle(self):
        return self._title

    def setTitle(self, title):
        self._title = title
        filename = os.path.join(self.path, "title")
        with open(filename, "w") as f:
            f.write(title)

    title = property(getTitle, setTitle)

    @property
    def fullDescription(self):
        def _prepareDescription():
            footnote = ""
            try:
                ref = self.repo().head.ref
                footnote += "<p>Your current branch is set to <b>%s</b>. GeoGig will track and sync with this branch.</p>" % ref
                c = Commit.fromref(self.repo(), ref)
                epoch = time.mktime(c.committerdate.timetuple())
                offset = datetime.fromtimestamp (epoch) - datetime.utcfromtimestamp (epoch)
                d = c.committerdate + offset
                lastDate = d.strftime("%b %d, %Y %I:%M%p")
                author = c.authorname
                lastVersion = "%s (%s by %s)" % (c.message.splitlines()[0], lastDate, author)
            except:
                lastVersion = ""
            with open(resourceFile("descriptiontemplate_edit.html")) as f:
                s = "".join(f.readlines())
            s = s.replace("[NAME]", self.name)
            s = s.replace("[TITLE]", self.title)
            editIcon = os.path.dirname(__file__) + "/../ui/resources/pencil-icon.png"
            s = s.replace("[EDIT]", "<img src='" + editIcon + "'>")
            s = s.replace("[LAST_VERSION]", lastVersion)
            s = s.replace("[FOOTNOTE]", footnote)
            layers = "<dl>%s</dl>" % "".join(["<dd>%s</dd>" % tree.path for tree in self.repo().trees])
            s = s.replace("[LAYERS]", layers)
            return s
        return(execute(_prepareDescription))


