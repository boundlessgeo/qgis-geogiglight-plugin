# -*- coding: utf-8 -*-

"""
***************************************************************************
    diff.py
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


TYPE_MODIFIED = "Modified"
TYPE_ADDED = "Added"
TYPE_REMOVED = "Removed"

ATTRIBUTE_DIFF_MODIFIED, ATTRIBUTE_DIFF_ADDED, ATTRIBUTE_DIFF_REMOVED, ATTRIBUTE_DIFF_UNCHANGED = ["MODIFIED", "ADDED", "REMOVED", "NO_CHANGE"]
FEATURE_MODIFIED, FEATURE_ADDED, FEATURE_REMOVED = ["MODIFIED", "ADDED", "REMOVED"]
LOCAL_FEATURE_ADDED, LOCAL_FEATURE_MODIFIED, LOCAL_FEATURE_REMOVED = 1, 2, 3


class Diffentry(object):

    '''A difference between two references for a given path'''

    def __init__(self, repo, oldcommitref, newcommitref, path, changetype):
        self.repo = repo
        self.path = path
        self.oldcommitref = oldcommitref
        self.newcommitref = newcommitref
        self.changetype = changetype
        self._featurediff = {True:None, False:None}

    def featurediff(self, allAttrs = True):
        if self._featurediff[allAttrs] is None:
            self._featurediff[allAttrs] = self.repo.featurediff(self.oldcommitref, self.newcommitref, self.path)
        return self._featurediff[allAttrs]


class LocalDiff(object):

    def __init__(self, layername, fid, repo, newfeature, oldcommitid, changetype):
        self.layername = layername
        self.fid = fid
        self.newfeature = newfeature
        self.changetype = changetype
        self.oldcommitid = oldcommitid
        self.repo = repo

    @property
    def oldfeature(self):
        if self.changetype == LOCAL_FEATURE_ADDED:
            return {}
        return self.repo.feature(self.layername + "/" + self.fid, self.oldcommitid)

class ConflictDiff(object):

    def __init__(self, repo, path, originCommit, remoteCommit, localCommit, localFeature,
                localFeatureId, remoteFeatureId, transactionId):
        self.repo = repo
        self.path = path
        self.remoteCommit = remoteCommit
        self.originCommit = originCommit
        self.remoteFeatureId = remoteFeatureId
        self.localCommit = localCommit
        self.localFeature = localFeature
        self.localFeatureId = localFeatureId
        self.transactionId = transactionId

    def resolveWithLocalVersion(self):
        self.repo.resolveConflictWithFeatureId(self.path, self.localFeatureId, self.transactionId)

    def resolveWithRemoteVersion(self):
        self.repo.resolveConflictWithFeatureId(self.path, self.remoteFeatureId, self.transactionId)

    def resolveWithNewFeature(self, feature):
        self.repo.resolveConflictWithFeature(self.path, feature, self.remoteCommit,
                                               self.localCommit, self.transactionId)

    def resolveDeletingFeature(self):
        self.repo.deleteFeature(self.path, self.transactionId)
