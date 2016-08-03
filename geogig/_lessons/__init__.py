# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from geogig.tests.testplugin import backupConfiguration, restoreConfiguration
import os
import traceback
from geogig.tests import REPOS_SERVER_URL, REPOS_FOLDER
import requests

try:
    from lessons.lesson import Lesson, Step
    class GeoGigLesson(Lesson):
        def __init__(self, name):
            Lesson.__init__(self, name, "GeoGig lessons", "lesson.html")
            self.folder = os.path.dirname(traceback.extract_stack()[-2][0])
            self.description = self.resolveFile(self.description)
            self.addStep("Preparing lesson", "Preparing lesson", backupConfiguration)
            helpFile= os.path.abspath(os.path.join(os.path.dirname(__file__), "common", "preparegeogig.html"))
            self.addStep("Prepare GeoGig environment", helpFile,
               endcheck=checkGeoGig, steptype=Step.MANUALSTEP)
            self.setCleanup(restoreConfiguration)
except:
    pass

def checkGeoGig():
    if not os.path.exists(REPOS_FOLDER):
        return False
    try:
        requests.get(REPOS_SERVER_URL + "repos")
        return True
    except:
        return False