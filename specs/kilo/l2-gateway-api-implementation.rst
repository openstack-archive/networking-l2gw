..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
Implementation of L2 gateway APIs using OVSDB
===========================================================

Launchpad blueprint:

https://blueprints.launchpad.net/neutron/+spec/l2-gateway-api-implementation

The blueprint discloses one implementation of the L2 gateway APIs described in
https://review.openstack.org/144173
using the standard OVSDB hardware_vtep schema.

Problem Description
===================
Per the above specified URL, there is a proposal to represent an L2 gateway
(hardware or software) with logical resources in Neutron. It also defines
REST APIs in Neutron which will manage these resources.

The current spec discloses an implementation of these APIs.


Proposed Change
===============
The current spec proposes one implementation of the said REST APIs.
It makes use of the open standard OVSDB server underneath which
provides hardware_vtep schema to provision an L2 gateway.

The diagram below provides a high level overview of how the entire system
works.


Flows::

                            +–––––––––––––––––––––––––+
                            |                         |
                            |                         |
                            |      Neutron Server     |
                            |                         |
                    +-------+                         +-----+
                    |       |                         |     |
                    |       |                         |     |
                    |       |                         |     |
                    |       +–––––––––––––––––––––––––+     |
                    |                                       |
                    |                                       |
          +–––––––––+–––––––––––––––+          +––––––––––––+––––––––––––+
          |                         |          |                         |
          |                         |          |                         |
          |      ML2 Plugin         |          |      L2 Gateway         |
          |                         |   +------+      Service            |
          |                         |   |      |      Plugin             |
          |                         |   |      |                         |
          |                         |   |      |                         |
          +–––––––––+–––––––––––––––+   |      +–––––––––––––––––––––––––+
                    |                   |
                    |                   |
                    |                   |
                    |                   |
                    |                   |
                    |                   |
         +––––––––––+––––––––––––––+    |        +–––––––––––––––––––––––+
         |                         |    |        |    Monitoring         |
         |  Compute/Network Node   |    +--------+    L2 gateway agent   |
         |                         |    |        |                       +---+
         |                         |    |     +––––––––––––––––––––––+   |   |
         |                         |    |     |                      |   |   |
         +–––––––––––––––––––––––––+    +-----+   Transact           |–––+   |
                                              |   L2 gateway agent   |       |
                                              |                      +--+    |
                                              |                      |  |    |
                                              +––––––––––––––––––––––+  |    |
                                                                        |    |
                                                                        |    |
                                              +––––––––––––––––––––––+  |    |
                                              |                      |  |    |
                                              |                      +--+    |
                                              |     OVSDB            |  |    |
                                              |                      +--|----+
                                              |                      |  |    |
                                              |                      |  |    |
                                         +––––––––––––––––––––––+    |  |    |
                                         |                      |    |  |    |
                                         |                      |––––+  |    |
                                         |                      |       |    |
                                         |     OVSDB            +-------+    |
                                         |                      |            |
                                         |                      |            |
                                         |                      +------------+
                                         +––––––––––––––––––––––+


The L2 gateway service plugin transforms the REST APIs into Neutron RPCs
over the RabbitMQ bus to the proposed L2 gateway agents.

The RPCs from the plugin to an L2 gateway agent may include:
- A cast message to send details of virtual machines, compute node on which the
virtual machines are hosted and network details to the agent.
- A cast message to send the mapping of VXLAN segmentation ID of the specified
virtual network and VLAN ID on the physical network to the agent so that the
binding is created on the gateway device
- A cast message to send the mapping of VXLAN segmentation ID of the specified
virtual network and VLAN ID on the physical network to the agent so that the
binding is destroyed on the gateway device

An L2 gateway may be a physical switch, or a server with two NICs, or a
virtual machine with two virtual interfaces. In the first iteration,
we will support only a physical switch. Once the implementation is mature
and most of the use cases work, then anyone can enhance it for other
models.

An L2 gateway agent communicates with an OVSDB server over the OVSDB
protocol. The OVSDB server supports hardware_vtep database schema [2].
It does not matter for the agent where the OVSDB server runs, or the physical
gateway device runs.

Location of an L2 gateway agent is not tied to any node. It can run on any
system that is reachable by the neutron server and the OVSDB server.
Only one instance of L2 gateway agent can run on a node.

L2 gateway agent configuration
------------------------------
A configuration file, /etc/neutron/l2gateway_agent.ini will be placed
on the node on which the L2 gateway agent runs. This file contains the
information about which L2 gateway the agent is associated to
(as shown below).

# List of tuple ovsdb_name:ip:port
# ovsdb_hosts = foo1:foo_ip1:foo_port1, foo2:foo_ip2:foo_port2

# Below variables need to be set if secure connection is required
# between the L2 gateway agent and OVSDB server.

# If the agent wants a secure communication with the OVSDB server,
# then the following attributes are to be set

