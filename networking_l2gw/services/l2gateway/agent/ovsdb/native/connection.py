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

from ovs.db import idl

from ovsdbapp.backend.ovs_idl import connection as conn


def get_schema_helper_for_vtep():
    current_dir = os.path.dirname(os.path.realpath(__file__))
    return idl.SchemaHelper(current_dir + '/../vtep/vtep.ovsschema')


class Connection(conn.Connection):
    def __init__(self, connection, timeout, schema_name):
        idl_ = idl.Idl(connection, get_schema_helper_for_vtep())
        super(Connection, self).__init__(idl_, timeout)
