Debian packaging and installation of neutron-l2gateway-agent.

Prior requirements
script install_l2gateway_agent.sh will run on neutron installed and configured nodes
(controller, compute and network nodes).

install_l2gateway_agent.sh will create and install debian package of networking-l2gw,
and it will start neutron-l2gateway-agent.

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

#info for neutron-l2gateway-agent.conf file
enter the networking-l2gw binary path
/usr/bin/neutron-l2gateway-agent
enter the neutron config file path
/etc/neutron/neutron.conf
enter the l2gateway agent config file path
/usr/etc/neutron/l2gateway_agent.ini
enter the l2gateway log file path
/var/log/neutron/l2gateway-agent.log

after execution of install_l2gateway_agent.sh check neutron-l2gateway-agent status

sudo service neutron-l2gateway-agent status
neutron-l2gateway-agent start/running, process 15276
