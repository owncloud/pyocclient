#!/bin/bash
#
# ownCloud
#
# @author Thomas Müller
# @copyright 2014 Thomas Müller thomas.mueller@tmit.eu
#

set -e

DATABASENAME=oc_autotest
DATABASEUSER=oc_autotest
ADMINLOGIN=admin
BASEDIR=$PWD

DBCONFIGS="mysql"
PHPUNIT=$(which phpunit)

# use tmpfs for datadir - should speedup unit test execution
DATADIR=$BASEDIR/data-autotest

echo "Using database $DATABASENAME"

cat > ./tests/autoconfig-mysql.php <<DELIM
<?php
\$AUTOCONFIG = array (
  'installed' => false,
  'dbtype' => 'mysql',
  'dbtableprefix' => 'oc_',
  'adminlogin' => '$ADMINLOGIN',
  'adminpass' => 'admin',
  'directory' => '$DATADIR',
  'dbuser' => '$DATABASEUSER',
  'dbname' => '$DATABASENAME',
  'dbhost' => 'localhost',
  'dbpass' => 'owncloud',
);
DELIM

function execute_tests {
    echo "Setup environment for $1 testing ..."
    # back to root folder
    cd $BASEDIR

    # revert changes to tests/data
    #git checkout tests/data/*

    # reset data directory
    rm -rf $DATADIR
    mkdir $DATADIR

    # copy autoconfig
    cp $BASEDIR/tests/autoconfig-$1.php $BASEDIR/core/config/autoconfig.php

    # trigger installation
    echo "INDEX"
    php -f core/index.php
    echo "END INDEX"

    #test execution
    cd tests
    php -f enable_all.php
}

#
# start test execution
#
if [ -z "$1" ]
  then
    # run all known database configs
    for DBCONFIG in $DBCONFIGS; do
        execute_tests $DBCONFIG
    done
else
    execute_tests $1 $2 $3
fi

# show environment


echo "owncloud configuration:"
cat $BASEDIR/config/config.php


echo "data directory:"
ls -ll $DATADIR

echo "owncloud.log:"
cat $DATADIR/owncloud.log

cd $BASEDIR


