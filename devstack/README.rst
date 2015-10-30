======================
 Enabling in Devstack
======================

1. Download DevStack

2. Add this repo as an external repository:

     > cat local.conf
     [[local|localrc]]
     enable_plugin networking-l2gw https://github.com/openstack/networking-l2gw
     enable_service l2gw-plugin l2gw-agent
     OVSDB_HOSTS=<ovsdb_name>:<ip address>:<port>
     Q_PLUGIN_EXTRA_CONF_PATH=/etc/neutron
     Q_PLUGIN_EXTRA_CONF_FILES=(l2gw_plugin.ini)


3. run ``stack.sh``
