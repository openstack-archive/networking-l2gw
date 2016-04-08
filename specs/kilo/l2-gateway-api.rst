..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============
L2 Gateway API
==============

This 'manifesto' introduces a Neutron API extension that can be used to express
and manage L2 Gateway components. In the simplest terms L2 Gateways are meant
to bridge two or more networks together to make them look at a single L2
broadcast domain.

The are a number of use cases that can be addressed by an L2 Gateway API. Most
notably in cloud computing environments, a typical use case is bridging the
virtual with the physical. Translate this to Neutron and the OpenStack world,
and this means relying on L2 Gateway capabilities to extend Neutron logical
(overlay) networks into physical (provider) networks that are outside the
OpenStack realm. These networks can be, for instance, VLAN's that may or may
not be managed by OpenStack.

To fix ideas, we are going to present this API assuming the afore-mentioned
use case is going to be tackled initially, and we are going to use VXLAN and VLAN
as the two L2 segmentation technologies being bridged by an L2 Gateway. How these
L2 Gateway components are going to be implemented (either in software or hardware)
is outside the scope of this document, and will be discussed elsewhere.

Proposed Approach
=================

This specification tries to expose enough details so that API is flexible enough to
allow implementers to map logical gateways to the physical ones the way they see fit.
This implies that the API could be implemented with physical gateway, software gateway,
and/or different bridging mechanisms, details of which are deferred to the implementation.

The below diagram depicts that the API will be implemented  in the proposed service
plugin just like other Neutron API extensions.

diagram::

                            +–––––––––––––––––––––––––+
                            |                         |
                            |                         |
                            |      Neutron Server     +-----+
                            |                         |     |
                            |                         |     |
                            |                         |     |
                            +–––––––––––––––––––––––––+     |
                                                            |
                                                            |
                                               +––––––––––––+––––––––––––+
                                               |                         |
                                               |      L2 Gateway         |
                                               |      Service            |
                                               |      Plugin             |
                                               |                         |
                                               |                         |
                                               +–––––––––––––––––––––––––+


L2 gateway service plugin is proposed, which provides REST interfaces to
support the following use cases:

Note: These commands/APIs can be executed only by the admin users.

1. Creating an abstraction of an L2 gateway with its interface(s).
   That is, creation of a logical gateway.
   e.g.,
   neutron l2-gateway-create <gateway-name>
   --device name=<device-name1>,interface_names=<interface-name1>[:<seg-id1>];
   <interface-name2>[:<seg-id2>,<seg-id3>]
   --device name=<device-name2>,interface_names=<interface-name1>[:<seg-id1>];
   <interface-name2>[:<seg-id2>,<seg-id3>]

   where seg-id is optional,
   gateway-name is a descriptive name for the logical gateway,
   device-name1 and device-name2 are the names or identifiers of the
   L2 gateways.
   interface-name1 and interface-name2 ... interface-nameN are interfaces on
   the gateways.
   seg-id indicates the segmentation identifier of the physical network to
   which the interfaces belong to.

2. Updating a logical gateway

   neutron l2-gateway-update <gateway-name> --device name=<existing-device>
   [--add-interface=<new-interface-name>:<segmentation-ids-with-commas>]
   [--remove-interface=<existing-interface-name>]

3. Deletion of a logical gateway
   neutron l2-gateway-delete <gateway-name/uuid>

4. List all the logical gateways
   neutron l2-gateway-list

5. Show details of a logical gateway
   neutron l2-gateway-show <gateway-name/uuid>

6. Binding a logical gateway to an overlay network.
   neutron l2-gateway-connection-create <gateway-name/uuid> <network-name/uuid>
   [--default-segmentation-id=<seg-id>]

   Note:
   a. We will support specifying a list of networks in this command in
   future.
   b. We will add --segmentation-type option in future to support other
   bridging mechanisms like FLAT

   <network-name> is the name of the neutron network.

   --default-segmentation-id indicates the default segmentation-id that will
   be applied to the interfaces for which segmentation id was not specified
   in l2-gateway-create command.

   Outcome: <connection-uuid> <neutron_net_uuid> <gateway_uuid>

   Support for multi-segmented networks is out of scope of this spec.
   For the time being, if a network consists of more than one segment, then it
   will throw an error.

