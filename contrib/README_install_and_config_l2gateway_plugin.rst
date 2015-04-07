Debian packaging, installation and configuration of
neutron-l2gateway plugin.

Prior requirements
script install_and_config_l2gateway_plugin.sh will run on openstack controller.

install_and_config_l2gateway_plugin.sh will create and install debian package of networking-l2gw,
and it will enable neutron-l2gateway service plugin.

Creation of debian package requires copyright, changelog, control, compat
and rules file inside the debian folder.
debian folder is to be placed inside the folder which needs to be packaged (networking-l2gw).
command dpkg-buildpackage -b, builds debian package of networking-l2gw which uses the files
mentioned inside debian folder to create debian package.

please refer https://www.debian.org/doc/manuals/maint-guide/dreq.en.html
for further details.

Installation procedure example:

The script will ask for further details for packaging and installing as shown below.
press ENTER for assigning default values to debian/changelog and debian/control file.

#info for debian/changelog file
enter package name for debian/changelog
networking-l2gw
enter package version for debian/changelog
1.0

#info for debian/control file
enter the networking-l2gw source name
networking-l2gw
enter the networking-l2gw package name
networking-l2gw
enter the version number
1.0
enter the maintainer info
user@hp.com
enter the architecture
all
enter the description title
l2gateway package
enter the description details
description details of l2gateway package

#info of neutron.conf file path
press ENTER for assigning default file path /etc/neutron/neutron.conf for neutron.conf file.
enter neutron.conf file path
/etc/neutron/neutron.conf

after execution of install_and_config_l2gateway_plugin.sh
check neutron-server status.

sudo service neutron-server status
neutron-server start/running, process 17876

and also check service_plugins in neutron.conf file whether 
networking_l2gw.services.l2gateway.plugin.L2GatewayPlugin is enabled or not.
