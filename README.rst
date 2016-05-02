GeoGig QGIS Plugin
==============================

This is a QGIS plugin to work with GeoGig repositories using the GeoGig Web API

Installation
*************

To install, copy the ``geogig`` folder into ``[your_user_folder]/.qgis2/python/plugins/`` (You may need to create this directory). You should have a ``geogig`` folder under the QGIS plugins folder.

Open QGIS and make sure that the plugin is enabled, by opening the QGIS Plugin Manager.

Usage
********

Usage is documented `here <./doc/usage.rst>`_



Cloning this repository
=======================

This repository uses external repositories as submodules. Therefore in order to include the external repositories during cloning you should use the *--recursive* option:

git clone --recursive http://github.com/boundlessgeo/qgis-geogiglight-plugin.git

Also, to update the submodules whenever there are changes in the remote repositories one should do:

git submodule update --remote
