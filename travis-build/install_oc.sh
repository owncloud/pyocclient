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
echo "New Workdir: $WORKDIR"

#
# install script
#
cd core

DATABASENAME=oc_autotest
DATABASEUSER=oc_autotest
ADMINLOGIN=admin
BASEDIR=$PWD

DBCONFIGS="sqlite"
#PHPUNIT=$(which phpunit)

# use tmpfs for datadir - should speedup unit test execution
DATADIR=$BASEDIR/data

# users to create (with unusable password)
USERS="share"

echo "Using database $DATABASENAME"

cat > ./tests/autoconfig-sqlite.php <<DELIM
<?php
\$AUTOCONFIG = array (
  'installed' => false,
  'dbtype' => 'sqlite',
  'dbtableprefix' => 'oc_',
  'adminlogin' => '$ADMINLOGIN',
  'adminpass' => 'admin',
  'directory' => '$DATADIR',
);
DELIM

echo "Setup environment for testing ..."
# back to root folder
cd $BASEDIR

# reset data directory
mkdir $DATADIR

cp $BASEDIR/tests/preseed-config.php $BASEDIR/config/config.php

# copy autoconfig
cp $BASEDIR/tests/autoconfig-sqlite.php $BASEDIR/config/autoconfig.php

# trigger installation
echo "INDEX"
php -f index.php
echo "END INDEX"

echo "Insert test users"
for USER in $USERS; do
	sqlite3 $DATADIR/owncloud.db "INSERT INTO oc_users (uid,displayname,password) VALUES ('$USER','$USER','x');"
done


echo "owncloud configuration:"
cat $BASEDIR/config/config.php

echo "data directory:"
ls -ll $DATADIR

echo "owncloud.log:"
#cat $DATADIR/owncloud.log

cd $BASEDIR