# Base path to private key file(s).
# Agent will find key file named
# $l2_gw_agent_priv_key_base_path/$ovsdb_name.key
l2_gw_agent_priv_key_base_path =

# Base path to cert file(s).
# Agent will find cert file named
# $l2_gw_agent_cert_base_path/$ovsdb_name.cert
l2_gw_agent_cert_base_path =

# Base path to ca cert file(s).
# Agent will find ca cert file named
# $l2_gw_agent_ca_cert_base_path/$ovsdb_name.ca_cert
l2_gw_agent_ca_cert_base_path =

foo_ip1 and foo_ip2 represent the IP addresses of the OVSDB
servers/L2 gateways that are to be managed by this agent.
foo_port1 and foo_port2 are the TCP ports on which the OVSDB servers are
listening to.


High Availability
-----------------
In order to support scale out model, multiple such L2 gateway agents may
run on different nodes and send their heartbeats to the neutron server.
Any agent can 'transact' with the OVSDB servers (active/active replication).
In this model, messages that come from the neutron server are casted to
any available agent at any given time.
Conversely, an agent needs to be notified by the OVSDB servers of events
that happen in the physical space. If all agents listened, there will be
duplicates, and therefore only have one agent can 'monitor' the OVSDB servers
at any given time (active/passive replication).
The service plugin scheduler component determines one of these agents as
the "monitoring" agent and the rest of the agents as "transact" agents.
The monitoring agent listens to the OVSDB server state change notifications
over the TCP socket specified in the l2gateway_agent.ini file.
The OVSDB notifications may include information of the L2 gateway device and
MAC addresses of the bare metal hosts that are learnt by the L2 gateway
device. The agent converts these notifications into RabbitMQ messages
(cast RPC) that are sent to the service plugin.
The service plugin may write the required information to the Neutron database,
and sends RPC messages (add/delete_fdb_entries) to the L2 agent on compute
and network nodes. This results in VXLAN tunnels from compute/network nodes
to the L2 gateway devices.

When a logical gateway is bound to a given virtual network in the command:
neutron l2-gateway-connection-create <gateway-name/uuid> <network-name/uuid>
[--default-segmentation-id=<seg-id>]

the outcome depends upon the following two scenarios described.

Scenario 1: The command is issued when virtual machines exist in the network
----------------------------------------------------------------------------
The service plugin prepares a list of MACs of all the virtual machines that
belong to the network, VMs' IPs, compute nodes' VTEP IPs and makes an RPC
call to the L2 gateway agents over the RabbitMQ message bus. In the RPC call,
it also sends the VXLAN ID-to-VLAN mapping.
One of the "transact" L2 gateway agents consumes this message from the bus.
The agent, in turn, updates the OVSDB tables with the binding information
(VXLAN ID-to-VLAN mapping in case of VXLAN networks), the new MAC addresses
(virtual machines) and the remote compute/network node IP which acts as a
remote VTEP IP. The L2 gateway, then creates a reverse VXLAN tunnel to the
compute nodes/network node's VTEP IP.

Scenario 2: The command is issued when the network does not have virtual
machines
------------------------------------------------------------------------
The service plugin sends the VXLAN ID-to-VLAN mapping in an RPC call over
the RabbitMQ bus. One of the "transact" L2 gateway agents consumes this
message from the bus. The agent, in turn, updates the OVSDB tables with
the binding information (VXLAN ID-to-VLAN mapping in case of VXLAN networks).
Later, when a virtual machine is spawned on this network, the service plugin
sends the MAC address of this VM along with its IP address, compute node's
VTEP IP in an RPC to the transact agents. One of the transact agents consumes
this message and updates the OVSDB tables with the information.
The L2 gateway, then creates a reverse VXLAN tunnel to the compute node.


Note: The plugin can either send one bulk message to a transact agent to
process, or split a request into multiple RPCs to the agents. This will
be taken care in the implementation.

L2 gateways are configured based on the information present in the OVSDB
tables.
This is left to each vendor how to configure the gateway based on the
information in the OVSDB tables.

If the "monitoring" agent dies due to some reason, the heartbeats from
the agent stop arriving at the neutron server. The service plugin, then
makes the L2 gateway agent that has sent the latest heartbeat as the
"monitoring" agent.

Note that the monitoring agent will read the entire OVSDB after it is
elected as the monitoring agent so that events are not missed.

Most typical agent failure modes will be kept in mind during the
implementation.

L2 gateway agents will be listed in the neutron agent-list command output.


Data Model Impact
-----------------
New tables representing OVSDB tables (hardware_vtep schema) [2] may be added in
the neutron DB:
- Ucast_Macs_Local table will be added that will represent details of bare
metal server on the physical side.
- Ucast_Macs_Remote table will be added that will represent details of the
virtual machines on the virtual side.
- Physical_Locator table will be added that will represent details of the
VTEPs (compute node, network node and physical side VTEPs aka gateway
devices)
- Physical_Switch table will be added that will represent details of the
gateway devices on the physical side
- Physical_Port table will be added that will represent details of the
physical interfaces of the gateway devices
- Logical_Switch table will be added that will represent details of the
virtual network (this is just a placeholder and we may not reqruire the
table when we come to the implementation as network information is already
kept inside the neutron tables)

