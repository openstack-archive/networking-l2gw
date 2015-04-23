#!/bin/bash
# Copyright (c) 2015 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License

if [ $(id -u -r) -ne 0 ]
then
        echo "Requires root privileges. Please re-run using sudo."
        exit 1
fi
apt-get update -y
apt-get install devscripts -y
apt-get install debhelper -y
apt-get install dh-make -y
#read the package name and version,if not take default values and enter to
#debian/changelog file.
cd ..
if [ -f "debian/changelog" ]
then
   echo info for debian/changelog file
   echo enter package name for debian/changelog
   read pck
   sed -i 's/PACKAGE/'${pck:-networking-l2gw}'/' debian/changelog
   echo enter package version for debian/changelog
   read pck_ver
   sed -i 's/VERSION/'${pck_ver:-1.0}'/' debian/changelog
fi
#control file contains various values which dpkg, dselect, apt-get, apt-cache, aptitude,
#and other package management tools will use to manage the package.
#It is defined by the Debian Policy Manual, 5 "Control files and their fields".
if [ -f "debian/control" ]
then
    echo info for debian/control file
    echo enter the networking-l2gw source name
    read src_name
    echo enter the networking-l2gw package name
    read pck_name
    echo enter the version number
    read ver
    echo enter the maintainer info
    read maintainer_info
    echo enter the architecture
    read architecture
    echo enter the description title
    read description
    echo enter the description details
    read description_details
    sed -i 's/source/'${src_name:-networking-l2gw}'/' debian/control
    sed -i 's/package/'${pck_name:-networking-l2gw}'/' debian/control
    sed -i 's/version/'${ver:-1.0}'/' debian/control
    sed -i 's/maintainer/'${maintainer_info:-user@openstack}'/' debian/control
    sed -i 's/arch/'${architecture:-all}'/' debian/control
    sed -i 's/desc/'${description:-networking-l2gw}'/' debian/control
    sed -i 's/desc_details/'${description_details:-networking-l2gw}'/' debian/control
fi
#dpkg-buildpackage, build binary or source packages from sources.
#-b Specifies a binary-only build, no source files are to be built and/or distributed.
echo building debian package
dpkg-buildpackage -b
cd ../
if [ -z "$pck_name" ]
then
pck_name="networking-l2gw"
fi
if [ -z "$pck_ver" ]
then
pck_ver=1.0
fi
if [ -z "$architecture" ]
then
architecture="all"
fi
echo installing $pck_name\_$pck_ver\_$architecture.deb
dpkg -i  $pck_name\_$pck_ver\_$architecture.deb
echo enter neutron.conf file path
read neutron_conf
l2gw_plugin=", networking_l2gw.services.l2gateway.plugin.L2GatewayPlugin"
while read line
do
if [[ $line == *"service_plugins"* ]]
then
   if [[ $line != *$l2gw_plugin* ]]
   then
   serv_plugin=$line$l2gw_plugin
   sed -i "s|$line|$serv_plugin|" ${neutron_conf:-/etc/neutron/neutron.conf}
   fi
fi
done <${neutron_conf:-/etc/neutron/neutron.conf}
service neutron-server restart
