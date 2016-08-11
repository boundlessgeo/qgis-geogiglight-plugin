GeoGig QGIS Plugin
==================

This is a QGIS plugin to work with GeoGig repositories using the GeoGig Web API. 

GeoGig is an open source tool that draws inspiration from Git, but adapts its core concepts to handle distributed versioning of geospatial data. GeoGig is maintained by Boundless (http://boundlessgeo.com/). For more information about GeoGig see http://geogig.org/

Installation
*************

To install the latest version of the plugin on **Linux**:

- clone this repository, open a console in the repository folder and type

::

	paver setup

This will get all the dependencies needed by the plugin.

- install into QGIS by running

::

	paver install


To install the latest version of the plugin on **Windows**:

- open as Administrator the "OSGeo command shell" available in any QGIS installation

- launch the following command to install paver (https://github.com/paver/paver)

::

	pip install paver


- download and unzip the latest code of the plugin using the following URL

::

	https://github.com/boundlessgeo/qgis-geogiglight-plugin/archive/master.zip


- using the OSGeo command shell enter the unzipped folder and run

::

	paver setup

This will get all the dependencies needed by the plugin


- copy the "geogig" folder inside of

::

	c:\users\yourusername\.qgis2\python\plugins\


Usage
********

Usage is documented `here <./doc/source/usage.rst>`_


