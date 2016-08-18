GeoGig QGIS Plugin
==================

This is a QGIS plugin to work with GeoGig repositories using the GeoGig Web API. 

GeoGig is an open source tool that draws inspiration from Git, but adapts its core concepts to handle distributed versioning of geospatial data. GeoGig is maintained by Boundless (http://boundlessgeo.com/). For more information about GeoGig see http://geogig.org/

Installation
*************

To install the latest version of the plugin:

- Clone this repository or download and unzip the latest code of the plugin using the following URL

::

	https://github.com/boundlessgeo/qgis-geogiglight-plugin/archive/master.zip
	
- If you do not have paver (https://github.com/paver/paver) installed, install it by typing the following in a console:

::

	pip install paver
	
- Open a console in the folder created in the first step, and type

::

	paver setup

This will get all the dependencies needed by the plugin.

- Install into QGIS by running

::

	paver install


Usage
********

Usage is documented `here <./docs/source/usage.rst>`_


