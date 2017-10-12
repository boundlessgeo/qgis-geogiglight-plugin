To follow this lesson, you will need to have a GeoGig server running in
your localhost in the 8182 port. If you haven't done it before, follow
these instructions to set it up.

* Download GeoGig version 1.1.1 from www.geogig.org;
* Unzip the `geogig-1.1.1.zip` to a folder of your choice;
* Add the unzipped `geogig/bin/` folder to your PATH environment variable;
* If not done yet, install Java JVM and also add it to the PATH
  environment variable;

* Using the command line, setup GeoGig global `user.name` and
  `user.email` using the following commands:

    `geogig config --global user.name yourname`

    `geogig config --global user.email your@email.com`

* Using the command line, start the GeoGig server by running the
  following command from the folder that will store your repository
  folder:

    `geogig serve -m`

  If the server started correctly, you will see the following message:

  *"Starting server on port 8182, use CTRL+C to exit."*

Click **Next step** once you are done.