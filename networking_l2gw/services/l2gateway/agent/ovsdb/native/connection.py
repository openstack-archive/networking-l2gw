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

import os
import threading

from ovs.db import idl
from ovs import poller

from neutron.agent.ovsdb.native import connection as conn
from neutron.agent.ovsdb.native import idlutils


def get_schema_helper_for_vtep():
    current_dir = os.path.dirname(os.path.realpath(__file__))
    return idl.SchemaHelper(current_dir + '/../vtep/vtep.ovsschema')


class Connection(conn.Connection):
    def __init__(self, connection, timeout, schema_name):
        super(Connection, self).__init__(connection, timeout, schema_name)

    def start(self, table_name_list=None):
        with self.lock:
            if self.idl is not None:
                return

            helper = get_schema_helper_for_vtep()

            if table_name_list is None:
                helper.register_all()
            else:
                for table_name in table_name_list:
                    helper.register_table(table_name)
            self.idl = idl.Idl(self.connection, helper)
            idlutils.wait_for_change(self.idl, self.timeout)
            self.poller = poller.Poller()
            self.thread = threading.Thread(target=self.run)
            self.thread.setDaemon(True)
            self.thread.start()