7. Listing connections
   neutron l2-gateway-connection-list

8. Show details of a connection
   neutron l2-gateway-connection-show <connection-uuid>

9. Destroying binding between neutron network and the VLAN
   neutron l2-gateway-connection-delete <connection-uuid>

Data Model Impact
-----------------
The following four tables will be introduced.

l2gateways:
+-----------+--------------+------+-----+---------+-------+
| Field     | Type         | Null | Key | Default | Extra |
+-----------+--------------+------+-----+---------+-------+
| id        | varchar(36)  | NO   | PRI | NULL    |       |
| name      | varchar(255) | YES  |     | NULL    |       |
| tenant_id | varchar(36)  | YES  |     | NULL    |       |
+-----------+--------------+------+-----+---------+-------+

l2gatewaydevices:
+--------------------+-------------+------+-----+---------+-------+
| Field              | Type        | Null | Key | Default | Extra |
+--------------------+-------------+------+-----+---------+-------+
| id                 | varchar(36) | NO   | PRI | NULL    |       |
| device_name        | varchar(36) | NO   | PRI | NULL    |       |
| l2_gateway_id      | varchar(36) | NO   | FOR | NULL    |       |
+--------------------+-------------+------+-----+---------+-------+

l2gatewayinterfaces:
+--------------------+-------------+------+----------+---------+-------+
| Field              | Type        | Null | Key      | Default | Extra |
+--------------------+-------------+------+----------+---------+-------+
| id                 | varchar(36) | NO   | PRI      | NULL    |       |
| interface_name     | varchar(36) | NO   | MUL      | NULL    |       |
| device_id          | varchar(36) | NO   | FOR, MUL | NULL    |       |
| segmentation_id    | int(11)     | YES  |          | NULL    |       |
+--------------------+-------------+------+----------+---------+-------+


networkconnections:
+--------------------+---------------------+------+-----+---------+-------+
| Field              | Type                | Null | Key | Default | Extra |
+--------------------+---------------------+------+-----+---------+-------+
| id                 | varchar(36)         | NO   | PRI | NULL    |       |
| tenant_id          | varchar(255)        | YES  |     | NULL    |       |
| l2_gateway_id      | varchar(36)         | YES  | MUL | NULL    |       |
| network_id         | varchar(36)         | YES  | MUL | NULL    |       |
| port_id            | varchar(36)         | NO   | PRI | NULL    |       |
+--------------------+---------------------+------+-----+---------+-------+


REST API Impact
---------------
New REST resources are shown below.

l2gateways:

+-----------+--------------+---------+---------+--------------+
|Attribute  |Type          |Access   |Default  |Description   |
|Name       |              |         |Value    |              |
+===========+==============+=========+=========+==============+
|id         |string        |CRD      |generated|identity      |
|           |(UUID)        |         |         |              |
+-----------+--------------+---------+---------+--------------+
|tenant id  |string        |CRUD     |         |              |
|           |(UUID)        |         |         |              |
+-----------+--------------+---------+---------+--------------+
|name       |string        |CRUD     |''       |              |
|           |              |         |         |              |
+-----------+--------------+---------+---------+--------------+
|devices    |list of       |CRUD     |[]       |              |
|           |dicts         |         |         |              |
|           |for devices   |         |         |              |
|           |and interfaces|         |         |              |
|           |              |         |         |              |
+-----------+--------------+---------+---------+--------------+

Note: In "devices" attribute, existing device can be updated
to add/remove interface only.


networkconnections:

+-------------------+-------+---------+---------+--------------+
|Attribute          |Type   |Access   |Default  |Description   |
|Name               |       |         |Value    |              |
+===================+=======+=========+=========+==============+
|id                 |string |CRD      |generated|connectionuuid|
|                   |(UUID) |         |         |              |
+-------------------+-------+---------+---------+--------------+
|l2                 |string |CRD      |         |              |
|gateway id         |(UUID) |         |         |              |
+-------------------+-------+---------+---------+--------------+
|network id         |string |         |         |              |
|                   | (UUID)|CRD      |         |              |
+-------------------+-------+---------+---------+--------------+
|port_id            |UUID   |CRD      |         |              |
+-------------------+-------+---------+---------+--------------+
|default            | int   |C        |         |              |
|segmentation_id    |       |         |         |              |
+-------------------+-------+---------+---------+--------------+

