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

from neutron import manager
from neutron.plugins.ml2 import managers
from neutron.tests import base

from neutron_lib import context
from neutron_lib.plugins import directory

from networking_l2gw.db.l2gateway import l2gateway_db
from networking_l2gw.db.l2gateway.ovsdb import lib
from networking_l2gw.services.l2gateway.common import constants as n_const
from networking_l2gw.services.l2gateway.common import ovsdb_schema
from networking_l2gw.services.l2gateway.common import tunnel_calls
from networking_l2gw.services.l2gateway.ovsdb import data
from networking_l2gw.services.l2gateway.service_drivers import agent_api


class TestL2GatewayOVSDBCallbacks(object):

    def setUp(self):
        super(TestL2GatewayOVSDBCallbacks, self).setUp()
        self.context = context.get_admin_context()

    def test_update_ovsdb_changes(self):
        fake_activity = 1
        fake_ovsdb_data = {n_const.OVSDB_IDENTIFIER: 'fake_id'}
        with mock.patch.object(data, 'OVSDBData') as ovs_data:
            self.l2gw_callbacks.update_ovsdb_changes(self.context,
                                                     fake_activity,
                                                     fake_ovsdb_data)
            ovsdb_return_value = ovs_data.return_value
            ovsdb_return_value.update_ovsdb_changes.assert_called_with(
                self.context, fake_activity, fake_ovsdb_data)

    def test_notify_ovsdb_states(self):
        fake_ovsdb_states = {'ovsdb1': 'connected'}
        with mock.patch.object(data, 'OVSDBData') as ovs_data:
            self.l2gw_callbacks.notify_ovsdb_states(self.context,
                                                    fake_ovsdb_states)
            ovsdb_return_value = ovs_data.return_value
            ovsdb_return_value.notify_ovsdb_states.assert_called_with(
                self.context, fake_ovsdb_states)

    def test_get_ovsdbdata_object(self):
        fake_ovsdb_id = 'fake_ovsdb_id'
        with mock.patch.object(data, 'OVSDBData') as ovs_data:
            ret_value = self.l2gw_callbacks.get_ovsdbdata_object(
                fake_ovsdb_id)
            ret_value1 = ovs_data.assert_called_with(fake_ovsdb_id)
            self.assertEqual(ret_value, ret_value1)


