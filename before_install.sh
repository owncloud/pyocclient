#!/bin/bash
#
# ownCloud
#
# @author Thomas Müller
# @copyright 2014 Thomas Müller thomas.mueller@tmit.eu
#

set -e

WORKDIR=$PWD
CORE_BRANCH=$1
echo "Work directory: $WORKDIR"
git clone --depth 1 -b $CORE_BRANCH https://github.com/owncloud/core
cd core
git submodule update --init

cd $WORKDIR

if [ "$DB" == "mysql" ] ; then
  mysql -e 'create database oc_autotest;'
  mysql -u root -e "CREATE USER 'oc_autotest'@'localhost' IDENTIFIED BY 'owncloud'";
  mysql -u root -e "grant all on oc_autotest.* to 'oc_autotest'@'localhost'";
fi

#
# copy install script
#
cd core

bash ./core_install.sh mysql
