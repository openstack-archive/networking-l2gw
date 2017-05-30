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

import mock
from mock import MagicMock
import ovs.jsonrpc

from neutron.tests import base
from ovsdbapp.backend.ovs_idl import command as cmd
from ovsdbapp.backend.ovs_idl import idlutils

from networking_l2gw.services.l2gateway.agent.ovsdb import impl_idl


class Msg(object):
    id = 0
    type = 1
    method = 'update'
    params = [
        None, {'Global': {
            '381d60b5-6171-484a-842f-49f3e83bb586': {'new': {
                'switches': ['uuid', '03eebc5d-153f-4b03-8efa-45d22eb9942f'],
                'other_config': [
                    'map', []
                ],
                'managers': ['set', []]}
            }},
            'Physical_Switch': {'03eebc5d-153f-4b03-8efa-45d22eb9942f': {
                'new': {'management_ips': ['set', []],
                        'description': '', 'other_config': ['map', []],
                        'tunnel_ips': ['set', []],
                        'switch_fault_status': ['set', []],
                        'ports': ['set', []], 'tunnels': ['set', []],
                        'name': 'ps1'}}}}
    ]


class SimpleIdlTests(base.BaseTestCase):
    def setUp(self):
        super(SimpleIdlTests, self).setUp()

    def test_list_physical_switches(self):
        session_mock = mock.patch.object(
            ovs.jsonrpc.Session,
            'open',
            return_value=ovs.jsonrpc.Session(None, None)
        )
        wait_mock = mock.patch.object(idlutils, 'wait_for_change')

        execute_mock = mock.patch.object(
            cmd.BaseCommand,
            'execute',
            return_value=['ps1'])
        with session_mock, execute_mock, wait_mock:
            ovs.jsonrpc.Session.run = MagicMock(
                return_value=MagicMock(return_value='myrun'))
            ovs.jsonrpc.Session.get_seqno = MagicMock(return_value=None)
            ovs.jsonrpc.Session.wait = MagicMock(return_value=None)
            ovs.jsonrpc.Session.is_connected = MagicMock(return_value=True)
            ovs.jsonrpc.Session.recv = MagicMock(
                side_effect=[Msg, None, None, None, None])

            self.db = impl_idl.OvsdbHardwareVtepIdl(self,
                                                    'tcp:fake_ip:fake_port',
                                                    3)

            sw_list = self.db.get_physical_sw_list().execute()

            assert (sw_list is not None) & (sw_list[0] == 'ps1')
            print('physical switch: %s' % sw_list)