The following new REST APIs will be introduced.

1. neutron l2-gateway-create <gateway-name>
   --device name=<device-name1>,interface_names=<interface-name1>[:<seg-id1>];
   <interface-name2>[:<seg-id2>,<seg-id3>]
   --device name=<device-name2>,interface_names=<interface-name1>[:<seg-id1>];
   <interface-name2>[:<seg-id2>,<seg-id3>]

JSON Request

::

    POST /v2/l2-gateways
    Content-Type: application/json
    {"l2_gateway": {"name": "<gateway-name>",
                    "devices": [{"device_name": "<device-name1>",
                                 "interfaces": [{"name":"<interface-name1>",
                                                 "segmentation-id":[<seg-id1>]},
                                                {"name":"<interface-name2>",
                                                 "segmentation-id":[<seg-id2>,
                                                                    <seg-id3>]}]
                                },
                                {"device_name": "<device-name2>",
                                 "interfaces": [{"name":"<interface-name1>",
                                                 "segmentation-id":[<seg-id1>]},
                                                {"name":"<interface-name2>",
                                                 "segmentation-id":[<seg-id2>,
                                                                    <seg-id3>]}]
                                }]}}

Response:

::

    {"l2_gateway": {"name": "<gateway-name>",
                    "tenant_id": "7ea656c7c9b8447494f33b0bc741d9e6",
                    "devices": [{"device_name": "<device-name1>",
                                 "interfaces": [{"name":"<interface-name1>",
                                                 "segmentation-id":[<seg-id1>]},
                                                {"name":"<interface-name2>",
                                                 "segmentation-id":[<seg-id2>,
                                                                    <seg-id3>]}]
                                },
                                {"device_name": "<device-name2>",
                                 "interfaces": [{"name":"<interface-name1>",
                                                 "segmentation-id":[<seg-id1>]},
                                                {"name":"<interface-name2>",
                                                 "segmentation-id":[<seg-id2>,
                                                                    <seg-id3>]}]
                                }],
                    "id": "d3590f37-b072-4358-9719-71964d84a31c"}}

Normal Response Code(s): Created (201)
Error Response Code(s):  Standard http error codes


2. neutron l2-gateway-update <gateway-name> --device name=<existing-device>
   [--add-interface=<new-interface-name>:<segmentation-ids-with-commas>]
   [--remove-interface=<existing-interface-name>]


JSON Request

::

    POST /v2/l2-gateways
    Content-Type: application/json
    {"l2_gateway": {"name": "<gateway-name>",
                    "devices": [{"device_name": "<existing-device>",
                                 "new_interfaces": [{"name":"<new-interface-name>",
                                                     "segmentation-id":[<seg-id>]}]
                                },
                                 "deleted_interfaces": [{"name":"<interface-name>"}]
                               ]}}

Response:

::

    {"l2_gateway": {"name": "<gateway-name>",
                    "tenant_id": "7ea656c7c9b8447494f33b0bc741d9e6",
                    "devices": [{"device_name": "<device-name1>",
                                 "interfaces": [{"name":"<interface-name1>",
                                                 "segmentation-id":[<seg-id1>]},
                                                {"name":"<interface-name2>",
                                                 "segmentation-id":[<seg-id2>,
                                                                    <seg-id3>]}]
                                },
                                {"device_name": "<device-name2>",
                                 "interfaces": [{"name":"<interface-name1>",
                                                 "segmentation-id":[<seg-id1>]},
                                                {"name":"<interface-name2>",
                                                 "segmentation-id":[<seg-id2>,
                                                                    <seg-id3>]}]
                                }],
                    "id": "d3590f37-b072-4358-9719-71964d84a31c"}}

Normal Response Code(s): Created (200)
Error Response Code(s):  Standard http error codes

2. neutron l2-gateway-connection-create <gateway-name/uuid> <network-name/uuid>
   [--default-segmentation-id=<seg-id>]

