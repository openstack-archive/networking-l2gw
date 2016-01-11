======================
 Enabling in Devstack
======================

1. Download DevStack

2. Add this repo as an external repository and configure following flags in ``local.conf``::

     [[local|localrc]]
     enable_plugin networking-l2gw https://github.com/openstack/networking-l2gw
     enable_service l2gw-plugin l2gw-agent
     OVSDB_HOSTS=<ovsdb_name>:<ip address>:<port>

3. If you want to override the default service driver for L2Gateway (which uses
L2Gateway Agent with RPC) with an alternative service driver, please give that
alternative service driver inside the parameter NETWORKING_L2GW_SERVICE_DRIVER
of your ``local.conf``.

For example, to configure ODL service driver to be used for L2Gateway,
you need to include ODL Service Driver in ``local.conf`` as below:

NETWORKING_L2GW_SERVICE_DRIVER=L2GW:OpenDaylight:networking_odl.l2gateway.driver.OpenDaylightL2gwDriver:default

3. Read the settings file for more details.

4. run ``stack.sh``