class TestOVSDBData(base.BaseTestCase):

    def setUp(self):
        super(TestOVSDBData, self).setUp()
        self.context = context.get_admin_context()
        self.ovsdb_identifier = 'fake_ovsdb_id'
        mock.patch.object(directory, 'get_plugin').start()
        mock.patch.object(managers, 'TypeManager').start()
        self.ovsdb_data = data.OVSDBData(self.ovsdb_identifier)

    def test_init(self):
        with mock.patch.object(data.OVSDBData,
                               '_setup_entry_table') as setup_entry_table:
            self.ovsdb_data.__init__(self.ovsdb_identifier)
            self.assertEqual('fake_ovsdb_id',
                             self.ovsdb_data.ovsdb_identifier)
            self.assertTrue(setup_entry_table.called)

    def test_update_ovsdb_changes(self):
        fake_dict = {}
        fake_activity = 1
        fake_remote_mac = {'uuid': '123456',
                           'mac': 'mac123',
                           'ovsdb_identifier': 'host1',
                           'logical_switch_id': 'ls123'}
        fake_new_logical_switches = [fake_dict]
        fake_new_physical_port = [fake_dict]
        fake_new_physical_switches = [fake_dict]
        fake_new_physical_locators = [fake_dict]
        fake_new_local_macs = [fake_dict]
        fake_new_remote_macs = [fake_remote_mac]
        fake_modified_remote_macs = [fake_dict]
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
            'modified_remote_macs': fake_modified_remote_macs,
            'modified_physical_ports': fake_modified_physical_ports,
            'modified_local_macs': fake_modified_local_macs,
            'deleted_logical_switches': fake_deleted_logical_switches,
            'deleted_physical_switches': fake_deleted_physical_switches,
            'deleted_physical_ports': fake_deleted_physical_ports,
            'deleted_physical_locators': fake_deleted_physical_locators,
            'deleted_local_macs': fake_deleted_local_macs,
            'deleted_remote_macs': fake_deleted_remote_macs}
        with mock.patch.object(self.ovsdb_data,
                               '_process_new_logical_switches') as process_new_logical_switches, \
            mock.patch.object(self.ovsdb_data,
                              '_process_new_physical_ports') as process_new_physical_ports, \
            mock.patch.object(self.ovsdb_data,
                              '_process_new_physical_switches') as process_new_physical_switches, \
            mock.patch.object(self.ovsdb_data,
                              '_process_new_physical_locators') as process_new_physical_locators, \
            mock.patch.object(self.ovsdb_data,
                              '_process_new_local_macs') as process_new_local_macs, \
            mock.patch.object(self.ovsdb_data,
                              '_process_new_remote_macs') as process_new_remote_macs, \
            mock.patch.object(self.ovsdb_data,
                              '_process_modified_remote_macs') as process_modified_remote_macs, \
            mock.patch.object(self.ovsdb_data,
                              '_process_modified_physical_ports') as process_modified_physical_ports, \
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_logical_switches') as process_deleted_logical_switches, \
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_physical_switches') as process_deleted_physical_switches, \
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_physical_ports') as process_deleted_physical_ports, \
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_physical_locators') as process_deleted_physical_locators, \
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_local_macs') as process_deleted_local_macs, \
            mock.patch.object(self.ovsdb_data,
                              '_process_deleted_remote_macs') as process_deleted_remote_macs, \
            mock.patch.object(self.ovsdb_data,
                              '_handle_l2pop') as mock_handle_l2pop:
            self.ovsdb_data.entry_table = {
                'new_logical_switches': process_new_logical_switches,
                'new_physical_ports': process_new_physical_ports,
                'new_physical_switches': process_new_physical_switches,
                'new_physical_locators': process_new_physical_locators,
                'new_local_macs': process_new_local_macs,
                'new_remote_macs': process_new_remote_macs,
                'modified_remote_macs': process_modified_remote_macs,
                'modified_physical_ports': process_modified_physical_ports,
                'deleted_logical_switches': process_deleted_logical_switches,
                'deleted_physical_switches': process_deleted_physical_switches,
                'deleted_physical_ports': process_deleted_physical_ports,
                'deleted_physical_locators': process_deleted_physical_locators,
                'deleted_local_macs': process_deleted_local_macs,
                'deleted_remote_macs': process_deleted_remote_macs}
            self.ovsdb_data.update_ovsdb_changes(
                self.context, fake_activity, fake_ovsdb_data)

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
            process_modified_remote_macs.assert_called_with(
                self.context, fake_modified_remote_macs)
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
            self.assertTrue(mock_handle_l2pop.called)

    @mock.patch.object(lib, 'get_all_pending_remote_macs_in_asc_order')
    @mock.patch.object(lib, 'delete_pending_ucast_mac_remote')
    @mock.patch.object(ovsdb_schema, 'LogicalSwitch')
    @mock.patch.object(ovsdb_schema, 'PhysicalLocator')
    @mock.patch.object(ovsdb_schema, 'UcastMacsRemote')
    @mock.patch.object(agent_api.L2gatewayAgentApi, 'add_vif_to_gateway')
    @mock.patch.object(agent_api.L2gatewayAgentApi, 'update_vif_to_gateway')
    @mock.patch.object(agent_api.L2gatewayAgentApi, 'delete_vif_from_gateway')
    def test_notify_ovsdb_states(self, mock_del_vif, mock_upd_vif,
                                 mock_add_vif, mock_ucmr, mock_pl,
                                 mock_ls, mock_del_pend_recs,
                                 mock_get_pend_recs):
        fake_ovsdb_states = {'ovsdb1': 'connected'}
        fake_dict = {'logical_switch_uuid': 'fake_ls_id',
                     'mac': 'fake_mac',
                     'locator_uuid': 'fake_loc_id',
                     'dst_ip': 'fake_dst_ip',
                     'vm_ip': 'fake_vm_ip'}
        fake_insert_dict = {'operation': 'insert'}
        fake_insert_dict.update(fake_dict)
        fake_update_dict = {'operation': 'update'}
        fake_update_dict.update(fake_dict)
        fake_delete_dict = {'operation': 'delete'}
        fake_delete_dict.update(fake_dict)
        mock_get_pend_recs.return_value = [fake_insert_dict]
        self.ovsdb_data.notify_ovsdb_states(
            self.context, fake_ovsdb_states)
        self.assertTrue(mock_add_vif.called)
        mock_get_pend_recs.return_value = [fake_update_dict]
        self.ovsdb_data.notify_ovsdb_states(
            self.context, fake_ovsdb_states)
        self.assertTrue(mock_upd_vif.called)
        mock_get_pend_recs.return_value = [fake_delete_dict]
        self.ovsdb_data.notify_ovsdb_states(
            self.context, fake_ovsdb_states)
        self.assertTrue(mock_del_vif.called)

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
                self.assertEqual('fake_ovsdb_id',
                                 fake_dict[n_const.OVSDB_IDENTIFIER])
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
                self.assertEqual('fake_ovsdb_id',
                                 fake_dict[n_const.OVSDB_IDENTIFIER])
                get_ps.assert_called_with(self.context, fake_dict)
                add_ps.assert_called_with(self.context, fake_dict)

    @mock.patch.object(lib, 'get_physical_port', return_value=None)
    @mock.patch.object(lib, 'add_physical_port')
    @mock.patch.object(lib, 'get_vlan_binding', return_value=None)
    @mock.patch.object(lib, 'add_vlan_binding')
    def test_process_new_physical_ports(self, add_vlan, get_vlan,
                                        add_pp, get_pp):
        fake_dict1 = {}
        fake_dict2 = {'vlan_bindings': [fake_dict1]}
        fake_new_physical_ports = [fake_dict2]
        self.ovsdb_data._process_new_physical_ports(
            self.context, fake_new_physical_ports)
        self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict2)
        self.assertEqual('fake_ovsdb_id',
                         fake_dict2[n_const.OVSDB_IDENTIFIER])
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
                self.assertEqual('fake_ovsdb_id',
                                 fake_dict[n_const.OVSDB_IDENTIFIER])
                get_pl.assert_called_with(self.context, fake_dict)
                add_pl.assert_called_with(self.context, fake_dict)

    @mock.patch.object(lib, 'get_ucast_mac_local', return_value=None)
    @mock.patch.object(lib, 'add_ucast_mac_local')
    def test_process_new_local_macs(self, add_lm, get_lm):
        fake_dict = {'uuid': '123456',
                     'mac': 'mac123',
                     'ovsdb_identifier': 'host1',
                     'logical_switch_id': 'ls123'}
        fake_new_local_macs = [fake_dict]
        self.ovsdb_data._process_new_local_macs(
            self.context, fake_new_local_macs)
        self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
        self.assertEqual('fake_ovsdb_id',
                         fake_dict[n_const.OVSDB_IDENTIFIER])
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
                self.assertEqual('fake_ovsdb_id',
                                 fake_dict[n_const.OVSDB_IDENTIFIER])
                get_mr.assert_called_with(self.context, fake_dict)
                add_mr.assert_called_with(self.context, fake_dict)

    def test_process_modified_remote_macs(self):
        fake_dict = {'logical_switch_id': 'ls123'}
        fake_modified_remote_macs = [fake_dict]
        with mock.patch.object(lib,
                               'update_ucast_mac_remote') as update_mr:
            self.ovsdb_data._process_modified_remote_macs(
                self.context, fake_modified_remote_macs)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual('fake_ovsdb_id',
                             fake_dict[n_const.OVSDB_IDENTIFIER])
            update_mr.assert_called_with(self.context, fake_dict)

    def test_process_deleted_logical_switches(self):
        fake_dict = {}
        fake_deleted_logical_switches = [fake_dict]
        with mock.patch.object(lib, 'delete_logical_switch') as delete_ls:
            self.ovsdb_data._process_deleted_logical_switches(
                self.context, fake_deleted_logical_switches)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual('fake_ovsdb_id',
                             fake_dict[n_const.OVSDB_IDENTIFIER])
            delete_ls.assert_called_with(self.context, fake_dict)

    def test_get_agent_by_mac(self):
        fake_mac = {'mac': 'fake_mac_1'}
        fake_port = [{'binding:host_id': 'fake_host'}]
        with mock.patch.object(self.ovsdb_data, '_get_port_by_mac',
                               return_value=fake_port) as mock_get_port_mac, \
            mock.patch.object(
                self.ovsdb_data,
                '_get_agent_details_by_host') as mock_get_agent_detail:
            self.ovsdb_data._get_agent_by_mac(self.context, fake_mac)
            mock_get_port_mac.assert_called_with(self.context, 'fake_mac_1')
            mock_get_agent_detail.assert_called_with(self.context, 'fake_host')

    def test_get_agent_details_by_host(self):
        fake_agent = {'configurations': {'tunnel_types': ["vxlan"],
                      'l2_population': True}}
        fake_agents = [fake_agent]
        with mock.patch.object(self.ovsdb_data.core_plugin,
                               'get_agents',
                               return_value=fake_agents):
            l2pop_enabled = self.ovsdb_data._get_agent_details_by_host(
                self.context, 'fake_host')
            self.assertTrue(l2pop_enabled)

    def test_process_deleted_physical_switches(self):
        fake_dict = {}
        fake_deleted_physical_switches = [fake_dict]
        fake_ls_dict = {'uuid': 'ls-uuid'}
        fake_ls_list = [fake_ls_dict]
        with mock.patch.object(lib, 'delete_physical_switch') as delete_ps, \
            mock.patch.object(lib, 'get_all_physical_switches_by_ovsdb_id',
                              return_value=False) as get_ps, \
            mock.patch.object(lib, 'get_all_logical_switches_by_ovsdb_id',
                              return_value=fake_ls_list) as get_ls, \
            mock.patch.object(agent_api.L2gatewayAgentApi,
                              'delete_network') as del_network:
            self.ovsdb_data._process_deleted_physical_switches(
                self.context, fake_deleted_physical_switches)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual('fake_ovsdb_id',
                             fake_dict[n_const.OVSDB_IDENTIFIER])
            delete_ps.assert_called_with(self.context, fake_dict)
            get_ps.assert_called_with(self.context, 'fake_ovsdb_id')
            get_ls.assert_called_with(self.context, 'fake_ovsdb_id')
            del_network.assert_called_with(self.context, 'fake_ovsdb_id',
                                           'ls-uuid')

    def test_process_deleted_physical_ports(self):
        fake_dict = {'name': 'fake_uuid', 'uuid': 'fake_name'}
        fake_deleted_physical_ports = [fake_dict]
        fake_physical_port = {'uuid': 'fake_uuid',
                              'name': 'fake_name'}
        fake_physical_switch = {'uuid': 'fake_uuid',
                                'ovsdb_identifier': 'fake_ovsdb_id',
                                'name': 'fake_switch'},
        fake_vlan_binding = {'port_uuid:': 'fake_port_uuid',
                             'vlan': 'fake_vlan',
                             'logical_switch_uuid': 'fake_switch_uuid',
                             'ovsdb_identifier': 'fake_ovsdb_id'}
        with mock.patch.object(lib,
                               'delete_physical_port'), \
            mock.patch.object(lib,
                              'get_physical_port',
                              return_value=fake_physical_port), \
            mock.patch.object(lib, 'get_physical_switch',
                              return_vaue=fake_physical_switch), \
            mock.patch.object(lib,
                              'get_all_vlan_bindings_by_physical_port',
                              return_vaue=fake_vlan_binding), \
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_get_l2gw_ids_by_interface_switch',
                              return_value=['fake_uuid']), \
            mock.patch.object(
                l2gateway_db.L2GatewayMixin,
                '_delete_connection_by_l2gw_id') as l2gw_conn_del:
            self.ovsdb_data._process_deleted_physical_ports(
                self.context, fake_deleted_physical_ports)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual('fake_ovsdb_id',
                             fake_dict[n_const.OVSDB_IDENTIFIER])
            l2gw_conn_del.assert_called_with(self.context, 'fake_uuid')

    @mock.patch.object(lib, 'delete_physical_port')
    @mock.patch.object(lib, 'get_physical_port')
    @mock.patch.object(lib, 'get_physical_switch')
    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       '_get_l2gw_ids_by_interface_switch',
                       return_value=['fake_uuid'])
    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       '_delete_connection_by_l2gw_id')
    @mock.patch.object(lib,
                       'get_all_vlan_bindings_by_physical_port')
    @mock.patch.object(lib,
                       'get_all_vlan_bindings_by_logical_switch')
    @mock.patch.object(data.OVSDBData, '_delete_macs_from_ovsdb')
    @mock.patch.object(lib, 'delete_vlan_binding')
    def test_process_deleted_physical_ports_with_delete_macs(
            self, del_vlan, del_macs, get_vlan_by_ls, get_vlan_by_pp,
            l2gw_conn_del, get_l2gw, get_ps, get_pp, delete_pp):
        fake_dict = {'uuid': 'fake_uuid', 'name': 'fake_name',
                     'logical_switch_id': 'fake_ls_id',
                     'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_deleted_physical_ports = [fake_dict]
        fake_physical_port = {'uuid': 'fake_uuid',
                              'name': 'fake_name',
                              'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_physical_switch = {'uuid': 'fake_uuid',
                                'ovsdb_identifier': 'fake_ovsdb_id',
                                'name': 'fake_switch'}
        vlan_binding_dict = {'logical_switch_uuid': 'fake_ls_id',
                             'ovsdb_identifier': 'fake_ovsdb_id',
                             'port_uuid': 'fake_uuid',
                             'vlan': 'fake_vlan',
                             'logical_switch_id': 'fake_ls_id'}
        fake_vlan_binding_list = [vlan_binding_dict]
        fake_binding_list = [vlan_binding_dict]
        get_pp.return_value = fake_physical_port
        get_ps.return_vaue = fake_physical_switch
        get_vlan_by_pp.return_value = fake_vlan_binding_list
        get_vlan_by_ls.return_value = fake_binding_list
        self.ovsdb_data._process_deleted_physical_ports(
            self.context, fake_deleted_physical_ports)
        self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
        self.assertEqual('fake_ovsdb_id',
                         fake_dict[n_const.OVSDB_IDENTIFIER])
        l2gw_conn_del.assert_called_with(self.context, 'fake_uuid')
        get_vlan_by_pp.assert_called_with(self.context, fake_dict)
        del_vlan.assert_called_with(self.context, vlan_binding_dict)
        get_vlan_by_ls.assert_called_with(self.context, vlan_binding_dict)
        del_macs.assert_called_with(self.context,
                                    'fake_ls_id', 'fake_ovsdb_id')
        del_vlan.assert_called_with(self.context, vlan_binding_dict)
        delete_pp.assert_called_with(self.context, fake_dict)

    @mock.patch.object(data.OVSDBData,
                       '_get_logical_switch_ids',
                       return_value=['1'])
    @mock.patch.object(lib,
                       'get_all_physical_switches_by_ovsdb_id',
                       return_value=[{'tunnel_ip': '3.3.3.3'}])
    @mock.patch.object(data.OVSDBData,
                       '_get_fdb_entries')
    @mock.patch.object(lib,
                       'delete_physical_locator')
    @mock.patch.object(data.OVSDBData, '_get_agent_ips',
                       return_value={'1.1.1.1': 'hostname'})
    @mock.patch.object(tunnel_calls.Tunnel_Calls,
                       'trigger_l2pop_delete')
    def test_process_deleted_physical_locators(
            self, trig_l2pop, get_agent_ips, delete_pl, get_fdb, get_all_ps,
            get_ls):
        """Test case to test _process_deleted_physical_locators.

        for unicast rpc to the L2 agent
        """
        fake_dict1 = {'dst_ip': '1.1.1.1'}
        fake_dict2 = {'dst_ip': '2.2.2.2'}
        fake_deleted_physical_locators = [fake_dict2, fake_dict1]
        mock.patch.object(manager, 'NeutronManager').start()
        self.ovsdb_data._process_deleted_physical_locators(
            self.context, fake_deleted_physical_locators)
        self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict1)
        self.assertTrue(get_ls.called)
        self.assertTrue(get_all_ps.called)
        self.assertTrue(get_fdb.called)
        self.assertEqual('fake_ovsdb_id',
                         fake_dict1[n_const.OVSDB_IDENTIFIER])
        delete_pl.assert_called_with(self.context, fake_dict1)
        self.assertTrue(get_agent_ips.called)
        trig_l2pop.assert_called_with(self.context,
                                      mock.ANY,
                                      'hostname')

    @mock.patch.object(data.OVSDBData,
                       '_get_logical_switch_ids',
                       return_value=['1'])
    @mock.patch.object(lib,
                       'get_all_physical_switches_by_ovsdb_id',
                       return_value=[{'tunnel_ip': '3.3.3.3'}])
    @mock.patch.object(data.OVSDBData,
                       '_get_fdb_entries')
    @mock.patch.object(lib,
                       'delete_physical_locator')
    @mock.patch.object(data.OVSDBData, '_get_agent_ips',
                       return_value={'2.2.2.2': 'hostname'})
    @mock.patch.object(tunnel_calls.Tunnel_Calls,
                       'trigger_l2pop_delete')
    def test_process_deleted_physical_locators1(
            self, trig_l2pop, get_agent_ips, delete_pl, get_fdb,
            get_all_ps, get_ls):
        """Test case to test _process_deleted_physical_locators.

        for broadcast rpc to the L2 agents
        """
        fake_dict1 = {'dst_ip': '1.1.1.1'}
        fake_deleted_physical_locators = [fake_dict1]
        mock.patch.object(manager, 'NeutronManager').start()
        self.ovsdb_data._process_deleted_physical_locators(
            self.context, fake_deleted_physical_locators)
        self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict1)
        self.assertTrue(get_ls.called)
        self.assertTrue(get_all_ps.called)
        self.assertTrue(get_fdb.called)
        self.assertEqual('fake_ovsdb_id',
                         fake_dict1[n_const.OVSDB_IDENTIFIER])
        delete_pl.assert_called_once_with(self.context, fake_dict1)
        self.assertTrue(get_agent_ips.called)
        trig_l2pop.assert_called_with(self.context,
                                      mock.ANY)

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
                self.assertEqual('fake_ovsdb_id',
                                 fake_dict[n_const.OVSDB_IDENTIFIER])
                delete_ml.assert_called_with(self.context, fake_dict)

    def test_process_deleted_remote_macs(self):
        fake_dict = {}
        fake_deleted_remote_macs = [fake_dict]
        with mock.patch.object(lib, 'delete_ucast_mac_remote') as delete_mr:
            self.ovsdb_data._process_deleted_remote_macs(
                self.context, fake_deleted_remote_macs)
            self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict)
            self.assertEqual('fake_ovsdb_id',
                             fake_dict[n_const.OVSDB_IDENTIFIER])
            delete_mr.assert_called_with(self.context, fake_dict)

    @mock.patch.object(lib, 'get_physical_port')
    @mock.patch.object(lib, 'add_physical_port')
    @mock.patch.object(lib, 'get_all_vlan_bindings_by_physical_port')
    @mock.patch.object(lib, 'add_vlan_binding')
    @mock.patch.object(lib, 'update_physical_ports_status')
    def test_process_modified_physical_ports(self, update_pp_status, add_vlan,
                                             get_vlan, add_pp, get_pp):
        fake_dict1 = {}
        fake_dict2 = {'vlan_bindings': [fake_dict1],
                      'uuid': 'fake_uuid'}
        fake_modified_physical_ports = [fake_dict2]
        self.ovsdb_data._process_modified_physical_ports(
            self.context, fake_modified_physical_ports)
        self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict2)
        self.assertEqual('fake_ovsdb_id',
                         fake_dict2[n_const.OVSDB_IDENTIFIER])
        get_pp.assert_called_with(self.context, fake_dict2)
        update_pp_status.assert_called_with(self.context, fake_dict2)
        self.assertFalse(add_pp.called)
        get_vlan.assert_called_with(self.context, fake_dict2)
        self.assertIn(n_const.OVSDB_IDENTIFIER, fake_dict1)
        self.assertIn('port_uuid', fake_dict1)
        add_vlan.assert_called_with(self.context, fake_dict1)
