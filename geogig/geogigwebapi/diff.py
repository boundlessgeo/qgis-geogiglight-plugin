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
        return self.repo.feature(self.layername + "/" + self.fid, self.oldcommitid)