::

    JSON Request
    POST /v2/l2-gateway-connections
    Content-Type: application/json
    {"network_id": "591ffe08-f8f5-44c1-85c1-1026878f69bd",
     "default_segmentation_id": <seg-id>,
     "gateway_id": "d3590f37-b072-4358-9719-71964d84a31c"
    }

    Response:
    {"tenant_id": "7ea656c7c9b8447494f33b0bc741d9e6",
     "connection_id": "<connection-uuid>",
     "network_id": "591ffe08-f8f5-44c1-85c1-1026878f69bd",
     "default_segmentation_id": <seg-id>,
     "gateway_id": "d3590f37-b072-4358-9719-71964d84a31c",
     "port_id": "9ea656c7c9b8447494f33b0bc741d9a9"
    }

Normal Response Code(s): Created (201)

Error Response Code(s):  Standard http error codes


3. neutron l2-gateway-connection-list

::

    JSON Request
    GET /v2/l2-gateway-connections
    Content-Type: application/json
    Response:
    {"l2_gateway_connections": [{"connection_id": "<connection-uuid>",
    "tenant_id": "7ea656c7c9b8447494f33b0bc741d9e6",
    "network_id":
    "e5062ab3-b120-41b2-b138-dc5d2fcaf216",
    "default_segmentation_id": <seg-id>,
    "gateway_id":
    "d3590f37-b072-4358-9719-71964d84a31c",
    "port_id": "9ea656c7c9b8447494f33b0bc741d9a9"}]
    }
    Normal Response Code(s):  OK (200)
    Error Response Code(s):  Standard http error codes


4. neutron l2-gateway-connection-show <connection-uuid>

::

    JSON Request
    GET /v2/l2-gateway-connections/<connection-uuid>
    Content-Type: application/json
    Response:
    {"connection_id" : "<connection-uuid>",
    "tenant_id": "7ea656c7c9b8447494f33b0bc741d9e6",
    "network_id": "e5062ab3-b120-41b2-b138-dc5d2fcaf216",
    "default_segmentation_id": <seg-id>,
    "gateway_id": "d3590f37-b072-4358-9719-71964d84a31c",
    "port_id": "9ea656c7c9b8447494f33b0bc741d9a9"
    }

Normal Response Code(s):  OK (200)
Error Response Code(s):  Standard http error codes


5. neutron l2-gateway-list

::

    JSON Request
    GET /v2/l2-gateways
    Content-Type: application/json
    Response:
    {"l2_gateways": [{"name": "<gateway-name>",
                      "tenant_id": "7ea656c7c9b8447494f33b0bc741d9e6",
                      "devices": [{"device_name": "<device-name1>",
                                   "interfaces": [{"name":"<interface-name1>",
                                                   "segmentation-id":[<seg-id1>]},
                                                  {"name":"<interface-name2>",
                                                   "segmentation-id":[<seg-id2>,
                                                                      <seg-id3>]}]
                                  },
                                  {"device_name": "<device-name2>",
                                   "interfaces": [{"name":"<interface-name1>",
                                                   "segmentation-id":[<seg-id1>]},
                                                  {"name":"<interface-name2>",
                                                   "segmentation-id":[<seg-id2>,
                                                                      <seg-id3>]}]
                                  }],
                      "id": "d3590f37-b072-4358-9719-71964d84a31c"}]}


Normal Response Code(s):  OK (200)
Error Response Code(s):  Standard http error codes


6. neutron l2-gateway-show <gateway-name/uuid>

::

    JSON Request
    GET /v2/l2-gateways/<uuid>
    Content-Type: application/json
    Response:
    {"l2_gateway": {"name": "<gateway-name>",
                    "tenant_id": "7ea656c7c9b8447494f33b0bc741d9e6",
                    "devices": [{"device_name": "<device-name1>",
                                 "interfaces": [{"name":"<interface-name1>",
                                                 "segmentation-id":[<seg-id1>]},
                                                {"name":"<interface-name2>",
                                                 "segmentation-id":[<seg-id2>,
                                                                    <seg-id3>]}]
                                },
                                {"device_name": "<device-name2>",
                                 "interfaces": [{"name":"<interface-name1>",
                                                 "segmentation-id":[<seg-id1>]},
                                                {"name":"<interface-name2>",
                                                 "segmentation-id":[<seg-id2>,
                                                                    <seg-id3>]}]
                                }],
                    "id": "d3590f37-b072-4358-9719-71964d84a31c"}
    }

