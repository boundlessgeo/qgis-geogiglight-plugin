Manual and automatic tests of GeoGig QGIS Plugin
================================================

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
