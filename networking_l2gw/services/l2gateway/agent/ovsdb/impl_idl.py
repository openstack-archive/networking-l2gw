# Copyright (c) 2016 OpenStack Foundation.
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
from ovsdbapp.backend.ovs_idl.transaction import Transaction

from networking_l2gw.services.l2gateway.agent.ovsdb import api
from networking_l2gw.services.l2gateway.agent.ovsdb.native import (
    commands as cmd)
from networking_l2gw.services.l2gateway.agent.ovsdb.native import connection


class OvsdbHardwareVtepIdl(api.API):
    def __init__(self, context, ovsdb_conn, timeout):
        self.context = context
        self.timeout = timeout
        self.ovsdb_connection = connection.Connection(ovsdb_conn, timeout,
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
        return Transaction(self, self.ovsdb_connection,
                           self.timeout,
                           check_error, log_errors)

    def db_find(self, table, *conditions, **kwargs):
        pass

    def get_physical_sw_list(self):
        return cmd.ListPhysicalSwitchCommand(self)
