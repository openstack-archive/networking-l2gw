
===================================
Implementation of L2 Border Gateway
===================================



Problem Description
===================

The current implementation of the L2 Gateway connects bare metal servers
connected to hardware switch to OpenStack overlay tenant networks.

This spec propose an extension of the current functionality to a scenario where
two or more overlay networks running on two or more different OpenStack domains
(such as OpenStack instances, cells or regions) needs to be connected
in Layer 2.

The name - Border Gateway will be used in order to provide distinction between
the L2GW functionality, which is to connect overlay network to bare metal
servers and the functionality of the Border Gateway, which is to connect two or
more overlay networks that resides on different clouds.

The diagram below provides high level overview of the system components::

    +-------------------+
    |                   |             OpenStack A
    |                   |
    |  Computer Node    |                  +----------------+
    |                   |                  |                |
    |   +------------+  |  VXLAN Tunnel    | Border Gateway |   <---------+
    |   |   OVS      |  | <--------------> |                |             |
    |   +------------+  |                  +----------------+             |
    +-------------------+                                                 |
                                                                          |
                                                                 VXLAN    | WAN
                                                                 Tunnel   |
                                                                          |
    +-------------------+                                                 |
    |                   |             OpenStack B                         |
    |                   |                                                 |
    |  Computer Node    |                  +----------------+             |
    |                   |                  |                |             |
    |   +------------+  |  VXLAN Tunnel    | Border Gateway |   <---------+
    |   |   OVS      |  | <--------------> |                |
    |   +------------+  |                  +----------------+
    +-------------------+



Network Segmentation Handling
=============================

The connection between the Border Gateway and the internal overlay network is
unchanged and done by using the create gateway and create gateway-connection
commands. These commands actually creates logical switch in the physical switch
(L2GW device) and also create a tunnel from the logical switch to the OVS in
each Compute Node. The segmentation of the overlay networks is done using the
overlay network segmentation id. Each cloud manages its own segmentation id
and so the usage of single end-to-end segmentation id, which is translated to
VXLAN tunnel key, is hard to manage or even impossible.

To overcome this challenge, the Border Gateway uses different tunnel key
internally - to connect to each Compute Nodes, and externally - to connect the
two Border Gateways. When configuring end-to-end connection between the overlay
networks, the admin needs to make sure that the remote gateway connection uses
the same segmentation id on both sides on the WAN link, as the configuration of
the WAN tunnel is done on every Border Gateway separately.

Following is a diagram that provides overview of the different segmentation id
used by the Border Gateway::

                          OpenStack A
    +----------------+                    +----------------+
    | Compute Node 1 | ------------------ | Border Gateway |-----------------+
    +----------------+   Seg-ID 123       +----------------+  Seg-ID 456     |
           |                                    |                            |
           |  Seg-ID 123                        |                            |
    +----------------+                          |                            |
    | Compute Node 2 | -------------------------+                            |
    +----------------+   Seg-ID 123                                          |
                                                                             |
                                                                             |
                                                                             |
                          OpenStack B                                        |
    +----------------+                    +----------------+                 |
    |  Compute Node  | ------------------ | Border Gateway |-----------------+
    +----------------+   Seg-ID 789       +----------------+  Seg-ID 456


The segmentation id that is used in each cloud between each of the Compute Nodes
and the Border Gateway is handled by Neutron. When setting up gateway connection
using l2-gateway-connection-create command, a tunnel is created between a
logical switch in the Border Gateway and the OpenVSwitch in each Compute Node
with the same segmentation id as the tunnel key. In the diagram above you can
see segmentation ids 123 and 789 that are used for intra-cloud connection for
OpenStack A and OpenStack B respectively.

When setting up the connection between the Border Gateways, the admin need to
provide segmentation id to be used by each of the gateways to connect the
internal overlay network to the inter-cloud tunnel.

The inter-cloud connection command, l2-remote-gateway-connection-create, needs
to be run on the two Border Gateway while using the same segmentation id - 456
on both sides, in addition to the internal overlay network information.

When configuring the inter-cloud tunnel, the segmentation id is optional and
if not provided the tunnel between the Border Gateways will use the same
segmentation id on this link as the id used for Border Gateway to Compute Node
tunnels.


OVSDB Support
=============

The L2 Gateway project uses OVSDB's HARDWARE VTEP schema to configure the
hardware switches. The previous HARDWARE VTEP schema had a tunnel key parameter
in the Logical_Switch table, which leads to a situation where all tunnels that
connects to this logical switch would use the same tunnel id. The schema needs
to be updated so Physical_Locator table will also have tunnel key parameter
providing the ability to setup different tunnels the uses different tunnel key
while connecting to a single logical switch.

The tunnel setting will support hierarchical configuration in a way that if the
tunnel key is configured in the Physical_Locator table, it will be used for the
tunnel configuration, and if not, the tunnel key that is configured in the
Logical_Switch table will be used.


Tunnel Protocol Support
=======================

In the existing version, only VXLAN is supported as a tunnel protocol. The
limitation is not a technical one but the fact that the encapsulation_type
field in the Physical_Locator table is an enum with only one value:
vxlan_over_ipv4. In future releases, a multi tunnel protocol support can be
achieved with the different tunnel keys support for intra and inter cloud
tunnels explained above by adding additional values to the encapsulation_type
field. With these modifications, not only the inter-cloud and intra-cloud
tunnels will be able to use other protocols than VXLAN, but the Border Gateway
will be able to use different protocol for different connection (inter or intra
cloud connection).

Data Model Impact
-----------------

To support different segmentation id on each tunnel, a new column will be added
to physical_locators Neutron table.

Two Additional tables will be added to Neutron DB:

1. l2remotegateways table that will hold remote gateway information

2. l2remotegatewayconnections table that will hold configuration information
for remote gateway connection.


REST API Impact
---------------

API commands will be added for the following:

1. Create/Update/Delete/List/Show Remote Gateway configuration

2. Create/Delete/List/Show Remote Gateway Connection configuration

3. Create/Delete/List/Show Remote MAC configuration. This will enable adding
remote host switching information.

The above commands can be invoked by administrator or by special purpose
process.

See l2-border-gateway-api.rst document for more detailed information.


Security Impact
---------------

None.


Notifications Impact
--------------------

A cast message from the plugin to L2 gateway agents to create connection to
remote gateway for unknown MAC addresses. This will instruct the switch to
forward packets with unknown destination MAC addresses and broadcast
destination MAC to a connection to remote gateway.

A cast message from the plugin to L2 gateway agents to create remote MAC with
a remote gateway connection to be used for packet forwarding.


Performance Impact
------------------

None

IPv6 Impact
-----------

None

Dependencies
============

* L2 gateway APIs


Implementation
==============

Assignee(s)
-----------

Ofer Ben-Yacov (oferby)


Testing
=======

Tempest Tests
-------------

None

Functional Tests
----------------

None

API Tests
---------
None

Documentation Impact
====================

User Documentation
------------------

Functionality and configuration details will be documented


Developer Documentation
-----------------------
OpenStack Neutron wiki needs to be updated.
See here: https://wiki.openstack.org/wiki/Neutron/L2-GW


References
==========

API change request: https://bugs.launchpad.net/networking-l2gw/+bug/1529863
