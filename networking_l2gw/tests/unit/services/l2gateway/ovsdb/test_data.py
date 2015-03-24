# Copyright (c) 2015 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

import contextlib
from neutron import context
from neutron import manager
from neutron.tests import base

from networking_l2gw.db.l2gateway.ovsdb import lib
from networking_l2gw.services.l2gateway.common import constants as n_const
from networking_l2gw.services.l2gateway.ovsdb import data


class TestL2GatewayOVSDBCallbacks():

    def setUp(self):
        super(TestL2GatewayOVSDBCallbacks, self).setUp()
        self.context = context.get_admin_context()

    def test_update_ovsdb_changes(self):
        fake_ovsdb_data = {n_const.OVSDB_IDENTIFIER: 'fake_id'}
        with mock.patch.object(data, 'OVSDBData') as ovs_data:
            self.l2gw_callbacks.update_ovsdb_changes(self.context,
                                                     fake_ovsdb_data)
            ovsdb_return_value = ovs_data.return_value
            ovsdb_return_value.update_ovsdb_changes.assert_called_with(
                self.context, fake_ovsdb_data)


class TestOVSDBData(base.BaseTestCase):

    def setUp(self):
        super(TestOVSDBData, self).setUp()
        self.context = context.get_admin_context()
        self.ovsdb_identifier = 'fake_ovsdb_id'
        self.ovsdb_data = data.OVSDBData(self.ovsdb_identifier)

    def test_init(self):
        with mock.patch.object(data.OVSDBData,
                               '_setup_entry_table') as setup_entry_table:
            self.ovsdb_data.__init__(self.ovsdb_identifier)
            self.assertEqual(self.ovsdb_data.ovsdb_identifier,
                             'fake_ovsdb_id')
            self.assertTrue(setup_entry_table.called)

    def test_update_ovsdb_changes(self):
        fake_dict = {}
        fake_new_logical_switches = [fake_dict]
        fake_new_physical_port = [fake_dict]
        fake_new_physical_switches = [fake_dict]
        fake_new_physical_locators = [fake_dict]
        fake_new_local_macs = [fake_dict]
        fake_new_remote_macs = [fake_dict]
        fake_modified_physical_ports = [fake_dict]
        fake_modified_local_macs = [fake_dict]
        fake_deleted_logical_switches = [fake_dict]
        fake_deleted_physical_ports = [fake_dict]
        fake_deleted_physical_switches = [fake_dict]
        fake_deleted_physical_locators = [fake_dict]
        fake_deleted_local_macs = [fake_dict]
        fake_deleted_remote_macs = [fake_dict]

        fake_ovsdb_data = {
            n_const.OVSDB_IDENTIFIER: 'fake_ovsdb_id',
            'new_logical_switches': fake_new_logical_switches,
            'new_physical_ports': fake_new_physical_port,
            'new_physical_switches': fake_new_physical_switches,
            'new_physical_locators': fake_new_physical_locators,
            'new_local_macs': fake_new_local_macs,
            'new_remote_macs': fake_new_remote_macs,
            'modified_physical_ports': fake_modified_physical_ports,
            'modified_local_macs': fake_modified_local_macs,
            'deleted_logical_switches': fake_deleted_logical_switches,
            'deleted_physical_switches': fake_deleted_physical_switches,
            'deleted_physical_ports': fake_deleted_physical_ports,
            'deleted_physical_locators': fake_deleted_physical_locators,
            'deleted_local_macs': fake_deleted_local_macs,
            'deleted_remote_macs': fake_deleted_remote_macs}
        with contextlib.nested(
            mock.patch.object(self.ovsdb_data,
                              '_process_new_logical_switches'),
            mock.patch.object(self.ovsdb_data,
                              '_process_new_physical_ports'),
            mock.patch.object(self.ovsdb_data,
                              '_process_new_physical_switches'),
            mock.patch.object(self.ovsdb_data,
                              '_process_new_physical_locators'),
            mock.patch.object(self.ovsdb_data,
                              '_process_new_local_macs'),
            mock.patch.object(self.ovsdb_data,
                              '_process_new_remote_macs'),
            mock.patch.object(self.ovsdb_data,
                              '_process_modified_physical_ports'),
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_logical_switches'),
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_physical_switches'),
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_physical_ports'),
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_physical_locators'),
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_local_macs'),
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_remote_macs')
            ) as (process_new_logical_switches,
                  process_new_physical_ports,
                  process_new_physical_switches,
                  process_new_physical_locators,
                  process_new_local_macs,
                  process_new_remote_macs,
                  process_modified_physical_ports,
                  process_deleted_logical_switches,
                  process_deleted_physical_switches,
                  process_deleted_physical_ports,
                  process_deleted_physical_locators,
                  process_deleted_local_macs,
                  process_deleted_remote_macs):
            self.ovsdb_data.entry_table = {
                'new_logical_switches': process_new_logical_switches,
                'new_physical_ports': process_new_physical_ports,
                'new_physical_switches': process_new_physical_switches,
                'new_physical_locators': process_new_physical_locators,
                'new_local_macs': process_new_local_macs,
                'new_remote_macs': process_new_remote_macs,
                'modified_physical_ports': process_modified_physical_ports,
                'deleted_logical_switches': process_deleted_logical_switches,
                'deleted_physical_switches': process_deleted_physical_switches,
                'deleted_physical_ports': process_deleted_physical_ports,
                'deleted_physical_locators': process_deleted_physical_locators,
                'deleted_local_macs': process_deleted_local_macs,
                'deleted_remote_macs': process_deleted_remote_macs}
            self.ovsdb_data.update_ovsdb_changes(
                self.context, fake_ovsdb_data)

            process_new_logical_switches.assert_called_with(
                self.context, fake_new_logical_switches)
            process_new_physical_ports.assert_called_with(
                self.context, fake_new_physical_port)
            process_new_physical_switches.assert_called_with(
                self.context, fake_new_physical_switches)
            process_new_physical_locators.assert_called_with(
                self.context, fake_new_physical_locators)
            process_new_local_macs.assert_called_with(
                self.context, fake_new_local_macs)
            process_new_remote_macs.assert_called_with(
                self.context, fake_new_remote_macs)
            process_modified_physical_ports.assert_called_with(
                self.context, fake_modified_physical_ports)
            process_deleted_logical_switches.assert_called_with(
                self.context, fake_deleted_logical_switches)
            process_deleted_physical_switches.assert_called_with(
                self.context, fake_deleted_physical_switches)
            process_deleted_physical_ports.assert_called_with(
                self.context, fake_deleted_physical_ports)
            process_deleted_physical_locators.assert_called_with(
                self.context, fake_deleted_physical_locators)
            process_deleted_local_macs.assert_called_with(
                self.context, fake_deleted_local_macs)
            process_deleted_remote_macs.assert_called_with(
                self.context, fake_deleted_remote_macs)

    def test_process_new_logical_switches(self):
        fake_dict = {}
        fake_new_logical_switches = [fake_dict]
        with mock.patch.object(lib, 'get_logical_switch',
                               return_value=None) as get_ls:
            with mock.patch.object(lib,
                                   'add_logical_switch') as add_ls:
                self.ovsdb_data._process_new_logical_switches(
                    self.context, fake_new_logical_switches)
                self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
                self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                                 'fake_ovsdb_id')
                get_ls.assert_called_with(self.context, fake_dict)
                add_ls.assert_called_with(self.context, fake_dict)

    def test_process_new_physical_switches(self):
        fake_dict = {'tunnel_ip': ['set']}
        fake_new_physical_switches = [fake_dict]
        with mock.patch.object(lib, 'get_physical_switch',
                               return_value=None) as get_ps:
            with mock.patch.object(lib,
                                   'add_physical_switch') as add_ps:
                self.ovsdb_data._process_new_physical_switches(
                    self.context, fake_new_physical_switches)
                self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
                self.assertIsNone(fake_dict['tunnel_ip'])
                self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                                 'fake_ovsdb_id')
                get_ps.assert_called_with(self.context, fake_dict)
                add_ps.assert_called_with(self.context, fake_dict)

    def test_process_new_physical_ports(self):
        fake_dict1 = {}
        fake_dict2 = {'vlan_bindings': [fake_dict1]}
        fake_new_physical_ports = [fake_dict2]
        with contextlib.nested(
            mock.patch.object(lib, 'get_physical_port',
                              return_value=None),
            mock.patch.object(lib,
                              'add_physical_port'),
            mock.patch.object(lib,
                              'get_vlan_binding', return_value=None),
            mock.patch.object(lib,
                              'add_vlan_binding')) as (
                get_pp, add_pp, get_vlan, add_vlan):
            self.ovsdb_data._process_new_physical_ports(
                self.context, fake_new_physical_ports)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict2)
            self.assertEqual(fake_dict2[n_const.OVSDB_IDENTIFIER],
                             'fake_ovsdb_id')
            get_pp.assert_called_with(self.context, fake_dict2)
            add_pp.assert_called_with(self.context, fake_dict2)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict1)
            self.assertIn('port_uuid', fake_dict1)
            get_vlan.assert_called_with(self.context, fake_dict1)
            add_vlan.assert_called_with(self.context, fake_dict1)

    def test_process_new_physical_locators(self):
        fake_dict = {}
        fake_new_physical_locators = [fake_dict]
        with mock.patch.object(lib, 'get_physical_locator',
                               return_value=None) as get_pl:
            with mock.patch.object(lib,
                                   'add_physical_locator') as add_pl:
                self.ovsdb_data._process_new_physical_locators(
                    self.context, fake_new_physical_locators)
                self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
                self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                                 'fake_ovsdb_id')
                get_pl.assert_called_with(self.context, fake_dict)
                add_pl.assert_called_with(self.context, fake_dict)

    def test_process_new_local_macs(self):
        fake_dict = {'uuid': '123456',
                     'mac': 'mac123',
                     'ovsdb_identifier': 'host1',
                     'logical_switch_id': 'ls123'}
        fake_new_local_macs = [fake_dict]
        with contextlib.nested(
            mock.patch.object(lib, 'get_ucast_mac_local', return_value=None),
            mock.patch.object(lib, 'add_ucast_mac_local')) as (
                get_lm, add_lm):
            self.ovsdb_data._process_new_local_macs(
                self.context, fake_new_local_macs)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                             'fake_ovsdb_id')
            get_lm.assert_called_with(self.context, fake_dict)
            add_lm.assert_called_with(self.context, fake_dict)

    def test_process_new_remote_macs(self):
        fake_dict = {'logical_switch_id': 'ls123'}
        fake_new_remote_macs = [fake_dict]
        with mock.patch.object(lib, 'get_ucast_mac_remote',
                               return_value=None) as get_mr:
            with mock.patch.object(lib,
                                   'add_ucast_mac_remote') as add_mr:
                self.ovsdb_data._process_new_remote_macs(
                    self.context, fake_new_remote_macs)
                self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
                self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                                 'fake_ovsdb_id')
                get_mr.assert_called_with(self.context, fake_dict)
                add_mr.assert_called_with(self.context, fake_dict)

    def test_process_deleted_logical_switches(self):
        fake_dict = {}
        fake_deleted_logical_switches = [fake_dict]
        with mock.patch.object(lib, 'delete_logical_switch') as delete_ls:
            self.ovsdb_data._process_deleted_logical_switches(
                self.context, fake_deleted_logical_switches)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                             'fake_ovsdb_id')
            delete_ls.assert_called_with(self.context, fake_dict)

    def test_process_deleted_physical_switches(self):
        fake_dict = {}
        fake_deleted_physical_switches = [fake_dict]
        with mock.patch.object(lib, 'delete_physical_switch') as delete_ps:
            self.ovsdb_data._process_deleted_physical_switches(
                self.context, fake_deleted_physical_switches)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                             'fake_ovsdb_id')
            delete_ps.assert_called_with(self.context, fake_dict)

    def test_process_deleted_physical_ports(self):
        fake_dict = {}
        fake_deleted_physical_ports = [fake_dict]
        with mock.patch.object(lib, 'delete_physical_port') as delete_pp:
            self.ovsdb_data._process_deleted_physical_ports(
                self.context, fake_deleted_physical_ports)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                             'fake_ovsdb_id')
            delete_pp.assert_called_with(self.context, fake_dict)

    def test_process_deleted_physical_locators(self):
        fake_dict = {}
        fake_deleted_physical_locators = [fake_dict]
        mock.patch.object(manager, 'NeutronManager').start()
        with mock.patch.object(lib, 'delete_physical_locator') as delete_pl:
            self.ovsdb_data._process_deleted_physical_locators(
                self.context, fake_deleted_physical_locators)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                             'fake_ovsdb_id')
            delete_pl.assert_called_with(self.context, fake_dict)

    def test_process_deleted_local_macs(self):
        fake_dict = {'uuid': '123456',
                     'mac': 'mac123',
                     'ovsdb_identifier': 'host1',
                     'logical_switch_id': 'ls123'}
        fake_deleted_local_macs = [fake_dict]
        with mock.patch.object(lib, 'delete_ucast_mac_local') as delete_ml:
            with mock.patch.object(lib,
                                   'get_ucast_mac_remote_by_mac_and_ls',
                                   return_value=True):
                self.ovsdb_data._process_deleted_local_macs(
                    self.context, fake_deleted_local_macs)
                self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
                self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                                 'fake_ovsdb_id')
                delete_ml.assert_called_with(self.context, fake_dict)

    def test_process_deleted_remote_macs(self):
        fake_dict = {}
        fake_deleted_remote_macs = [fake_dict]
        with mock.patch.object(lib, 'delete_ucast_mac_remote') as delete_mr:
            self.ovsdb_data._process_deleted_remote_macs(
                self.context, fake_deleted_remote_macs)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual(fake_dict[n_const.OVSDB_IDENTIFIER],
                             'fake_ovsdb_id')
            delete_mr.assert_called_with(self.context, fake_dict)

    def test_process_modified_physical_ports(self):
        fake_dict1 = {}
        fake_dict2 = {'vlan_bindings': [fake_dict1],
                      'uuid': 'fake_uuid'}
        fake_modified_physical_ports = [fake_dict2]
        with contextlib.nested(
            mock.patch.object(lib, 'get_physical_port'),
            mock.patch.object(lib,
                              'add_physical_port'),
            mock.patch.object(lib,
                              'get_all_vlan_bindings_by_physical_port'),
            mock.patch.object(lib,
                              'add_vlan_binding')) as (
                get_pp, add_pp, get_vlan, add_vlan):
            self.ovsdb_data._process_modified_physical_ports(
                self.context, fake_modified_physical_ports)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict2)
            self.assertEqual(fake_dict2[n_const.OVSDB_IDENTIFIER],
                             'fake_ovsdb_id')
            get_pp.assert_called_with(self.context, fake_dict2)
            self.assertFalse(add_pp.called)
            get_vlan.assert_called_with(self.context, fake_dict2)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict1)
            self.assertIn('port_uuid', fake_dict1)
            add_vlan.assert_called_with(self.context, fake_dict1)
