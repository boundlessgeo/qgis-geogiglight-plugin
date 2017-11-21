# -*- coding: utf-8 -*-

"""
***************************************************************************
    commit.py
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
from __future__ import absolute_import
from builtins import str

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import datetime
import time

from .commitish import Commitish
from geogig.tools.utils import relativeDate

NULL_ID = "0" * 40


class Commit(Commitish):

    _commitcache = {}
    
    @staticmethod
    def addToCache(repoUrl, commits):
        for c in commits:
            Commit._commitcache[(repoUrl, c.commitid)] = c 

    ''' A geogig commit'''

    def __init__(self, repo, commitid, treeid, parents, message, authorname,
                 authordate, committername, committerdate, added, removed, modified):
        Commitish.__init__(self, repo, commitid)
        self.repo = repo
        self.commitid = commitid
        self.treeid = treeid
        self._parents = parents or [NULL_ID]
        self.message = str(message)
        self.authorname = authorname
        self.authordate = authordate
        self.committername = committername
        self.committerdate = committerdate
        self.added = added
        self.removed = removed
        self.modified = modified
        self._children = []
        self.tags = []
        self.generation = 1

    @staticmethod
    def fromref(repo, ref):
        '''
        Returns a Commit corresponding to a given id.
        ref is passed as a string.
        '''
        if ref == NULL_ID:
            return Commitish(repo, NULL_ID)
        else:
            cid = repo.revparse(ref)
            if (repo.url, cid) not in Commit._commitcache:
                log = repo.log(until = cid, limit = 1)
                if not log:                                    
                    Commit._commitcache[(repo.url, cid)] = Commitish(repo, NULL_ID)
                else:
                    Commit._commitcache[(repo.url, cid)] = log[0]
            return Commit._commitcache[(repo.url, cid)]

    childrenCache = None
    @property
    def children(self):
        '''Returns a list of commits with commits representing the children of this commit'''
        if self.childrenCache is None:
            self.childrenCache =  [self.fromref(self.repo, p) for p in self._children]
        return self.childrenCache
    
    parentsCache = None
    @property
    def parents(self):
        '''Returns a list of commits with commits representing the parents of this commit'''
        if self.parentsCache is None:
            self.parentsCache = [self.fromref(self.repo, p) for p in self._parents]
        return self.parentsCache

    @property
    def parent(self):
        '''
        Returns the parent commit, assuming a linear history.
        It's similar to the tilde(~) operator
        '''
        return self.parents[0]

    def addsLayer(self):
        '''Returns true if this commit adds a new layer'''
        if self._parents == [NULL_ID]:
            return True
        prevLayers = self.repo.trees(self.parent.commitid)
        layers = self.repo.trees(self.commitid)
        return len(layers) > len(prevLayers)

    def diff(self, path = None):
        '''Returns a list of DiffEntry with all changes introduced by this commit'''
        if self._diff is None:
            self._diff = self.repo.diff(self.parent.ref, self.ref, path)
        return self._diff

    def humantext(self):
        '''Returns a nice human-readable description of the commit'''
        headid = self.repo.revparse(self.repo.HEAD)
        if headid == self.id:
            return "Current last commit"
        epoch = time.mktime(self.committerdate.timetuple())
        offset = datetime.datetime.fromtimestamp (epoch) - datetime.datetime.utcfromtimestamp (epoch)
        d = self.committerdate + offset
        return self.message + d.strftime(" (%m/%d/%y %H:%M)")

    def committerprettydate(self):
        return relativeDate(self.committerdate)

    def authorprettydate(self):
        return relativeDate(self.authordate)

    def __str__(self):
        try:
            msg = str(self.message, errors = "ignore")
        except TypeError:
            msg = self.message
        s = "id " + self.commitid + "\n"
        s += "parents " + str(self._parents) + "\n"
        s += "tree " + self.treeid + "\n"
        s += "author " + self.authorname + " " + str(self.authordate) + "\n"
        s += "message " + msg + "\n"

        return s
    
    def isFork(self):
        ''' Returns True if the node is a fork'''
        return len(self._children) > 1

    def isMerge(self):
        ''' Returns True if the node is a fork'''
        return len(self._parents) > 1

def setChildren(commits):
    commitsDict = {c.commitid:c for c in commits}
    
    for c in commits[::-1]:
        if c.parents:
            generation = None
            for p in c._parents:
                parent = commitsDict.get(p, None)
                if parent:
                    parent._children.append(c.commitid)
                    if generation is None:
                        generation = parent.generation+1
                    generation = max(parent.generation+1, generation)
                else:
                    generation = 0
            c.generation = generation

    return commits
    