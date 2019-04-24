===============
networking-l2gw
===============

API's and implementations to support L2 Gateways in Neutron.

* Free software: Apache license
* Source: https://opendev.org/openstack/networking-l2gw

L2 Gateways
-----------

This project proposes a Neutron API extension that can be used to express
and manage L2 Gateway components. In the simplest terms L2 Gateways are meant
to bridge two or more networks together to make them look at a single L2
broadcast domain.

Initial implementation
----------------------

There are a number of use cases that can be addressed by an L2 Gateway API.
Most notably in cloud computing environments, a typical use case is bridging
the virtual with the physical. Translate this to Neutron and the OpenStack
world, and this means relying on L2 Gateway capabilities to extend Neutron
logical (overlay) networks into physical (provider) networks that are outside
the OpenStack realm. These networks can be, for instance, VLAN's that may or
may not be managed by OpenStack.

More information
----------------

For help using or hacking on L2GW, you can send an email to the
`OpenStack Discuss Mailing List <mailto:openstack-discuss@lists.openstack.org>`;
please use the [L2-Gateway] Tag in the subject. Most folks involved hang out on
the IRC channel #openstack-neutron.

Getting started
---------------

To get started you have to install the l2gw plugin software on the Controller
node where you are already running the Neutron server. Then you need a new
node, that we call the l2gw node, where you do the actual bridging between a
vxlan tenant network and a physical network. The l2gw node could be a bare
metal switch that supports the OVSDB schema, or a server with OVS installed. In
this example we are going to use a server.

In this example the l2gw node has a `ens5` interface attached to a physical
segment, and a management interface with IP 10.225.0.27.

::

  ip link set up dev ens5
  apt-get install openvswitch-vtep
  ovsdb-tool create /etc/openvswitch/vtep.db /usr/share/openvswitch/vtep.ovsschema
  ovsdb-tool create /etc/openvswitch/vswitch.db /usr/share/openvswitch/vswitch.ovsschema
  ovsdb-server --pidfile --detach --log-file --remote ptcp:6632:10.225.0.27 \
               --remote punix:/var/run/openvswitch/db.sock --remote=db:hardware_vtep,Global,managers \
               /etc/openvswitch/vswitch.db /etc/openvswitch/vtep.db
  ovs-vswitchd --log-file --detach --pidfile unix:/var/run/openvswitch/db.sock
  ovs-vsctl add-br myphyswitch
  vtep-ctl add-ps myphyswitch
  vtep-ctl set Physical_Switch myphyswitch tunnel_ips=10.225.0.27
  ovs-vsctl add-port myphyswitch ens5
  vtep-ctl add-port myphyswitch ens5
  /usr/share/openvswitch/scripts/ovs-vtep \
               --log-file=/var/log/openvswitch/ovs-vtep.log \
               --pidfile=/var/run/openvswitch/ovs-vtep.pid \
               --detach myphyswitch

At this point your l2gw node is running.

For the configuration of the Openstack control plane you have to check three files:
``neutron.conf``, `l2gw_plugin.ini <https://github.com/openstack/networking-l2gw/blob/master/etc/l2gw_plugin.ini>`__, and `l2gateway_agent.ini <https://github.com/openstack/networking-l2gw/blob/master/etc/l2gateway_agent.ini>`__
Edit your ``neutron.conf`` on the controller node and make sure that in the ``service_plugins`` you have the string
``networking_l2gw.services.l2gateway.plugin.L2GatewayPlugin``.

You can add it with:
::

  sudo sed -ri 's/^(service_plugins.*)/\1,networking_l2gw.services.l2gateway.plugin.L2GatewayPlugin/' \
     /etc/neutron/neutron.conf

Make sure the neutron-server runs with ``--config-file=/etc/neutron/l2gw_plugin.ini``.
The default for the l2gw_plugin.ini file should be okay.

Now you are ready to create the database tables for the neutron l2gw plugin using the command:
``neutron-db-manage upgrade heads``

The file `l2gateway_agent.ini <https://github.com/openstack/networking-l2gw/blob/master/etc/l2gateway_agent.ini>`__ is used to configure the neutron-l2gateway agent.
The agent is the piece of software that will configure the l2gw node when you interact with the Openstack API.
Here it is important to give the pointer to the switch.
``ovsdb_hosts = 'ovsdb1:10.225.0.27:6632'``

The name ``ovsdb1`` is just a name that will be used in the Openstack database to identify this switch.

Now that both the l2gw node and the Openstack control plane are configured, we can use the API service to bridge a VXLAN tenant network to a physical interface of the l2gw node.

First let's create in Openstack a l2-gateway object. We need to give the interface names and the name of the bridge that we used before in the OVS commands.

``l2-gateway-create --device name="myphyswitch",interface_names="ens5" openstackname``

Use the <GATEWAY-NAME/UUID> just created to feed the second command where you do the actual bridging between the VXLAN tenant network and the Physical L2 network.

``l2-gateway-connection-create <GATEWAY-NAME/UUID> <NETWORK-NAME/UUID>``

Now let's see what happened. On the l2gw node you can do the commands:
::

  ovs-vsctl show
  vtep-ctl show

You should see some VXLAN tunnels are created. You will see a vxlan tunnel to each compute node that is hosting an
instance attached to the tenant network that you bridge. If there is also a router in this tenant network,
you will find a VXLAN tunnel also to the network node.

References:
 * http://networkop.co.uk/blog/2016/05/21/neutron-l2gw/
 * http://kimizhang.com/neutron-l2-gateway-hp-5930-switch-ovsdb-integration/
 * http://openvswitch.org/support/dist-docs-2.5/vtep/README.ovs-vtep.md.html
