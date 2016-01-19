# Copyright (c) 2015 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import threading
from uuid import UUID

from ovs.db import idl
from ovs.jsonrpc import Session
from ovs import poller

from neutron.agent.ovsdb import impl_idl
from neutron.agent.ovsdb.native import connection
from neutron.agent.ovsdb.native import idlutils


from networking_l2gw.services.l2gateway.agent.ovsdb import commands as cmd
from networking_l2gw.services.l2gateway.agent.ovsdb import ovsdb_model as model


class Connection(connection.Connection):
    def __init__(self, connection, timeout, schema_name):
        super(Connection, self).__init__(connection, timeout, schema_name)

    def accept(self):
        session = Session.open(self.connection)
        # first call to session.run creates the PassiveStream object and second
        # one accept incoming connection
        session.run()
        session.run()

        helper = idlutils.get_schema_helper_from_stream(session.stream,
                                                        'hardware_vtep')
        helper.register_all()
        self.idl = idl.Idl(self.connection, helper, session)
        idlutils.wait_for_change(self.idl, self.timeout)
        self.poller = poller.Poller()
        self.thread = threading.Thread(target=self.run)
        self.thread.setDaemon(True)
        self.thread.start()


class OvsdbHardwareVtepIdl():
    def __init__(self, context, ovsdb_conn, timeout):
        self.context = context
        self.timeout = timeout
        self.ovsdb_connection = Connection(ovsdb_conn, timeout,
                                           'hardware_vtep')
        if self.is_passive(ovsdb_conn):
            self.ovsdb_connection.accept()
        else:
            self.ovsdb_connection.start()

        self.idl = self.ovsdb_connection.idl

    @property
    def _ovs(self):
        return self._tables['Global'].rows.values()[0]

    @property
    def _tables(self):
        return self.idl.tables

    def is_passive(self, ovsdb_conn):

        return ovsdb_conn.startswith("punix:") or ovsdb_conn.startswith(
            "ptcp:")

    def transaction(self, check_error=False, log_errors=True, **kwargs):
        return impl_idl.Transaction(self, self.ovsdb_connection,
                                    self.timeout,
                                    check_error, log_errors)

    def list_sw(self):
        return cmd.ListPhysicalSwitchCommand(self)

    def get_logical_switch_by_name(self, name):
        switch = idlutils.row_by_value(self.idl, 'Logical_Switch',
                                       'name',
                                       name, None)
        if switch:
            return model.LogicalSwitch(switch.uuid.hex, switch.name,
                                       switch.description, switch.tunnel_key)
        return None

    def get_logical_switch_by_uuid(self, uuid):
        row = self._tables['Logical_Switch'].rows.get(UUID(uuid))
        if not row:
            return
        return model.LogicalSwitch(row.uuid, row.name, row.description,
                                   row.tunnel_key)

    def add_logical_switch(self, name, description, tunnel_key,
                           may_exist=True):
        return cmd.AddLogicalSwitch(self, name, description, tunnel_key,
                                    may_exist)

    def del_logical_switch_by_name(self, name):
        return cmd.DelLogicalSwitchByNameCommand(self, name)

    def get_physical_locator_list(self):
        return cmd.GetPhysicalLocatorList(self)

    def get_ucast_macs_remote(self, logical_sw_uuid, mac):

        sw = self._tables['Logical_Switch'].rows.get(UUID(logical_sw_uuid))
        if not sw:
            raise Exception('Logical Switch not found')

        row = [x for x in
               self._tables['Ucast_Macs_Remote'].rows.values()
               if x.MAC == mac and x.logical_switch == sw]

        if row:
            return model.UcastMacs(row[0].uuid.hex, row[0].MAC, row[0].ipaddr,
                                   row[0].logical_switch.uuid.hex,
                                   row[0].locator.uuid.hex)

    def add_ucast_mac_remote(self, logical_sw_uuid, locator, mac, ipaddr):
        return cmd.AddUcastMacsRemote(self, logical_sw_uuid, locator, mac,
                                      ipaddr)

    def del_ucast_macs_remote(self, logical_switch_uuid, mac):
        return cmd.DelUcastMacsRemoteByLogicalSwAndMac(
            self,
            logical_switch_uuid,
            mac
        )

    def del_ucast_mac_remote_by_uuid(self, uuid):
        return cmd.DelUcastMacsRemote(self, uuid)

    def add_mcast_macs_remote(self, mac, logical_sw_uuid, locator_list):
        return cmd.AddMcastMacsRemote(self, mac, logical_sw_uuid, locator_list)

    def del_remote_connection(self, ipaddr, tunnel_key):
        return cmd.DelRemoteConnection(self, ipaddr, tunnel_key)

    def del_mcast_macs_remote_by_id(self, mac_uuid):
        return cmd.DelUcastMacsRemote(self, mac_uuid)