Normal Response Code(s):  OK (200)
Error Response Code(s):  Standard http error codes


7. neutron l2-gateway-connection-delete <connection-uuid>

::

    JSON Request
    DELETE /v2/l2-gateway-connections/<connection-uuid>
    Content-Type: application/json
    Response: null
    Normal Response Code(s):  No content (204)
    Error Response Code(s):  Standard http error codes


8. neutron l2-gateway-delete <gateway-name/uuid>

::

    JSON Request
    DELETE /v2/l2-gateways/<uuid>
    Content-Type: application/json
    Response:
    null

Normal Response Code(s):  No content (204)
Error Response Code(s):  Standard http error codes


Typical workflow using the proposed REST APIs
---------------------------------------------
Consider a cloud administrator has identified a physical gateway
with hostname 'gatewayhost' with physical interfaces port1, port2,
.... portN which s/he can use to leverage services like a legacy database
server, an edge firewall, etc. residing on bare metal hosts.
Consider that port1 and port2 belong to VLAN 100
on the physical side, to which bare metal hosts BM1 and BM2 are connected.
The administrator can then execute the following commands to interconnect
the existing virtual machines in the cloud with the bare metal hosts.

1. The administrator creates a logical gateway 'gw1' representing the hardware
gateway device 'gatewayhost' and its interfaces port1 and port2.

neutron l2-gateway-create gw1
--device name=gatewayhost,interface_names=port1;port2

This just creates an entry in the Neutron database.

Flow::

                            +–––––––––––––––––––––––––+
                            |                         |
                            |                         |
                            |      Neutron Server     +-----+
                            |                         |     |
                            |                         |     |
                            |                         |     |
                            +–––––––––––––––––––––––––+     |
                                                            |
                                                           \|/
                                               +––––––––––––+––––––––––––+
                                               |                         |
                                               |      L2 Gateway         |
                                               |      Service            |
                                               |      Plugin             |
                                               |                         |
                                               |                         |
                                               +––––––––––––+––––––––––––+
                                                            |
                                                           \|/
                                               +––––––––––––+––––––––––––+
                                               |                         |
                                               |      Neutron DB         |
                                               |                         |
                                               |                         |
                                               +–––––––––––––––––––––––––+



Note: From steps 2 to 8, Neutron server is not shown for convenience.

2. The administrator binds an existing VXLAN network 'net1' with the VXLAN ID
1000 (I.e. provider:network_type=VXLAN, provider:segmentation_id=1000)
with this logical gateway gw1.

neutron l2-gateway-connection-create gw1 net1 --default-segmentation-id=100

As the segmentation ID was not specified in the gateway creation time, the
default segmentation ID 100 is used for both the interfaces, port1 and port2.

The service plugin builds the following:
- MAC addresses of all the virtual machines of the network net1
- IP addresses of the virtual machines
- VTEP IP of the compute nodes which host the virtual machines
- VXLAN-VLAN binding, that is 1000=100

and sends it to the underlying implementation.

The underlying implementation configures the physical gateway with
the above information.

Flow::

         +–––––––––––––––––––––––––+
         |                         |
         |      L2 Gateway         |
         |      Service            |
         |      Plugin             |
         |                         |
         |                         |
         +––––––––––––+––––––––––––+
                      |
                      |
                      +-------------------------------------+
                                                            |
                                                           \|/
                                               +––––––––––––+––––––––––––+
                                               |                         |
                                               |    Physical Gateway     |
                                               |                         |
                                               |                         |
                                               +–––––––––––––––––––––––––+


As the physical gateway now knows the VTEP IP of the compute nodes, it creates
VXLAN tunnels to the compute nodes.


Flow::


 +––––––––––––+––––––––––––+                    +––––––––––––+––––––––––––+
 |                         |/                   |                         |
 |    Compute Node         +--------------------+    Physical Gateway     |
 |                         |\                   |                         |
 |                         |                    |                         |
 +–––––––––––––––––––––––––+                    +–––––––––––––––––––––––––+



3. The underlying implementation sends information of the physical gateway's VTEP
IP address, MAC addresses of the bare metal hosts and their IP addresses to the
service plugin.

