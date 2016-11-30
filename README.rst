GeoGig QGIS Plugin
==================

This is a QGIS plugin to work with GeoGig repositories using the GeoGig Web API. 

GeoGig is an open source tool that draws inspiration from Git, but adapts its core concepts to handle distributed versioning of geospatial data. GeoGig is maintained by Boundless (http://boundlessgeo.com/). For more information about GeoGig see http://geogig.org/

Installation
************

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
*****

Usage is documented `here <./docs/source/usage.rst>`_


Known issues
************

There is a known issue in QGIS about the extent of edited Geopackage layers (http://hub.qgis.org/issues/15273) that has been recently fixed (https://github.com/qgis/QGIS/commit/70ae301310c7a58134ac699fae70af7fd1176684) anyway the fix requires a GDAL/OGR minimum version (2.1.2) that is not yet widely used in QGIS installers.

Manual and automatic tests of GeoGig QGIS Plugin
************************************************

The GeoGig QGIS plugin includes a set of manual and automatic tests to be run using the "Tester" QGIS plugin (https://github.com/boundlessgeo/qgis-tester-plugin).

In order for the manual tests work you must ensure that:

- you have a working instance of GeoGig Server (ie: http://localhost:8182/)

- you have created a

::

	~/geogig/server


folder in order to allow the Tester plugin create the necessary temporary GeoGig repositories.

This parameters can be eventually manually modified by editing the

::

	geogig/tests/__init__.py


file of the GeoGig QGIS Plugin, and specifically the lines

::

	REPOS_SERVER_URL = "http://localhost:8182/"
	REPOS_FOLDER = os.path.expanduser("~/geogig/server")

must be eventually changed to reflect your personal setup.

Don't forget to run GeoGig Server by specifying the repositories folder to be published, ie on Linux:

::

	geogig serve -m ~/geogig/server

or on Windows

::

	geogig.bat serve -m c:\Users\yourusername\geogig\server
