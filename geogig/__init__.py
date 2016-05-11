# -*- coding: utf-8 -*-

"""
***************************************************************************
    __init__.py
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
