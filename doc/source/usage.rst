
========
Overview
========

.. _whatisl2gw:

1. What is L2 Gateway
=============================

L2 Gateway (L2GW) is an API framework for OpenStack that offers bridging two or more networks together to make them look at a
single broadcast domain. A typical use case is bridging the virtual with the physical networks

.. _model:

2. The L2GW model
=================

L2GW introduces a various models to describe the relationships between logical and the physical entities.

========================= ====================================================================
   Models                       Description
========================= ====================================================================
l2gateways                logical gateways that represents for the set of physical devices
l2gatewaydevices          l2 gateway devices that represents for logical gateways.
l2gatewayinterfaces       it represents the physical ports for the devices
l2gatewayconnections      represents connection between neutron network and the logical gateway

========================= =====================================================================

.. _usage:

3. L2GW NB API usage
=====================

L2GW NB REST API definitions are below,

3.1 Create l2gateway: neutron l2-gateway-create <l2gateway-name> --device name="<device_name>",interface_names=”<interface_name1>|[<segid1] ; <interface_name2>|[<segid2]”
Note : segid is an optional parameter , if it’s not provided while creating l2gateway , it needs to be provided while creating l2-gateway-connection

3.2 List l2gateways: neutron l2-gateway-list

3.3 Show l2gateway: neutron l2-gateway-show <l2gateway-id/l2gateway-name>

3.4 Delete l2gateway: neutron l2-gateway-delete <l2gateway-id/l2gateway-name>

3.5 Updatel2gateway: neutron l2-gateway-update <l2gateway-id/l2gateway-name> --name <new l2gateway-name> --device name=<device_name>,interface_names=”<interface_name1>|[<segid1] ; <interface_name2>|[<segid2]”

3.6 Create l2gateway-connection: neutron l2-gateway-connection-create <l2gateway-id > <network-id> --default-segmentation-id [seg-id]

3.7 List l2gateway-connection: neutron l2-gateway-connection-list

3.8 Show l2gateway-connection: neutron l2-gateway-connection-show <l2gateway-connection-id>

3.9 Delete l2gateway-connection: neutron l2-gateway-connection-delete <l2gateway-connection-id>

.. _l2gw_agent:

4. L2GW agent
=============
Configure the OVSDB parameters in /etc/neutron/l2gateway_agent.ini in case for openstack deployment.
Ex:
[ovsdb
ovsdb_hosts = ovsdb1:127.0.0.1:6632

In devstack local.conf will do a trick.(Refer - networking-l2gw/devstack/README.rst)
L2GW agent will be listed as part of “neutron agent-list”.
Details of L2GW Agent can be seen using “neutron agent-show <agent-id>” command
L2 Gateway Agent connects to ovsdb server to configure and fetch L2 Gateways

.. _l2gw_deployment:

5. L2GW Deployment
==================

.. image:: images/L2GW_deployment.png
           :height: 225px
           :width:  450px
           :align: center

For information on deploying L2GW refer networking-l2gw/doc/source/installation.rst  and  in devstack , networking-l2gw/devstack/README.rst
