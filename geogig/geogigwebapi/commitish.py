# -*- coding: utf-8 -*-

"""
***************************************************************************
    commitish.py
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
from builtins import str
from builtins import object

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


class Commitish(object):

    def __init__(self, repo, ref):
        self.ref = ref
        self.commitid = ref
        self.repo = repo
        self._diff = None
        self._id = None

    @property
    def id(self):
        '''Returns the SHA1 ID of this commitish'''
        if self._id is None:
            self._id = self.repo.revparse(self.ref)
        return self._id

    def log(self):
        '''Return the history up to this commitish'''
        return self.repo.log(until = self.ref)


    def diff(self):
        '''Returns a list of DiffEntry with all changes introduced by this commitish'''
        if self._diff is None:
            self._diff = self.repo.diff(self.ref + '~1', self.ref)
        return self._diff

    @property
    def parent(self):
        '''Returns a commitish that represents the parent of this one'''
        return Commitish(self.repo, self.ref + '~1')

    def humantext(self):
        '''Returns a nice human-readable description of the commitish'''
        headid = self.repo.revparse(self.repo.HEAD)
        if headid == self.id:
            return "Current branch"
        return self.ref

    def __str__(self):
        return str(self.ref)

    def isFork(self):
        ''' Returns True if the node is a fork'''
        return False

    def isMerge(self):
        ''' Returns True if the node is a fork'''
        return False

