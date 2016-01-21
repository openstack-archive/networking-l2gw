

==============
L2 Gateway API
==============

Until this version, the L2GW was meant to connect overlay Neutron network to
bare metal servers via hardware switches. This was done by connecting the
hardware switch to the local Compute Nodes using VXLAN and connecting the bare
metal servers to the hardware switches physical ports. To bind the proper
overlay network to the bare metal server the L2GW uses the overlay network's
segmentation-id as VXLAN tunnel id and VLANs on the hardware switch.

It is our intention to use this project to also support the connection of the
local overlay networks with remote overlay networks. One possible scenario is to
connect multiple OpenStack clouds in a way that the overlay networks could be
connected and act as local networks that are connected via WAN link
(inter-cloud connection). Currently the L2GW support L2 connection only but this
can also be changed in the future to add L3 connection as well.

To support the inter-cloud connection, the L2GW API is extended to provide a way
to stretch the network between the local and the remote clouds.

Note: the proposed API is an extension of the existing API and can be executed
by admin users only, as the previous one.

================
New API Commands
================

1. Remote Gateway

Remote Gateway is an entity that connects to a local Gateway using tunnel to
enable connection between local and remote networks. Different networks are
connected using different segmentation id. The segmentation id is implementation
specific. Different implementation can use different tunnel protocol with its
own tunnel key to be used as the segmentation id (VxLAN, GRE, Geneve, Etc.).
Single Remote Gateway can connect to multiple local Gateways and the local
networks that are attached to them. Also Local Gateway can connect to multiple
Remote Gateways using multiple Remote Gateway Connections, each connection to
a different Remote Gateway.

1.1. Remote Gateway creation:

usage: l2-remote-gateway-create <REMOTE-GATEWAY-NAME> <IP-ADDRESS>

where <REMOTE-GATEWAY-NAME> is a logical name for the remote gateway
and <IP-ADDRESS> is the IP address of the remote gateway which will be the end
point of the tunnel.


1.2. Remote Gateway update:

usage: l2-remote-gateway-update <L2_REMOTE_GATEWAY>

After creating a Remote Gateway, one can use this command to update the
IP address or/and the gateway's logical name.

1.3. Remote Gateway deletion:

usage: l2-remote-gateway-delete <L2_REMOTE_GATEWAY>

Use this command to delete Remote Gateway using its logical name or UUID.

1.4. Remote Gateway list:

usage: l2-remote-gateway-list

This command lists all the Remote Gateways. A response will look like
the following:

+--------------------------------------+------+----------+
| id                                   | name | ipaddr   |
+--------------------------------------+------+----------+
| 63821629-6cfd-44c8-8c4a-14c4b5fe28ea | rgw1 | 10.0.0.1 |
+--------------------------------------+------+----------+


1.5. Remote Gateway show:

usage: l2-remote-gateway-show <L2_REMOTE_GATEWAY>

Get information of specific Remote Gateway using its logical name or UUID.
Example of response:

+--------+--------------------------------------+
| Field  | Value                                |
+--------+--------------------------------------+
| id     | 63821629-6cfd-44c8-8c4a-14c4b5fe28ea |
| ipaddr | 10.0.0.1                             |
| name   | rgw1                                 |
+--------+--------------------------------------+


2. Remote Gateway Connection

Remote Gateway Connection is a connection between local and remote networks.
Currently the connections are implemented using VXLAN between the local
and remote switches.


2.1 Remote Gateway Connection creation:

Use this command to create a connection between local and remote network.

usage: l2-remote-gateway-connection-create <GATEWAY-NAME/UUID>
                                           <NETWORK-NAME/UUID>
                                           <REMOTE-GATEWAY-NAME/UUID>


<GATEWAY-NAME/UUID> is UUID or logical name of previously created local gateway.

<NETWORK-NAME/UUID> is UUID or logical name of tenant network that was
previously added to local gateway using l2-gateway-connection-create command.

<REMOTE-GATEWAY-NAME/UUID> is UUID or logical name of the Remote Gateway that
the remote network is connected to.

--seg-id is an optional parameter that will be used as tunnel key for the
connection between the local and remote Gateways. This parameter is optional and
in case it will not be used, the tunnel key that will be used is the overlay
network segmentation id.