Flow::

         +–––––––––––––––––––––––––+
         |                         |
         |      L2 Gateway         |
         |      Service            |
         |      Plugin             |
         |                         |
         |                         |
         +––––––––––––+––––––––––––+
                     /|\
                      |
                      +-------------------------------------+
                                                            |
                                                            |
                                               +––––––––––––+––––––––––––+
                                               |                         |
                                               |    Physical Gateway     |
                                               |                         |
                                               |                         |
                                               +–––––––––––––––––––––––––+


4. The service plugin sends this information to the compute nodes.

Flow::

         +–––––––––––––––––––––––––+
         |                         |
         |      L2 Gateway         |
         |      Service            |
         |      Plugin             |
         |                         |
         |                         |
         +––––––––––––+––––––––––––+
                      |
                      |
                +-----+
                |
               \|/
   +––––––––––––+––––––––––––+
   |                         |
   |    Compute Node         |
   |                         |
   |                         |
   +–––––––––––––––––––––––––+


5. The compute nodes create reverse VXLAN tunnels to the physical gateway.

Flow::

 +–––––––––––––––––––––––––+                    +–––––––––––––––––––––––––+
 |                         |/                   |                         |
 |                         +--------------------+                         |
 |                         |\                  \|
 |    Compute Node         +--------------------+    Physical Gateway     |
 |                         |                   /|                         |
 |                         |                    |                         |
 +–––––––––––––––––––––––––+                    +–––––––––––––––––––––––––+


6. Hereafter, any number of new virtual machines that are created
on this compute node on this network (net1), do not impact the VXLAN tunnel
that originated from the gateway and terminated at the compute node.
They can use the existing the tunnel to send/receive the data traffic.

7. Similarly, any number of new bare metal servers connected to the interfaces
port1 and port2 do not impact the VXLAN tunnel that originated from the
compute node and terminated at the gateway.
They can use the existing the tunnel to send/receive the data traffic.

8. Only when the last virtual machine on the compute node for the network net1
is destroyed, the plugin instructs the gateway to destroy the VXLAN tunnel to
the compute node as it is no longer needed.

9. Similarly, if all the bare metal servers connected to interfaces port1
and port2 are disconnected, then the plugin instructs the compute node
to destroy the VXLAN tunnel to the gateway as it is no longer needed.

10. In a case where the VXLAN tunnel exists between the compute node and
the gateway when there is at least one virtual machine on the compute node
on network net1 and at least one bare metal server on the gateway, the
administrator may still want to destroy the VXLAN tunnel between
the compute node and the gateway. This can be done using the below
command.

neutron l2-gateway-connection-delete connection-uuid

The underlying implementation deletes the below information from the
physical gateway:
- MAC addresses of all the virtual machines of the network net1
- IP addresses of the virtual machines
- VTEP IP of the compute nodes which host the virtual machines
- VXLAN-VLAN binding, that is 1000=100.

Flow::

         +–––––––––––––––––––––––––+
         |                         |
         |      L2 Gateway         |
         |      Service            |
         |      Plugin             |
         |                         |
         |                         |
         +––––––––––––+––––––––––––+
                      |
                      |
                      +-------------------------------------+
                                                            |
                                                           \|/
                                               +––––––––––––+––––––––––––+
                                               |                         |
                                               |    Physical Gateway     |
                                               |                         |
                                               |                         |
                                               +–––––––––––––––––––––––––+


11. As the binding is destroyed, the physical gateway destroys the VXLAN
tunnels to the compute nodes.

Flow::


 +–––––––––––––––––––––––––+                    +–––––––––––––––––––––––––+
 |                         |                    |                         |
 |                         |                    |                         |
 |                         |                   \|                         |
 |    Compute Node         +--------------------+    Physical Gateway     |
 |                         |                   /|                         |
 |                         |                    |                         |
 +–––––––––––––––––––––––––+                    +–––––––––––––––––––––––––+


12. The service plugin informs the compute nodes to destroy the VXLAN tunnels
to the physical gateway

Flow::


 +–––––––––––––––––––––––––+                    +–––––––––––––––––––––––––+
 |                         |                    |                         |
 |                         |                    |                         |
 |                         |                    |                         |
 |    Compute Node         |                    |    Physical Gateway     |
 |                         |                    |                         |
 |                         |                    |                         |
 +–––––––––––––––––––––––––+                    +–––––––––––––––––––––––––+