L2 gateway agent information will be stored in the existing Agent
table model.


REST API Impact
---------------

None.


Security Impact
---------------

None.


Notifications Impact
--------------------
A cast message from the plugin to L2 gateway agents to send details of
virtual machines, compute node on which the virtual machines are hosted
and network details to the agent.

A cast message from the plugin to L2 gateway agents to send the mapping of
VXLAN segmentation ID of the specified virtual network and VLAN ID on the
physical network to the agent so that the binding is created on the gateway
device

A cast message from the plugin to L2 gateway agents to send the mapping of
VXLAN segmentation ID of the specified virtual network and VLAN ID on the
physical network to the agent so that the binding is destroyed on the gateway
device

A call message from the plugin to an L2 gateway agent to elect it as the
monitoring agent

A cast message from the monitoring agent to the plugin to notify OVSDB state
changes.


Other End User Impact
---------------------

The L2 gateway agent will be listed along with other agents in
"neutron agent-list" command output.

Performance Impact
------------------

None

IPv6 Impact
-----------

None


Other Deployer Impact
---------------------

There is no change in the existing compute node based L2 OpenVSwitch agent.
The proposed L2 gateway agent and existing L2 OpenVSwitch agent are two
different agents. The L2 gateway agent does not necessarily require
OpenVSwitch installation on that node. It may run on any node. However,
it interacts with a remote OVSDB server 2.3.x which supports hardware_vtep
schema.
If L2 gateway service is to be enabled, then it is required to configure
the L2 gateway service plugin and L2 gateway agent.

/etc/neutron.conf:
service_plugins=l2gw

Provider driver may be specified optionally,
service_provider=L2GW:l2gw:<driver>

Developer Impact
----------------
None.

Community Impact
----------------
With this approach, different vendors can implement the support for their
gateways as the implementation is solely based on a standard hardware_vtep
schema supported by the OVSDB. With this spec, we can bring legacy VLAN
networks into cloud which will help the community.

Alternatives
------------
An alternative solution would be to develop a mechanism with which the
service plugin can interact with a gateway over NetConf or similar
configuration protocols.
However, the benefit cannot be leveraged by all the vendors. In the
proposed architecture, as the open standard OVSDB "hardware_vtep"
schema is used, everyone's needs may be satisfied.

Implementation
==============

Assignee(s)
-----------

Maruti Kamat (marutik)
Selvakumar S (selvakumar-s2)
Vivekanandan Narasimhan (vivekanandan-narasimhan)
Phani Pawan (ppawan)
Koteswara Rao Kelam (koti-kelam)
Manjunath Patil (mpatil)
Vikas D M (vikas-d-m)
Ashish Kumar Gupta (ashish-kumar-gupta)
Alok Kumar Maurya (alok-kumar-maurya)
Preeti Mirji (preeti-mirji)

Work Items
----------

The work is split up into three parts:

1. Initiating L2 gateway RPCs by/to the service plugin over the
   RabbitMQ message bus.

2. Implementation of the L2 gateway agent

   * This will require development of L2 gateway agent that
     will communicate with the OVSDB server so as to integrate with the
     L2 gateway. The agent will communicate with
     the OVSDB server over a TCP socket.
     The L2 gateway agent will manage the L2 gateways as
     specified in the configuration (l2gateway_agent.ini).

Future work:
   - Instead of configuring the IP addresses of the L2 gateways
     inside the l2gateway_agent.ini file, a REST interface
     may be provided to the neutron server. This way,
     an administrator can dynamically specify the mapping
     (in JSON format) of which L2 gateways are to be managed
     by which L2 gateway agents.

3. Packaging of the implemented software and its deployment

Dependencies
============

* L2 gateway APIs https://review.openstack.org/144173

Testing
=======

Tempest Tests
-------------
Tempest test cases will be added.

Functional Tests
----------------
The testing will be performed in a setup with an OpenStack deployment
(devstack) connected to a L2 gateway agent that reads/writes into the OVSDB
hardware_vtep schema.
Hardware based switches can be tested by a third party CI infrastructure.
Every vendor that supports hardware_vtep schema should be able to validate the
solution independently irrespective of whether it is a software or a hardware
gateway.

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
OpenStack Neutron wiki needs to be updated

References
==========

[1] L2 gateway APIs https://review.openstack.org/144173
[2] OVSDB hardware_vtep schema http://openvswitch.org/docs/vtep.5.pdf
[3] VTEP emulator https://github.com/openvswitch/ovs/blob/master/vtep/README.ovs-vtep.md
