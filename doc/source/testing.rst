Manual and automatic tests of GeoGig QGIS Plugin
==============================

The GeoGig QGIS plugin includes a set of manual and automatic tests to be run using the "Tester" QGIS plugin (https://github.com/boundlessgeo/qgis-tester-plugin).

In order for the manual tests work two variables needs to be configured in the 


::

	geogig/tests/__init__.py


file of the GeoGig QGIS Plugin, and specifically

::

	REPOS_SERVER_URL = "http://localhost:8182/"
	REPOS_FOLDER = "d:\\repo" #fill this with your repos folder

must be changed to reflect a working GeoGig server URL and the position of a local GeoGig repository.