13. The administrator deletes the logical gateway gw1 if it is not required
any longer.

neutron l2-gateway-delete gw1

This removes entry of gw1 from the Neutron database.

Flow::

                            +–––––––––––––––––––––––––+
                            |                         |
                            |                         |
                            |      Neutron Server     +-----+
                            |                         |     |
                            |                         |     |
                            |                         |     |
                            +–––––––––––––––––––––––––+     |
                                                            |
                                                           \|/
                                               +––––––––––––+––––––––––––+
                                               |                         |
                                               |      L2 Gateway         |
                                               |      Service            |
                                               |      Plugin             |
                                               |                         |
                                               |                         |
                                               +––––––––––––+––––––––––––+
                                                            |
                                                           \|/
                                               +––––––––––––+––––––––––––+
                                               |                         |
                                               |      Neutron DB         |
                                               |                         |
                                               |                         |
                                               +–––––––––––––––––––––––––+


Security Impact
---------------
None

Notifications Impact
--------------------

Impact depends upon the underlying implementation of the REST APIs.

Other End User Impact
---------------------

Python-neutronclient will invoke the APIs.

Performance Impact
------------------
None

IPv6 Impact
-----------
None

Other Deployer Impact
---------------------

If L2 gateway service is to be enabled, then it is required to configure
the L2 gateway service plugin in neutron.conf.

/etc/neutron.conf:
service_plugins=l2gw

Provider driver may be specified optionally,
service_provider=L2GW:l2gw:<driver>

Developer Impact
----------------
None

Community Impact
----------------
The spec does not impose a restriction on the implementation. It is
left to the party who wants to support its own gateway (hardware or software)
with whatever mechanism it wants to implement.
This way, we can bring legacy VLAN networks into cloud which will help the
community.

Alternatives
------------
An alternative solution would be to develop a monolithic vendor plugin.
However, the benefit cannot be leveraged by all the vendors.
Another advantage is that no major change in the existing ML2
plugin is required.

Other alternatives:
1. https://review.openstack.org/#/c/93613

This can be achieved by the APIs proposed in the current spec by providing
an option to specify other segmentation types in future.


2. https://review.openstack.org/#/c/136555
The spec does not support different segmentation types.
On the other hand, the current spec can add an option in future to support
different segmentation types.
With the current spec, it is possible to connect a virtual network to multiple
gateways.
The current spec also addresses a problem where different overlay networks
like VXLAN, GRE, etc. can communicate with VLAN networks. This helps in
intercommunication between two different overlay network types with an L2
gateway in between.
Another advantage of the current spec is that with the same set of APIs, it can
support both the types of gateways (hardware as well as software).

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
(Please add your name and launchpad ID if you are interested in contributing
to this spec - CLI, APIs and the service plugin)

Work Items
----------

The work is split into multiple parts:

1. Implementation of the service plugin

   * This will require supporting the REST calls described above.
   * Implementation of the proposed DB model.
   * Definition of RPCs for the underlying implementation.

2. Implementation of new CLIs in a client

3. Packaging of the implemented software and its deployment


Dependencies
============
None

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
The following tempest API tests will be added:
1. CRUD operation of an L2 gateway
2. CRD connection of an L2 gateway with a neutron network

Documentation Impact
====================

User Documentation
------------------
Functionality and configuration details will be documented

Developer Documentation
-----------------------
OpenStack wiki needs to be updated

References
==========

[1] NSX plugin https://github.com/openstack/neutron/blob/master/neutron/plugins/vmware/plugins/base.py#L88
[2] Connecting neutron networks with external networks at the layer-2 level https://review.openstack.org/#/c/100278
[3] Support for extensions in ML2 using Extension Mechanism Manager https://review.openstack.org/#/c/89211
[4] Support for external attachment type validators https://review.openstack.org/#/c/87825
[5] Service API for L2 bridging tenants/provider networks https://review.openstack.org/#/c/93613
[6] Paris summit Neutron lightning talks https://etherpad.openstack.org/p/neutron-kilo-lightning-talks
https://drive.google.com/file/d/0B6wARyYJHf0ZRDJvdkJYVjVLVzQ/view
