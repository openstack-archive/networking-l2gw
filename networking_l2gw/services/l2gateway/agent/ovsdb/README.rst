Other approaches for the L2 gateway agent to communicate with the OVSDB server
------------------------------------------------------------------------------
For an L2 gateway agent to communicate with an OVSDB server, IDL class provided by the OpenvSwitch library was explored.

The source code for the IDL class can be found at:
1. https://github.com/osrg/openvswitch/tree/master/python/ovs/db/idl.py
2. Alternatively, the source code can be downloaded from http://openvswitch.org/download/ as a tar ball.

Here are the findings.

1. IDL class maintains a socket connection with a given OVSDB server and maintains a local cache of the OVSDB tables.
2. Whenever there is a change in the OVSDB tables, the cache is updated automatically.
3. The caller has to pass the required data structures to perform a transaction on OVSDB tables.

Advantages:
1. Logic of maintaining connection with the OVSDB servers is easy.
2. No need to write extra logic of performing the transaction on the OVSDB tables.
   Only rows to be inserted/modified/deleted are to be supplied.

Disadvantages:
1. To perform a transaction on a table, the caller has to register that table with IDL so that the local cache is maintained. Without registering, a transaction cannot be performed.
2. Due to this, every transact L2 gateway agent will have to maintain unnecessary local cache of OVSDB tables (which gets updated automatically whenever there is a change in the OVSDB table state).
3. With the current approach, when the Monitor agent receives notifications for OVSDB changes, the agent instantly sends RPC to the plugin notifying the changes. The IDL class internally receives event notifications for any updates to the OVSDB tables and are processed internally. We may not be able to invoke RPCs to the plugin if IDL class is used.
4. It violates our basic concept of transact and monitor agent.
5. After browsing the code, could not find any option in this python binding to provide SSL keys/certs so as to open an SSL connection/stream to the OVSDB server.
https://github.com/osrg/openvswitch/blob/master/python/ovs/socket_util.py
https://github.com/osrg/openvswitch/blob/master/python/ovs/stream.py
6. We may have to package the openvswitch 2.3.1 library with the agent

Advantages of the current code of the L2 gateway agent over the IDL library:
1. It is light weight – does not maintain local cache of OVSDB tables.
2. Complies with the proposed spec/architecture.
3. As it implements the RFC 7047 described at http://tools.ietf.org/html/rfc7047, code maintenance is simple.
4. Changing the code to use IDL at the last moment is a bit of risk (this involves development from scratch, change in the agent architecture and testing).

We can always enhance the agent code to use IDL class in future.