--flood is an optional string of True/False values that state if the local
switch should flood unknown MACs or broadcast MAC to the remote connection.


2.2 Remote Gateway Connection delete:

usage: l2-remote-gateway-connection-delete <L2_GATEWAY_CONNECTION>

use Remote Gateway UUID to delete connection to remote network.

2.3 Remote Gateway Connection list:


usage: l2-remote-gateway-connection-list

Lists all the connection to Remote Gateways.
example of response:

+------------+-------------------+-----------------+-----------------+
| id         | l2_gateway_id     | network_id      | segmentation_id |
+------------+-------------------+-----------------+-----------------+
| 31c204.... | c8da3e74-fde9-... | d90db94a-2b3... |  9765           |
+------------+-------------------+-----------------+-----------------+


2.4 Remote Gateway Connection show:

Show information of a single connection to a Remote Gateway using the
connection UUID.

example:

l2-remote-gateway-connection-show 31c20418-9cf2-4d47-b17e-d92906e3f248

+-----------------+--------------------------------------+
| Field           | Value                                |
+-----------------+--------------------------------------+
| id              | 31c20418-9cf2-4d47-b17e-d92906e3f248 |
| l2_gateway_id   | c8da3e74-fde9-48e3-81f2-5fee756dd9de |
| network_id      | d90db94a-2b3c-4415-971f-967e2f52248d |
| segmentation_id | 9765                                 |
| tenant_id       | 84429618ed684296bc48eb120acf57bc     |
+-----------------+--------------------------------------+


3. Remote MAC

The following command could be used by orchestration application to provide
information on remote hosts - their MAC address, IP address
(for ARP suppression) and link them to Remote Gateway Connection for the local
switch to know where to switch the packets to.

3.1 Remote MAC creation:

usage: l2-remote-mac-create <MAC-IP> <REMOTE-GATEWAY-CONN-UUID>

<MAC-IP> is a tuple of remote host MAC address and optional IP address.
The format is as followed:

<MAC>[;<IP>]

Where:
<MAC> is the MAC address of the remote host in the form of 00:00:00:00:00:00
<IP> IP address of the remote host (optional).

<REMOTE-GATEWAY-CONN-UUID> the UUID of the Remote Gateway Connection that
will lead to the network where the remote host is located.

REST message format:

{
    "remote-mac" : {
        "mac": "00:11:22:33:44:55',
        "ip": "1.2.3.4"
    }

}


3.2 Bulk Remote MAC creation

To send bulk remote MAC creation to the server, the following REST message
should be used:

{
    "remote-macs": [
        {
            "mac": "00:11:22:33:44:55',
            "ip": "1.2.3.5"
        },
        {
            "mac": "00:11:22:33:44:66',
            "ip": "1.2.3.6"
        }
    ]
}



3.3 Remote MAC delete:

usage: l2-remote-mac-delete <L2_REMOTE_MAC>

L2_REMOTE_MAC is the UUID of the MAC address to be deleted.


3.4 Remote MAC list:

usage: l2-remote-mac-list [--remote-connection UUID]

Lists all the remote MAC addresses.
example of a response:

+--------------+-------------------+--------------------------------------+
| uuid         | mac               | ip_addr       |  rgw_connection      |
+--------------+-------------------+--------------------------------------+
| b59584eb-... | 00:11:22:33:44:55 | 192.168.10.23 |  a60dc097-...        |
+--------------+-------------------+--------------------------------------+

if the optional remote-connection is provided, only MACs that are configured
on this connection will be displayed.

3.4 Remote MAC show:

usage: l2-remote-mac-show <L2_REMOTE_MAC>

show information of a specific MAC address using its UUID.
example of response:

 l2-remote-mac-show b59584eb-432a-4dba-9a09-f929e77da0c7

+----------------+--------------------------------------+
| Field          | Value                                |
+----------------+--------------------------------------+
| ipaddr         | 3.3.3.3                              |
| mac            | 00:11:22:33:44:55                    |
| rgw_connection | a60dc097-13d7-4a9a-9842-117440911eb9 |
| uuid           | b59584eb-432a-4dba-9a09-f929e77da0c7 |
+----------------+--------------------------------------+
