#!/bin/bash
OC_VERSION=$1

docker pull nextcloud:$OC_VERSION
DOCKER_ID=$(docker run -d -p 80:80 nextcloud:$NC_VERSION)

# needed else occ isn't available directly...
sleep 5

docker exec -u www-data $DOCKER_ID ./occ maintenance:install --admin-user="admin" --admin-pass="admin" --database="sqlite"

