#!/bin/bash
# Run docker tests on your local machine

PLUGIN_NAME="geogig"
export QGIS_VERSION_TAG="master_2"

# Make sure the shared volume folder exists

if [ ! -d "./geogig_repo" ]; then
    mkdir ./geogig_repo
fi

docker-compose down -v
docker-compose up -d
sleep 10


DOCKER_RUN_COMMAND="docker-compose exec qgis-testing-environment sh -c"

# Setup
$DOCKER_RUN_COMMAND "qgis_setup.sh $PLUGIN_NAME"
$DOCKER_RUN_COMMAND "pip install paver"
$DOCKER_RUN_COMMAND "cd /tests_directory && paver setup && paver package --tests"

# Run the tests
$DOCKER_RUN_COMMAND "REPOS_SERVER_URL=http://geogig:8182/ REPOS_FOLDER=/geogig_repo DISPLAY=unix:0 qgis_testrunner.sh geogig.tests.testplugin.run_tests"
