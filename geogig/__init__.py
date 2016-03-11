# -*- coding: utf-8 -*-

import sys
import os
import site

# Ensure bundled tools are executable for OS X
if sys.platform == 'darwin':
    bin_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),'bin')
    jre_path = os.path.join(bin_path,'jre','osx','bin')
    gg_path = os.path.join(bin_path,'geogig','bin')

    for bin in os.listdir(gg_path):
        os.chmod(os.path.join(gg_path,bin), 0744)

    for bin in os.listdir(jre_path):
        os.chmod(os.path.join(jre_path,bin), 0744)

site.addsitedir(os.path.abspath(os.path.dirname(__file__) + '/ext-libs'))

def classFactory(iface):
    from geogig.plugin import GeoGigPlugin
    return GeoGigPlugin(iface)
