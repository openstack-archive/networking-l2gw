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

from neutron.common import rpc as n_rpc
from neutron.db import agents_db
from neutron.tests.unit.plugins.ml2 import test_plugin
from neutron_lib import context as ctx

from networking_l2gw.db.l2gateway.ovsdb import lib as db
from networking_l2gw.services.l2gateway.common import l2gw_validators
from networking_l2gw.services.l2gateway.common import ovsdb_schema
from networking_l2gw.services.l2gateway import exceptions as l2gw_exc
from networking_l2gw.services.l2gateway.ovsdb import data
from networking_l2gw.services.l2gateway.service_drivers import agent_api
from networking_l2gw.services.l2gateway.service_drivers import rpc_l2gw

from oslo_utils import importutils


class TestL2gwRpcDriver(test_plugin.Ml2PluginV2TestCase):

    def setUp(self):
        super(TestL2gwRpcDriver, self).setUp()
        self.service_plugin = mock.MagicMock()
        load_driver = mock.MagicMock()
        self.service_plugin._load_drivers.return_value = load_driver
        self.service_plugin._get_driver_for_provider.return_value = load_driver
        self.plugin = rpc_l2gw.L2gwRpcDriver(self.service_plugin)
        self.plugin.agent_rpc = mock.MagicMock()
        self.ovsdb_identifier = 'fake_ovsdb_id'
        self.context = mock.ANY

    @mock.patch.object(importutils,
                       'import_object')
    @mock.patch.object(agents_db,
                       'AgentExtRpcCallback')
    @mock.patch.object(n_rpc,
                       'create_connection')
    @mock.patch.object(n_rpc.Connection,
                       'consume_in_threads')
    @mock.patch.object(rpc_l2gw.LOG,
                       'debug')
    @mock.patch.object(rpc_l2gw.L2gwRpcDriver,
                       'start_l2gateway_agent_scheduler')
    def test_l2rpcdriver_init(self, scheduler, debug, consume_in_thread,
                              create_conn, agent_calback, import_obj):
        rpc_l2gw.L2gwRpcDriver(self.service_plugin)
        rpc_conn = create_conn.return_value
        rpc_conn.create_consumer.assert_called_with(
            mock.ANY, [mock.ANY, mock.ANY], fanout=mock.ANY)
        rpc_conn.consume_in_threads.assert_called_with()
        self.assertTrue(import_obj.called)
        self.assertTrue(agent_calback.called)
        self.assertTrue(create_conn.called)
        self.assertTrue(debug.called)
        self.assertTrue(scheduler.called)

    def test_validate_connection(self):
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100}
        fake_net_seg_list = [{'id': 'fake_id',
                              'network_type': 'fake_vxlan',
                              'physical_network': 'fake_phy_net',
                              'segmentation_id': 100}]
        fake_l2_gw = {'id': 'fake_l2gw_id'}
        fake_tenant_id = 'fake_tenant_id'
        fake_filters = {'network_id': ['fake_network_id'],
                        'tenant_id': [fake_tenant_id],
                        'l2_gateway_id': ['fake_l2gw_id']}
        with mock.patch.object(self.service_plugin,
                               '_is_vlan_configured_on_any_interface_for_l2gw',
                               return_value=False) as is_vlan, \
            mock.patch.object(l2gw_validators,
                              'validate_network_mapping_list',
                              return_value='fake_network_id') as val_ntwk, \
            mock.patch.object(self.service_plugin,
                              '_get_network_segments',
                              return_value=fake_net_seg_list), \
            mock.patch.object(self.service_plugin,
                              '_get_network',
                              return_value=True) as get_network, \
            mock.patch.object(self.service_plugin,
                              '_get_l2_gateway',
                              return_value=fake_l2_gw) as get_l2gw, \
            mock.patch.object(self.service_plugin,
                              '_retrieve_gateway_connections',
                              return_value=False) as ret_gw_conn, \
            mock.patch.object(self.service_plugin,
                              '_get_tenant_id_for_create',
                              return_value=fake_tenant_id) as get_ten_id, \
            mock.patch.object(self.service_plugin,
                              'get_l2_gateway_connections',
                              return_value=False) as get_l2_gw_conn, \
            mock.patch.object(
                self.plugin,
                '_check_port_fault_status_and_switch_fault_status') as pf_sf:
            self.plugin._validate_connection(self.context, fake_connection)
            is_vlan.assert_called_with(self.context, 'fake_l2gw_id')
            val_ntwk.assert_called_with(fake_connection, False)
            get_network.assert_called_with(self.context, 'fake_network_id')
            get_l2gw.assert_called_with(self.context, 'fake_l2gw_id')
            pf_sf.assert_called_with(self.context, 'fake_l2gw_id')
            ret_gw_conn.assert_called_with(self.context,
                                           'fake_l2gw_id',
                                           fake_connection)
            get_ten_id.assert_called_with(self.context, fake_l2_gw)
            get_l2_gw_conn.assert_called_with(self.context,
                                              filters=fake_filters)

    @mock.patch.object(db,
                       'get_physical_switch_by_name')
    @mock.patch.object(db,
                       'get_logical_switch_by_name')
    @mock.patch.object(db,
                       'get_physical_port_by_name_and_ps')
    def test_process_port_list(self, get_pp, get_ls, get_ps):
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100}
        fake_device = {'id': 'fake_device_id',
                       'device_name': 'fake_device_name'}
        fake_method = 'CREATE'
        fake_interface = {'interface_name': 'fake_interface_name'}
        fake_interface_list = [fake_interface]
        fake_physical_switch = {'uuid': 'fake_uuid',
                                'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_pp_dict = {'interface_name': 'fake_interface_name',
                        'ovsdb_identifier': 'fake_ovsdb_id',
                        'physical_switch_id': 'fake_uuid',
                        'logical_switch_name': 'fake_network_id',
                        'uuid': 'fake_uuid',
                        'name': 'fake_name'}
        fake_logical_switch = {'uuid': 'fake_uuid',
                               'name': 'fake_network_id'}
        fake_physical_port = {'uuid': 'fake_uuid',
                              'name': 'fake_name'}
        get_ps.return_value = fake_physical_switch
        get_ls.return_value = fake_logical_switch
        get_pp.return_value = fake_physical_port
        with mock.patch.object(
                self.service_plugin,
                'get_l2gateway_interfaces_by_device_id',
                return_value=fake_interface_list) as get_intf, \
                mock.patch.object(self.plugin,
                                  '_generate_port_list') as gen_port_list:
            self.plugin._process_port_list(self.context, fake_device,
                                           fake_connection,
                                           fake_method)
            get_intf.assert_called_with(self.context, 'fake_device_id')
            get_ps.assert_called_with(self.context, 'fake_device_name')
            get_pp.assert_called_with(self.context, fake_pp_dict)
            get_ls.assert_called_with(self.context, fake_pp_dict)
            gen_port_list.assert_called_with(
                self.context, fake_method, 100, fake_interface,
                fake_pp_dict, 'fake_uuid', fake_connection)

    def test_generate_port_list_for_create(self):
        fake_method = 'CREATE'
        fake_interface = {'interface_name': 'fake_interface_name'}
        fake_pp_dict = {'interface_name': 'fake_interface_name',
                        'ovsdb_identifier': 'fake_ovsdb_id',
                        'physical_switch_id': 'fake_uuid',
                        'logical_switch_name': 'fake_network_id',
                        'uuid': 'fake_uuid',
                        'name': 'fake_name'}
        fake_vlan_binding = {'vlan': 100,
                             'logical_switch_uuid': 'fake_uuid'}
        fake_vlan_binding_list = [fake_vlan_binding]
        with mock.patch.object(
            db, 'get_all_vlan_bindings_by_physical_port',
            return_value=fake_vlan_binding_list) as (
                get_vlan):
            self.plugin._generate_port_list(
                self.context, fake_method, 101, fake_interface,
                fake_pp_dict, 'fake_uuid')
            get_vlan.assert_called_with(self.context, fake_pp_dict)

    def test_generate_port_list_for_create_for_duplicate_seg_id(self):
        fake_method = 'CREATE'
        fake_interface = {'interface_name': 'fake_interface_name'}
        fake_pp_dict = {'interface_name': 'fake_interface_name',
                        'ovsdb_identifier': 'fake_ovsdb_id',
                        'physical_switch_id': 'fake_uuid',
                        'logical_switch_name': 'fake_network_id',
                        'uuid': 'fake_uuid',
                        'name': 'fake_name'}
        fake_vlan_binding = {'vlan': 100,
                             'logical_switch_uuid': 'fake_uuid'}
        fake_vlan_binding_list = [fake_vlan_binding]
        with mock.patch.object(
            db, 'get_all_vlan_bindings_by_physical_port',
            return_value=fake_vlan_binding_list) as (
                get_vlan):
            self.assertRaises(l2gw_exc.L2GatewayDuplicateSegmentationID,
                              self.plugin._generate_port_list,
                              self.context, fake_method, 100,
                              fake_interface, fake_pp_dict, 'fake_uuid')
            get_vlan.assert_called_with(self.context, fake_pp_dict)

    def test_generate_port_list_for_delete(self):
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100}
        fake_method = 'DELETE'
        fake_interface = {'interface_name': 'fake_interface_name'}
        fake_pp_dict = {'interface_name': 'fake_interface_name',
                        'ovsdb_identifier': 'fake_ovsdb_id',
                        'physical_switch_id': 'fake_uuid',
                        'logical_switch_name': 'fake_network_id',
                        'uuid': 'fake_uuid'}
        fake_vlan_binding = {'vlan': 100,
                             'logical_switch_uuid': 'fake_uuid'}
        fake_vlan_binding_list = [fake_vlan_binding]

        vlan_dict = {'vlan': 100,
                     'logical_switch_uuid': 'fake_uuid'}
        physical_port = ovsdb_schema.PhysicalPort(
            uuid='fake_uuid',
            name='fake_interface_name',
            phys_switch_id='fake_uuid',
            vlan_binding_dicts=None,
            port_fault_status=None)
        phys_port_dict = physical_port.__dict__
        phys_port_dict['vlan_bindings'] = [vlan_dict]
        with mock.patch.object(
            db,
            'get_all_vlan_bindings_by_physical_port',
            return_value=fake_vlan_binding_list) as (
                get_vlan):
            port = self.plugin._generate_port_list(
                self.context, fake_method, 100, fake_interface,
                fake_pp_dict, 'fake_uuid', fake_connection)
            get_vlan.assert_called_with(self.context, fake_pp_dict)
            self.assertEqual(phys_port_dict, port)

    def test_get_ip_details(self):
        fake_port = {'binding:host_id': 'fake_host',
                     'fixed_ips': [{'ip_address': 'fake_ip'}]}
        fake_agent = {'configurations': {'tunneling_ip': 'fake_tun_ip'}}
        with mock.patch.object(self.plugin,
                               '_get_agent_details',
                               return_value=fake_agent) as get_agent:
            (ret_dst_ip, ret_ip_add) = self.plugin._get_ip_details(
                self.context, fake_port)
            get_agent.assert_called_with(self.context, 'fake_host')
            self.assertEqual('fake_tun_ip', ret_dst_ip)
            self.assertEqual('fake_ip', ret_ip_add)

    def test_get_agent_details_for_no_ovs_agent(self):
        core_plugin = mock.PropertyMock()
        type(self.service_plugin)._core_plugin = core_plugin
        (self.service_plugin._core_plugin.get_agents.
         return_value) = []
        self.assertRaises(l2gw_exc.L2AgentNotFoundByHost,
                          self.plugin._get_agent_details,
                          self.context, 'fake_host')

    def test_get_network_details(self):
        fake_network = {'id': 'fake_network_id',
                        'name': 'fake_network_name',
                        'provider:segmentation_id': 'fake_key'}
        core_plugin = mock.PropertyMock()
        type(self.service_plugin)._core_plugin = core_plugin
        (self.service_plugin._core_plugin.get_network.
         return_value) = fake_network

    def test_get_port_details(self):
        fake_port = {'binding:host_id': 'fake_host',
                     'fixed_ips': [{'ip_address': 'fake_ip'}],
                     'mac_address': 'fake_mac_add'}
        fake_port_list = [fake_port]
        core_plugin = mock.PropertyMock()
        type(self.service_plugin)._core_plugin = core_plugin
        (self.service_plugin._core_plugin.get_ports.
         return_value) = fake_port_list

    def test_get_agent_details(self):
        fake_agent = [{'configurations': {'tunneling_ip': 'fake_tun_ip'}}]
        core_plugin = mock.PropertyMock()
        type(self.service_plugin)._core_plugin = core_plugin
        (self.service_plugin._core_plugin.get_agents.return_value) = fake_agent

    def test_get_logical_switch_dict(self):
        fake_logical_switch = {'uuid': 'fake_uuid',
                               'name': 'fake_network_id'}
        fake_ls = None
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100}
        fake_network = {'id': 'fake_network_id',
                        'name': 'fake_network_name',
                        'provider:network_type': 'vxlan',
                        'provider:segmentation_id': 'fake_key'}
        fake_ls_dict = {'uuid': 'fake_uuid',
                        'name': 'fake_network_id',
                        'description': 'fake_network_name',
                        'key': 'fake_key'}
        fake_ls_dict_without_ls = {'uuid': None,
                                   'name': 'fake_network_id',
                                   'description': 'fake_network_name',
                                   'key': 'fake_key'}
        with mock.patch.object(self.plugin,
                               '_get_network_details',
                               return_value=fake_network) as get_network:
            ret_ls_dict = self.plugin._get_logical_switch_dict(
                self.context, fake_logical_switch, fake_connection)
            ret_ls_dict_without_ls = self.plugin._get_logical_switch_dict(
                self.context, fake_ls, fake_connection)
            get_network.assert_called_with(self.context, 'fake_network_id')
            self.assertEqual(fake_ls_dict, ret_ls_dict)
            self.assertEqual(fake_ls_dict_without_ls, ret_ls_dict_without_ls)

    def test_get_logical_switch_dict_for_multi_segment_network(self):
        fake_logical_switch = {'uuid': 'fake_uuid',
                               'name': 'fake_network_id'}
        fake_ls = None
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100}
        fake_network = {'id': 'fake_network_id',
                        'name': 'fake_network_name',
                        'segments': [{"provider:network_type": "vxlan",
                                      "provider:segmentation_id": 'fake_key'},
                                     {"provider:network_type": "vlan",
                                      "provider:segmentation_id": 'fake_key'}]}
        fake_ls_dict = {'uuid': 'fake_uuid',
                        'name': 'fake_network_id',
                        'description': 'fake_network_name',
                        'key': 'fake_key'}
        fake_ls_dict_without_ls = {'uuid': None,
                                   'name': 'fake_network_id',
                                   'description': 'fake_network_name',
                                   'key': 'fake_key'}
        with mock.patch.object(self.plugin,
                               '_get_network_details',
                               return_value=fake_network) as get_network:
            ret_ls_dict = self.plugin._get_logical_switch_dict(
                self.context, fake_logical_switch, fake_connection)
            ret_ls_dict_without_ls = self.plugin._get_logical_switch_dict(
                self.context, fake_ls, fake_connection)
            get_network.assert_called_with(self.context, 'fake_network_id')
            self.assertEqual(fake_ls_dict, ret_ls_dict)
            self.assertEqual(fake_ls_dict_without_ls, ret_ls_dict_without_ls)

    def test_get_logical_switch_dict_for_non_Vxlan_networks(self):
        fake_logical_switch = {'uuid': 'fake_uuid',
                               'name': 'fake_network_id'}
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100}
        fake_network = {'id': 'fake_network_id',
                        'name': 'fake_network_name',
                        'segments': [{"provider:network_type": "vlan",
                                      "provider:segmentation_id": 'fake_key'},
                                     {"provider:network_type": "gre",
                                      "provider:segmentation_id": 'fake_key'}]}
        with mock.patch.object(self.plugin,
                               '_get_network_details',
                               return_value=fake_network) as get_network:
            self.assertRaises(l2gw_exc.VxlanSegmentationIDNotFound,
                              self.plugin._get_logical_switch_dict,
                              self.context, fake_logical_switch,
                              fake_connection)
            get_network.assert_called_with(self.context, 'fake_network_id')

    def test_get_logical_switch_dict_for_multiple_vxlan_segments(self):
        fake_logical_switch = {'uuid': 'fake_uuid',
                               'name': 'fake_network_id'}
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100}
        fake_network = {'id': 'fake_network_id',
                        'name': 'fake_network_name',
                        'segments': [{"provider:network_type": "vxlan",
                                      "provider:segmentation_id": 'seg_1'},
                                     {"provider:network_type": "vxlan",
                                      "provider:segmentation_id": 'seg_2'}]}
        with mock.patch.object(self.plugin,
                               '_get_network_details',
                               return_value=fake_network) as get_network:
            self.assertRaises(l2gw_exc.MultipleVxlanSegmentsFound,
                              self.plugin._get_logical_switch_dict,
                              self.context, fake_logical_switch,
                              fake_connection)
            get_network.assert_called_with(self.context, 'fake_network_id')

    @mock.patch.object(db,
                       'get_physical_locator_by_dst_ip')
    def test_get_locator_list(self, get_pl_by_dst_ip):
        fake_dst_ip = 'fake_tun_ip'
        fake_ovsdb_id = 'fake_ovsdb_id'
        fake_mac_list = []
        fake_locator_list = []
        fake_locator_dict = {'uuid': 'fake_uuid',
                             'dst_ip': 'fake_tun_ip',
                             'ovsdb_identifier': 'fake_ovsdb_id',
                             'macs': []}
        fake_pl = {'uuid': 'fake_uuid',
                   'dst_ip': 'fake_tun_ip'}
        fale_pl_list = [fake_locator_dict]
        get_pl_by_dst_ip.return_value = fake_pl
        with mock.patch.object(
                self.plugin,
                '_get_physical_locator_dict',
                return_value=fake_locator_dict) as get_pl_dict:
            ret_pl_list = self.plugin._get_locator_list(
                self.context, fake_dst_ip, fake_ovsdb_id,
                fake_mac_list, fake_locator_list)
            get_pl_by_dst_ip.assert_called_with(self.context,
                                                fake_locator_dict)
            get_pl_dict.assert_called_with(fake_dst_ip,
                                           'fake_uuid', fake_mac_list)
            self.assertEqual(fale_pl_list, ret_pl_list)

    @mock.patch.object(db,
                       'get_physical_switch_by_name')
    def test_get_identifer_list(self, get_ps):
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100}
        fake_device = {'id': 'fake_device_id',
                       'device_name': 'fake_device_name'}
        fake_device_list = [fake_device]
        fake_physical_switch = {'uuid': 'fake_uuid',
                                'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_identifier_set = set(['fake_ovsdb_id'])
        get_ps.return_value = fake_physical_switch
        with mock.patch.object(self.service_plugin,
                               'get_l2gateway_devices_by_gateway_id',
                               return_value=fake_device_list):
            ret_value = self.plugin._get_identifer_list(self.context,
                                                        fake_connection)
            (self.service_plugin.get_l2gateway_devices_by_gateway_id.
             assert_called_with(mock.ANY, mock.ANY))
            db.get_physical_switch_by_name.assert_called_with(
                self.context, 'fake_device_name')
            self.assertEqual(fake_identifier_set, ret_value)

    def test_get_set_of_ovsdb_ids(self):
        fake_connection = {'id': 'fake_id',
                           'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100}
        fake_gw_conn_ovsdb_set = set(['fake_ovsdb_id'])
        fake_connection_list = [fake_connection]
        with mock.patch.object(self.service_plugin,
                               'get_l2_gateway_connections',
                               return_value=fake_connection_list):
            ret_value = self.plugin._get_set_of_ovsdb_ids(
                self.context, fake_connection,
                fake_gw_conn_ovsdb_set)
            self.service_plugin.get_l2_gateway_connections.assert_called_with(
                mock.ANY, filters=mock.ANY)
            self.assertEqual(fake_gw_conn_ovsdb_set, ret_value)

    def test_remove_vm_macs(self):
        fake_network_id = 'fake_network_id'
        fake_ovsdb_id_set = set(['fake_ovsdb_id'])
        fake_port = {'binding:host_id': 'fake_host',
                     'fixed_ips': [{'ip_address': 'fake_ip'}],
                     'mac_address': 'fake_mac_add'}
        fake_port_list = [fake_port]
        with mock.patch.object(self.plugin,
                               '_get_port_details',
                               return_value=fake_port_list) as get_port, \
                mock.patch.object(self.plugin,
                                  'delete_port_mac') as delete_mac:
            self.plugin._remove_vm_macs(self.context,
                                        fake_network_id,
                                        fake_ovsdb_id_set)
            get_port.assert_called_with(self.context, fake_network_id)
            delete_mac.assert_called_with(self.context,
                                          fake_port_list)

    def test_add_port_mac(self):
        fake_ip1 = "fake_ip1"
        fake_ip2 = "fake_ip2"
        fake_network_dict = {'provider:segmentation_id': 100,
                             'name': 'fake_name',
                             'id': 'fake_network_id'}
        fake_conn_dict = {'id': 'fake_conn_id',
                          'l2_gateway_id': 'fake_gateway_id'}
        fake_conn_list = [fake_conn_dict]
        fake_logical_switch = {'ovsdb_identifier': 'fake_ovsdb_id',
                               'uuid': 'fake_network_id',
                               'description': 'fake_name'}
        fake_logical_switch_list = [fake_logical_switch]
        fake_locator_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                             'uuid': 'fake_locator_id',
                             'dst_ip': 'fake_ip2'}
        fake_pl_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                        'dst_ip': 'fake_ip1'}
        fake_mac_dict = {'mac': 'fake_mac',
                         'logical_switch_id': 'fake_network_id',
                         'physical_locator_id': 'fake_locator_id',
                         'ip_address': 'fake_ip1'}
        fake_dict = fake_mac_dict
        fake_dict['ovsdb_identifier'] = 'fake_ovsdb_id'
        core_plugin = mock.PropertyMock()
        type(self.service_plugin)._core_plugin = core_plugin
        (self.service_plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        ovsdb_identifier = 'fake_ovsdb_id'
        with mock.patch.object(self.plugin,
                               '_get_ip_details',
                               return_value=(fake_ip1,
                                             fake_ip2)),\
            mock.patch.object(self.plugin,
                              '_get_network_details',
                              return_value=fake_network_dict) as get_network,\
            mock.patch.object(self.service_plugin,
                              'get_l2_gateway_connections',
                              return_value=fake_conn_list) as get_l2gw_conn,\
            mock.patch.object(self.plugin,
                              '_form_physical_locator_schema',
                              return_value=fake_locator_dict) as get_pl,\
            mock.patch.object(ovsdb_schema,
                              'UcastMacsRemote') as mock_ucmr,\
            mock.patch.object(self.plugin,
                              '_get_dict',
                              return_value=fake_dict) as get_dict,\
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=False) as get_ucast_mac,\
            mock.patch.object(self.plugin.agent_rpc,
                              'add_vif_to_gateway') as add_rpc,\
            mock.patch.object(self.plugin.agent_rpc,
                              'update_vif_to_gateway') as update_rpc,\
            mock.patch.object(db,
                              'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_list):
            remote_mac = ovsdb_schema.UcastMacsRemote(
                None, fake_dict['mac'], fake_logical_switch['uuid'],
                fake_locator_dict['uuid'],
                fake_ip2)
            mock_ucmr.return_value = remote_mac
            self.plugin.add_port_mac(self.context, fake_dict)
            get_network.assert_called_with(self.context, 'fake_network_id')
            get_l2gw_conn.assert_called_with(
                self.context, filters={'network_id': ['fake_network_id']})
            get_pl.assert_called_with(self.context, fake_pl_dict)
            get_ucast_mac.assert_called_with(self.context, fake_dict)
            get_dict.assert_called_with(remote_mac)
            mock_ucmr.assert_called_with(
                uuid=None,
                mac=fake_dict['mac'],
                logical_switch_id=fake_logical_switch['uuid'],
                physical_locator_id=fake_locator_dict['uuid'],
                ip_address=fake_ip2)
            add_rpc.assert_called_with(
                self.context, ovsdb_identifier,
                fake_logical_switch, fake_locator_dict, fake_dict)
            self.assertFalse(update_rpc.called)

    @mock.patch.object(db,
                       'get_all_logical_switches_by_name')
    @mock.patch.object(db,
                       'get_ucast_mac_remote_by_mac_and_ls',
                       return_value=True)
    @mock.patch.object(agent_api.L2gatewayAgentApi,
                       'delete_vif_from_gateway')
    @mock.patch.object(db,
                       'get_logical_switch_by_name')
    def test_delete_port_mac_for_multiple_vlan_bindings(
            self, get_ls, delete_rpc, get_mac, get_all_ls):
        fake_port_list = [{'network_id': 'fake_network_id',
                           'device_owner': 'fake_owner',
                           'mac_address': 'fake_mac',
                           'ovsdb_identifier': 'fake_ovsdb_id'}]
        fake_logical_switch_dict = {'uuid': 'fake_uuid',
                                    'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_logical_switch_list = [fake_logical_switch_dict]
        lg_dict = {'logical_switch_name': 'fake_network_id',
                   'ovsdb_identifier': 'fake_ovsdb_id'}
        get_all_ls.return_value = fake_logical_switch_list
        get_ls.return_value = fake_logical_switch_dict
        with mock.patch.object(self.service_plugin,
                               'get_l2_gateway_connections',
                               return_value=[1, 2]):
            self.plugin.delete_port_mac(self.context, fake_port_list)
            self.assertFalse(get_all_ls.called)
            get_ls.assert_called_with(self.context, lg_dict)
            self.assertFalse(get_mac.called)
            self.assertFalse(delete_rpc.called)

    def test_add_port_mac_with_ovsdb_server_down(self):
        "Test case to test add_port_mac when the OVSDB server is down."
        fake_ip1 = "fake_ip1"
        fake_ip2 = "fake_ip2"
        fake_network_dict = {'provider:segmentation_id': 100,
                             'name': 'fake_name',
                             'id': 'fake_network_id'}
        fake_conn_dict = {'id': 'fake_conn_id',
                          'l2_gateway_id': 'fake_gateway_id'}
        fake_conn_list = [fake_conn_dict]
        fake_logical_switch = {'ovsdb_identifier': 'fake_ovsdb_id',
                               'uuid': 'fake_network_id',
                               'description': 'fake_name'}
        fake_logical_switch_list = [fake_logical_switch]
        fake_locator_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                             'uuid': 'fake_locator_id',
                             'dst_ip': 'fake_ip2'}
        fake_pl_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                        'dst_ip': 'fake_ip1'}
        fake_mac_dict = {'mac': 'fake_mac',
                         'logical_switch_id': 'fake_network_id',
                         'physical_locator_id': 'fake_locator_id',
                         'ip_address': 'fake_ip1'}
        fake_dict = fake_mac_dict
        fake_dict['ovsdb_identifier'] = 'fake_ovsdb_id'
        core_plugin = mock.PropertyMock()
        type(self.service_plugin)._core_plugin = core_plugin
        (self.service_plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        ovsdb_identifier = 'fake_ovsdb_id'
        with mock.patch.object(self.plugin,
                               '_get_ip_details',
                               return_value=(fake_ip1,
                                             fake_ip2)), \
                mock.patch.object(self.plugin,
                                  '_get_network_details',
                                  return_value=fake_network_dict) as get_network, \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway_connections',
                                  return_value=fake_conn_list), \
                mock.patch.object(self.plugin,
                                  '_form_physical_locator_schema',
                                  return_value=fake_locator_dict) as get_pl, \
                mock.patch.object(ovsdb_schema,
                                  'UcastMacsRemote') as mock_ucmr, \
                mock.patch.object(self.plugin,
                                  '_get_dict',
                                  return_value=fake_dict) as get_dict, \
                mock.patch.object(db,
                                  'get_ucast_mac_remote_by_mac_and_ls',
                                  return_value=False) as get_ucast_mac, \
                mock.patch.object(self.plugin.agent_rpc,
                                  'add_vif_to_gateway',
                                  side_effect=RuntimeError) as add_rpc, \
                mock.patch.object(self.plugin.agent_rpc,
                                  'update_vif_to_gateway') as update_rpc, \
                mock.patch.object(db, 'add_pending_ucast_mac_remote') as add_pending_mac, \
                mock.patch.object(db, 'get_all_logical_switches_by_name',
                                  return_value=fake_logical_switch_list):
            remote_mac = ovsdb_schema.UcastMacsRemote(
                None, fake_dict['mac'], fake_logical_switch['uuid'],
                fake_locator_dict['uuid'],
                fake_ip2)
            mock_ucmr.return_value = remote_mac
            self.plugin.add_port_mac(self.context, fake_dict)
            get_network.assert_called_with(mock.ANY, mock.ANY)
            self.service_plugin.get_l2_gateway_connections.assert_called_with(
                mock.ANY, filters=mock.ANY)
            get_pl.assert_called_with(self.context, fake_pl_dict)
            get_dict.assert_called_with(remote_mac)
            get_ucast_mac.assert_called_with(self.context, fake_dict)
            add_rpc.assert_called_with(
                self.context, ovsdb_identifier,
                fake_logical_switch, fake_locator_dict, fake_dict)
            self.assertFalse(update_rpc.called)
            self.assertTrue(add_pending_mac.called)

    def test_add_port_mac_vm_migrate(self):
        fake_ip1 = "fake_ip1"
        fake_ip2 = "fake_ip2"
        fake_network_dict = {'provider:segmentation_id': 100,
                             'name': 'fake_name',
                             'id': 'fake_network_id'}
        fake_conn_dict = {'id': 'fake_conn_id',
                          'l2_gateway_id': 'fake_gateway_id'}
        fake_conn_list = [fake_conn_dict]
        fake_logical_switch = {'ovsdb_identifier': 'fake_ovsdb_id',
                               'uuid': 'fake_network_id',
                               'description': 'fake_name'}
        fake_logical_switch_list = [fake_logical_switch]
        fake_locator_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                             'uuid': 'fake_locator_id',
                             'dst_ip': 'fake_ip2'}
        fake_pl_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                        'dst_ip': 'fake_ip1'}
        fake_mac_dict = {'mac': 'fake_mac',
                         'uuid': 'fake_mac_id',
                         'locator': 'fake_locator_id2',
                         'logical_switch_id': 'fake_network_id',
                         'physical_locator_id': 'fake_locator_id1',
                         'ip_address': 'fake_ip1'}
        fake_dict = fake_mac_dict
        fake_dict['ovsdb_identifier'] = 'fake_ovsdb_id'
        core_plugin = mock.PropertyMock()
        type(self.service_plugin)._core_plugin = core_plugin
        (self.service_plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        ovsdb_identifier = 'fake_ovsdb_id'
        with mock.patch.object(self.plugin,
                               '_get_ip_details',
                               return_value=(fake_ip1,
                                             fake_ip2)), \
                mock.patch.object(self.plugin,
                                  '_get_network_details',
                                  return_value=fake_network_dict) as get_network, \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway_connections',
                                  return_value=fake_conn_list) as get_l2gw_conn, \
                mock.patch.object(self.plugin,
                                  '_form_physical_locator_schema',
                                  return_value=fake_locator_dict) as get_pl, \
                mock.patch.object(self.plugin,
                                  '_get_dict',
                                  return_value=fake_dict), \
                mock.patch.object(db,
                                  'get_ucast_mac_remote_by_mac_and_ls',
                                  return_value=fake_mac_dict) as get_ucast_mac, \
                mock.patch.object(self.plugin.agent_rpc,
                                  'add_vif_to_gateway') as add_rpc, \
                mock.patch.object(self.plugin.agent_rpc,
                                  'update_vif_to_gateway') as update_rpc, \
                mock.patch.object(db,
                                  'get_all_logical_switches_by_name',
                                  return_value=fake_logical_switch_list):
            self.plugin.add_port_mac(self.context, fake_dict)
            get_network.assert_called_with(self.context, 'fake_network_id')
            get_l2gw_conn.assert_called_with(
                self.context, filters={'network_id': ['fake_network_id']})
            get_pl.assert_called_with(self.context, fake_pl_dict)
            get_ucast_mac.assert_called_with(self.context, fake_dict)
            self.assertFalse(add_rpc.called)
            update_rpc.assert_called_with(
                self.context, ovsdb_identifier,
                fake_locator_dict, fake_dict)

    def test_add_port_mac_vm_migrate_with_ovsdb_server_down(self):
        "Test case to test update_port_mac when the OVSDB server is down."
        fake_ip1 = "fake_ip1"
        fake_ip2 = "fake_ip2"
        fake_network_dict = {'provider:segmentation_id': 100,
                             'name': 'fake_name',
                             'id': 'fake_network_id'}
        fake_conn_dict = {'id': 'fake_conn_id',
                          'l2_gateway_id': 'fake_gateway_id'}
        fake_conn_list = [fake_conn_dict]
        fake_logical_switch = {'ovsdb_identifier': 'fake_ovsdb_id',
                               'uuid': 'fake_network_id',
                               'description': 'fake_name'}
        fake_logical_switch_list = [fake_logical_switch]
        fake_locator_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                             'uuid': 'fake_locator_id',
                             'dst_ip': 'fake_ip2'}
        fake_pl_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                        'dst_ip': 'fake_ip1'}
        fake_mac_dict = {'mac': 'fake_mac',
                         'uuid': 'fake_mac_id',
                         'locator': 'fake_locator_id2',
                         'logical_switch_id': 'fake_network_id',
                         'physical_locator_id': 'fake_locator_id1',
                         'ip_address': 'fake_ip1'}
        fake_dict = fake_mac_dict
        fake_dict['ovsdb_identifier'] = 'fake_ovsdb_id'
        core_plugin = mock.PropertyMock()
        type(self.service_plugin)._core_plugin = core_plugin
        (self.service_plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        with mock.patch.object(self.plugin,
                               '_get_ip_details',
                               return_value=(fake_ip1,
                                             fake_ip2)), \
                mock.patch.object(self.plugin,
                                  '_get_network_details',
                                  return_value=fake_network_dict) as get_network, \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway_connections',
                                  return_value=fake_conn_list) as get_l2gw_conn, \
                mock.patch.object(self.plugin,
                                  '_form_physical_locator_schema',
                                  return_value=fake_locator_dict) as get_pl, \
                mock.patch.object(self.plugin,
                                  '_get_dict',
                                  return_value=fake_dict), \
                mock.patch.object(db,
                                  'get_ucast_mac_remote_by_mac_and_ls',
                                  return_value=fake_mac_dict) as get_ucast_mac, \
                mock.patch.object(self.plugin.agent_rpc,
                                  'add_vif_to_gateway') as add_rpc, \
                mock.patch.object(self.plugin.agent_rpc,
                                  'update_vif_to_gateway',
                                  side_effect=RuntimeError) as update_rpc, \
                mock.patch.object(db, 'add_pending_ucast_mac_remote') as add_pending_mac, \
                mock.patch.object(db, 'get_all_logical_switches_by_name',
                                  return_value=fake_logical_switch_list):
            self.plugin.add_port_mac(self.context, fake_dict)
            get_network.assert_called_with(self.context, 'fake_network_id')
            get_l2gw_conn.assert_called_with(
                self.context, filters={'network_id': ['fake_network_id']})
            get_pl.assert_called_with(self.context, fake_pl_dict)
            get_ucast_mac.assert_called_with(self.context, fake_dict)
            self.assertFalse(add_rpc.called)
            self.assertTrue(update_rpc.called)
            self.assertTrue(add_pending_mac.called)

    def test_add_port_mac_tunnel_recreation(self):
        "Test case to test recreation of tunnels"
        "when the openvswitch agent is restarted."
        fake_ip1 = "fake_ip1"
        fake_ip2 = "fake_ip2"
        fake_network_dict = {'provider:segmentation_id': 100,
                             'name': 'fake_name',
                             'id': 'fake_network_id'}
        fake_conn_dict = {'id': 'fake_conn_id',
                          'l2_gateway_id': 'fake_gateway_id'}
        fake_conn_list = [fake_conn_dict]
        fake_logical_switch = {'ovsdb_identifier': 'fake_ovsdb_id',
                               'uuid': 'fake_network_id',
                               'description': 'fake_name'}
        fake_logical_switch_list = [fake_logical_switch]
        fake_locator_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                             'uuid': 'fake_locator_id',
                             'dst_ip': 'fake_ip2'}
        fake_pl_dict = {'ovsdb_identifier': 'fake_ovsdb_id',
                        'dst_ip': 'fake_ip1'}
        fake_mac_dict = {'mac': 'fake_mac',
                         'uuid': 'fake_mac_id',
                         'locator': 'fake_locator_id',
                         'logical_switch_id': 'fake_network_id',
                         'physical_locator_id': 'fake_locator_id',
                         'ip_address': 'fake_ip1'}
        fake_dict = fake_mac_dict
        fake_dict['ovsdb_identifier'] = 'fake_ovsdb_id'
        core_plugin = mock.PropertyMock()
        type(self.service_plugin)._core_plugin = core_plugin
        (self.service_plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        with mock.patch.object(self.plugin,
                               '_get_ip_details',
                               return_value=(fake_ip1,
                                             fake_ip2)), \
                mock.patch.object(self.plugin,
                                  '_get_network_details',
                                  return_value=fake_network_dict) as get_network, \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway_connections',
                                  return_value=fake_conn_list) as get_l2gw_conn, \
                mock.patch.object(self.plugin,
                                  '_form_physical_locator_schema',
                                  return_value=fake_locator_dict) as get_pl, \
                mock.patch.object(self.plugin,
                                  '_get_dict',
                                  return_value=fake_dict), \
                mock.patch.object(db,
                                  'get_ucast_mac_remote_by_mac_and_ls',
                                  return_value=fake_mac_dict) as get_ucast_mac, \
                mock.patch.object(agent_api.L2gatewayAgentApi,
                                  'add_vif_to_gateway') as add_rpc, \
                mock.patch.object(data.L2GatewayOVSDBCallbacks,
                                  'get_ovsdbdata_object') as get_ovsdbdata_obj, \
                mock.patch.object(db,
                                  'get_all_logical_switches_by_name',
                                  return_value=fake_logical_switch_list):
            self.plugin.add_port_mac(self.context, fake_dict)
            get_network.assert_called_with(self.context, 'fake_network_id')
            get_l2gw_conn.assert_called_with(
                self.context, filters={'network_id': ['fake_network_id']})
            get_pl.assert_called_with(self.context, fake_pl_dict)
            get_ucast_mac.assert_called_with(self.context, fake_dict)
            self.assertFalse(add_rpc.called)
            self.assertTrue(get_ovsdbdata_obj.called)

    @mock.patch.object(db,
                       'get_all_logical_switches_by_name')
    @mock.patch.object(db,
                       'get_ucast_mac_remote_by_mac_and_ls',
                       return_value=True)
    def test_delete_port_mac_with_list(self,
                                       get_mac, get_ls):
        network_id = 'fake_network_id'
        fake_port_dict = {'network_id': 'fake_network_id',
                          'device_owner': 'fake_owner',
                          'mac_address': 'fake_mac',
                          'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_logical_switch_dict = {'uuid': 'fake_uuid',
                                    'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_logical_switch_list = [fake_logical_switch_dict]
        fake_dict = {'mac': 'fake_mac',
                     'logical_switch_uuid': 'fake_uuid',
                     'ovsdb_identifier': 'fake_ovsdb_id'}
        get_ls.return_value = fake_logical_switch_list
        with mock.patch.object(self.plugin.agent_rpc,
                               'delete_vif_from_gateway') as delete_rpc, \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway_connections',
                                  return_value=True):
            self.plugin.delete_port_mac(self.context, fake_port_dict)
            get_ls.assert_called_with(self.context, network_id)
            get_mac.assert_called_with(self.context, fake_dict)
            delete_rpc.assert_called_with(
                self.context, 'fake_ovsdb_id', 'fake_uuid', ['fake_mac'])

    @mock.patch.object(db,
                       'get_logical_switch_by_name')
    @mock.patch.object(db,
                       'get_all_logical_switches_by_name')
    @mock.patch.object(db,
                       'get_ucast_mac_remote_by_mac_and_ls',
                       return_value=True)
    def test_delete_port_mac_for_single_l2gw_connection(self,
                                                        get_mac, get_ls,
                                                        get_ls_by_name):
        fake_port_dict = {'network_id': 'fake_network_id',
                          'device_owner': 'fake_owner',
                          'mac_address': 'fake_mac',
                          'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_port_list = [fake_port_dict]
        fake_rec_dict = {'uuid': 'fake_network_id',
                         'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_dict = {'logical_switch_name': 'fake_network_id',
                     'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_ucast_mac_and_ls = {'mac': 'fake_mac',
                                 'logical_switch_uuid': 'fake_network_id',
                                 'ovsdb_identifier': 'fake_ovsdb_id'}
        get_ls_by_name.return_value = fake_rec_dict
        with mock.patch.object(self.plugin.agent_rpc,
                               'delete_vif_from_gateway') as delete_rpc, \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway_connections',
                                  return_value=[1]):
            self.plugin.delete_port_mac(self.context, fake_port_list)
            get_ls_by_name.assert_called_with(self.context, fake_dict)
            get_ls.assert_not_called()
            get_mac.assert_called_with(self.context, fake_ucast_mac_and_ls)
            delete_rpc.assert_called_with(
                self.context, 'fake_ovsdb_id', 'fake_network_id', ['fake_mac'])

    @mock.patch.object(db,
                       'get_logical_switch_by_name')
    @mock.patch.object(db,
                       'get_all_logical_switches_by_name')
    @mock.patch.object(db,
                       'get_ucast_mac_remote_by_mac_and_ls',
                       return_value=True)
    def test_delete_port_mac_for_multiple_l2gw_connection(self,
                                                          get_mac, get_ls,
                                                          get_ls_by_name):
        fake_port_dict = {'network_id': 'fake_network_id',
                          'device_owner': 'fake_owner',
                          'mac_address': 'fake_mac',
                          'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_port_list = [fake_port_dict]
        fake_rec_dict = {'logical_switch_name': 'fake_network_id',
                         'ovsdb_identifier': 'fake_ovsdb_id'}
        with mock.patch.object(self.plugin.agent_rpc,
                               'delete_vif_from_gateway') as delete_rpc, \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway_connections',
                                  return_value=[1, 2]):
            self.plugin.delete_port_mac(self.context, fake_port_list)
            get_ls_by_name.assert_called_with(self.context, fake_rec_dict)
            get_ls.assert_not_called()
            get_mac.assert_not_called()
            delete_rpc.assert_not_called()

    @mock.patch.object(db,
                       'get_all_logical_switches_by_name')
    @mock.patch.object(db,
                       'get_ucast_mac_remote_by_mac_and_ls',
                       return_value=True)
    @mock.patch.object(db,
                       'get_all_vlan_bindings_by_logical_switch',
                       return_value=[1])
    @mock.patch.object(db,
                       'get_logical_switch_by_name')
    def test_delete_port_mac(self, get_ls, get_vlan_binding, get_mac,
                             get_all_ls):
        fake_port_list = [{'network_id': 'fake_network_id',
                           'device_owner': 'fake_owner',
                           'mac_address': 'fake_mac',
                           'allowed_address_pairs': [{'mac_address':
                                                      'fake_pairs'}],
                           'ovsdb_identifier': 'fake_ovsdb_id'}]
        fake_logical_switch_dict = {'uuid': 'fake_uuid',
                                    'ovsdb_identifier': 'fake_ovsdb_id'}
        lg_dict = {'logical_switch_name': 'fake_network_id',
                   'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_dict = {'mac': 'fake_mac',
                     'logical_switch_uuid': 'fake_uuid',
                     'ovsdb_identifier': 'fake_ovsdb_id'}
        get_all_ls.return_value = fake_logical_switch_dict
        get_ls.return_value = fake_logical_switch_dict
        with mock.patch.object(self.plugin.agent_rpc,
                               'delete_vif_from_gateway') as delete_rpc:
            self.plugin.delete_port_mac(self.context, fake_port_list)
            self.assertFalse(get_all_ls.called)
            get_ls.assert_called_with(self.context, lg_dict)
            get_mac.assert_called_with(self.context, fake_dict)
            delete_rpc.assert_called_with(
                self.context, 'fake_ovsdb_id', 'fake_uuid',
                ['fake_pairs', 'fake_mac'])

    @mock.patch.object(db,
                       'get_all_logical_switches_by_name')
    @mock.patch.object(db,
                       'get_ucast_mac_remote_by_mac_and_ls',
                       return_value=True)
    @mock.patch.object(db, 'add_pending_ucast_mac_remote')
    @mock.patch.object(db, 'get_logical_switch_by_name')
    def test_delete_port_mac_with_ovsdb_server_down(self,
                                                    get_ls, add_pending_mac,
                                                    get_mac, get_all_ls):
        "Test case to test delete_port_mac when the OVSDB server is down."
        fake_port_list = [{'network_id': 'fake_network_id',
                           'device_owner': 'fake_owner',
                           'mac_address': 'fake_mac',
                           'ovsdb_identifier': 'fake_ovsdb_id'}]
        fake_logical_switch_dict = {'uuid': 'fake_uuid',
                                    'ovsdb_identifier': 'fake_ovsdb_id'}
        lg_dict = {'logical_switch_name': 'fake_network_id',
                   'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_dict = {'mac': 'fake_mac',
                     'logical_switch_uuid': 'fake_uuid',
                     'ovsdb_identifier': 'fake_ovsdb_id'}
        get_all_ls.return_value = fake_logical_switch_dict
        get_ls.return_value = fake_logical_switch_dict
        with mock.patch.object(self.plugin.agent_rpc,
                               'delete_vif_from_gateway',
                               side_effect=RuntimeError) as delete_rpc:
            self.plugin.delete_port_mac(self.context, fake_port_list)
            self.assertFalse(get_all_ls.called)
            get_ls.assert_called_with(self.context, lg_dict)
            get_mac.assert_called_with(self.context, fake_dict)
            delete_rpc.assert_called_with(
                self.context, 'fake_ovsdb_id', 'fake_uuid', ['fake_mac'])
            self.assertTrue(add_pending_mac.called)

    def test_delete_l2_gateway_connection(self):
        self.db_context = ctx.get_admin_context()
        fake_conn_dict = {'l2_gateway_id': 'fake_l2gw_id',
                          'ovsdb_identifier': 'fake_ovsdb_id',
                          'network_id': 'fake_network_id'}
        ovsdb_id = 'fake_ovsdb_id'
        logical_switch = {'uuid': 'fake_uuid',
                          'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_device_dict = {'id': 'fake_device_id',
                            'device_name': 'fake_device_name'}
        fake_device_list = [fake_device_dict]
        fake_identifier_list = ['fake_ovsdb_id']
        fake_ovsdb_list = ['fake_ovsdb_id']
        fake_port_dict = {'network_id': 'fake_network_id',
                          'device_owner': 'fake_owner',
                          'mac_address': 'fake_mac',
                          'ovsdb_identifier': 'fake_ovsdb_id'}
        DELETE = "DELETE"
        with mock.patch.object(self.service_plugin,
                               '_admin_check',
                               return_value=True) as admin_check, \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway_connection',
                                  return_value=fake_conn_dict) as get_con, \
                mock.patch.object(self.plugin,
                                  '_get_identifer_list',
                                  return_value=fake_identifier_list) as get_id_list, \
                mock.patch.object(self.plugin,
                                  '_get_set_of_ovsdb_ids',
                                  return_value=fake_ovsdb_list) as get_ovsdb_id, \
                mock.patch.object(self.service_plugin,
                                  'get_l2gateway_devices_by_gateway_id',
                                  return_value=fake_device_list) as get_devices, \
                mock.patch.object(self.plugin,
                                  '_process_port_list',
                                  return_value=(ovsdb_id, logical_switch,
                                                fake_port_dict)) as port_list, \
                mock.patch.object(self.plugin.agent_rpc,
                                  'update_connection_to_gateway') as update_rpc, \
                mock.patch.object(self.plugin,
                                  '_remove_vm_macs') as remove_vm_mac:
            self.plugin.delete_l2_gateway_connection(self.context,
                                                     fake_conn_dict)
            admin_check.assert_called_with(self.context, 'DELETE')
            get_con.assert_called_with(self.context, fake_conn_dict)
            get_id_list.assert_called_with(self.context, fake_conn_dict)
            get_ovsdb_id.assert_called_with(
                self.context, fake_conn_dict,
                fake_identifier_list)
            get_devices.assert_called_with(self.context, 'fake_l2gw_id')
            port_list.assert_called_with(
                self.context, fake_device_dict,
                fake_conn_dict, DELETE, fake_identifier_list)
            self.assertTrue(update_rpc.called)
            remove_vm_mac.assert_called_with(
                self.context, 'fake_network_id', fake_ovsdb_list)

    def test_create_l2gateway_connection_with_switch_fault_status_down(self):
        self.db_context = ctx.get_admin_context()
        fake_l2gw_conn_dict = {'l2_gateway_connection': {
            'id': 'fake_id', 'network_id': 'fake_network_id',
            'l2_gateway_id': 'fake_l2gw_id'}}
        fake_device = {'devices': [{'device_name': 'fake_device',
                       'interfaces': [{'name': 'fake_interface'}]}]}
        fake_physical_port = {'uuid': 'fake_id',
                              'name': 'fake_name',
                              'physical_switch_id': 'fake_switch1',
                              'port_fault_status': 'UP'}
        fake_physical_switch = {'uuid': 'fake_id',
                                'name': 'fake_name',
                                'tunnel_ip': 'fake_tunnel_ip',
                                'ovsdb_identifier': 'fake_ovsdb_id',
                                'switch_fault_status': 'DOWN'}
        with mock.patch.object(self.service_plugin,
                               '_admin_check',
                               return_value=True), \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway', return_value=fake_device), \
                mock.patch.object(db, 'get_physical_port_by_name_and_ps',
                                  return_value=fake_physical_port), \
                mock.patch.object(db, 'get_physical_switch_by_name',
                                  return_value=fake_physical_switch), \
                mock.patch.object(self.service_plugin,
                                  '_get_network',
                                  return_value=True), \
                mock.patch.object(self.service_plugin,
                                  '_get_l2_gateway',
                                  return_value=True):
            self.assertRaises(l2gw_exc.L2GatewayPhysicalSwitchFaultStatus,
                              self.plugin.create_l2_gateway_connection,
                              self.db_context,
                              fake_l2gw_conn_dict)

    def test_create_l2gateway_connection_with_port_fault_status_down(self):
        self.db_context = ctx.get_admin_context()
        fake_l2gw_conn_dict = {'l2_gateway_connection': {
            'id': 'fake_id', 'network_id': 'fake_network_id',
            'l2_gateway_id': 'fake_l2gw_id'}}
        fake_device = {'devices': [{'device_name': 'fake_device',
                       'interfaces': [{'name': 'fake_interface'}]}]}
        fake_physical_port = {'uuid': 'fake_id',
                              'name': 'fake_name',
                              'physical_switch_id': 'fake_switch1',
                              'port_fault_status': 'DOWN'}
        fake_physical_switch = {'uuid': 'fake_id',
                                'name': 'fake_name',
                                'tunnel_ip': 'fake_tunnel_ip',
                                'ovsdb_identifier': 'fake_ovsdb_id',
                                'switch_fault_status': 'UP'}
        with mock.patch.object(self.service_plugin,
                               '_admin_check',
                               return_value=True), \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway', return_value=fake_device), \
                mock.patch.object(db, 'get_physical_port_by_name_and_ps',
                                  return_value=fake_physical_port), \
                mock.patch.object(db, 'get_physical_switch_by_name',
                                  return_value=fake_physical_switch), \
                mock.patch.object(self.service_plugin,
                                  '_get_network',
                                  return_value=True), \
                mock.patch.object(self.service_plugin,
                                  '_get_l2_gateway',
                                  return_value=True):
            self.assertRaises(l2gw_exc.L2GatewayPhysicalPortFaultStatus,
                              self.plugin.create_l2_gateway_connection,
                              self.db_context, fake_l2gw_conn_dict)

    @mock.patch.object(db, 'get_physical_port_by_name_and_ps')
    @mock.patch.object(db, 'get_physical_switch_by_name')
    def test_check_port_fault_status_and_switch_fault_status(
            self, phy_switch, phy_port):
        fake_device = {'devices': [{'device_name': 'fake_device',
                       'interfaces': [{'name': 'fake_interface'}]}]}
        self.db_context = ctx.get_admin_context()
        fake_device = {'devices': [{'device_name': 'fake_device',
                       'interfaces': [{'name': 'fake_interface'}]}]}
        fake_physical_port = {'uuid': 'fake_id',
                              'name': 'fake_name',
                              'physical_switch_id': 'fake_switch1',
                              'port_fault_status': None}
        fake_physical_switch = {'uuid': 'fake_id',
                                'name': 'fake_name',
                                'tunnel_ip': 'fake_tunnel_ip',
                                'ovsdb_identifier': 'fake_ovsdb_id',
                                'switch_fault_status': None}
        phy_port.return_value = fake_physical_port
        phy_switch.return_value = fake_physical_switch
        with mock.patch.object(self.service_plugin,
                               'get_l2_gateway',
                               return_value=fake_device) as get_l2gw:
            self.plugin._check_port_fault_status_and_switch_fault_status(
                mock.Mock(), mock.Mock())
            self.assertTrue(get_l2gw.called)
            self.assertTrue(phy_port.called)
            self.assertTrue(phy_switch.called)

    def test_create_l2_gateway_connection(self):
        self.db_context = ctx.get_admin_context()
        fake_l2gw_conn_dict = {'l2_gateway_connection': {
            'id': 'fake_id', 'network_id': 'fake_network_id',
            'l2_gateway_id': 'fake_l2gw_id'}}
        fake_port = {'device_owner': 'fake_owner',
                     'network_id': 'fake_network_id',
                     'mac_address': 'fake_mac',
                     'ip_address': 'fake_ip2',
                     'allowed_address_pairs': [{'ip_address': 'fake_ip2',
                                                'mac_address': 'fake_mac2'}],
                     }
        fake_port_list = [fake_port]
        fake_conn_dict = fake_l2gw_conn_dict.get('l2_gateway_connection')
        ovsdb_id = 'fake_ovsdb_id'
        logical_switch = {'uuid': 'fake_id'}
        fake_device_dict = {'device_name': 'fake_device_name'}
        fake_device_list = [fake_device_dict]
        fake_ls_dict = {'logical_switch_name': 'fake_network_id',
                        'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_pl_dict = {'uuid': 'fake_uuid', 'dst_ip': 'fake_ip1',
                        'ovsdb_identifier': 'fake_ovsdb_id',
                        'macs': [fake_port]}
        fake_pl_list = [fake_pl_dict]
        with mock.patch.object(self.service_plugin,
                               '_admin_check',
                               return_value=True) as admin_check, \
            mock.patch.object(self.plugin,
                              '_validate_connection'), \
            mock.patch.object(self.service_plugin,
                              'get_l2gateway_devices_by_gateway_id',
                              return_value=fake_device_list) as get_devices, \
            mock.patch.object(self.plugin,
                              '_process_port_list',
                              return_value=(ovsdb_id,
                                            logical_switch,
                                            fake_port)) as port_list, \
            mock.patch.object(self.plugin,
                              '_get_logical_switch_dict',
                              return_value=fake_ls_dict) as get_ls, \
            mock.patch.object(self.plugin,
                              '_get_port_details',
                              return_value=fake_port_list) as get_port, \
            mock.patch.object(self.plugin,
                              '_get_ip_details',
                              return_value=('fake_ip1', 'fake_ip2')) as get_ip, \
            mock.patch.object(self.plugin, '_get_dict', return_value=mock.ANY) as get_dict, \
            mock.patch.object(db, 'get_ucast_mac_remote_by_mac_and_ls') as get_ucast_mac, \
            mock.patch.object(self.plugin,
                              '_get_locator_list',
                              return_value=fake_pl_list) as get_pl, \
            mock.patch.object(self.plugin.agent_rpc,
                              'update_connection_to_gateway') as update_rpc:
            self.plugin.create_l2_gateway_connection(self.db_context,
                                                     fake_l2gw_conn_dict)
            admin_check.assert_called_with(self.db_context, 'CREATE')
            get_devices.assert_called_with(self.db_context, 'fake_l2gw_id')
            port_list.assert_called_with(
                self.db_context, fake_device_dict,
                fake_conn_dict, "CREATE")
            get_ls.assert_called_with(self.db_context,
                                      logical_switch,
                                      fake_conn_dict)
            get_port.assert_called_with(self.db_context, 'fake_network_id')
            self.assertTrue(get_ip.called)
            self.assertTrue(get_dict.called)
            self.assertEqual(get_ucast_mac.call_count, 2)
            self.assertTrue(get_pl.called)
            self.assertTrue(update_rpc.called)

    @mock.patch.object(db, 'get_physical_switch_by_name')
    def test_create_l2gateway_connection_with_invalid_device(self,
                                                             phy_switch):
        self.db_context = ctx.get_admin_context()
        fake_l2gw_conn_dict = {'l2_gateway_connection': {
            'id': 'fake_id', 'network_id': 'fake_network_id',
            'l2_gateway_id': 'fake_l2gw_id'}}
        fake_device = {'devices': [{'device_name': 'fake_device',
                       'interfaces': [{'name': 'fake_interface'}]}]}
        fake_physical_switch = None
        phy_switch.return_value = fake_physical_switch
        with mock.patch.object(self.service_plugin,
                               '_admin_check',
                               return_value=True), \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway',
                                  return_value=fake_device), \
                mock.patch.object(self.service_plugin,
                                  '_get_network',
                                  return_value=True), \
                mock.patch.object(self.service_plugin,
                                  '_get_l2_gateway',
                                  return_value=True):
            self.assertRaises(l2gw_exc.L2GatewayDeviceNotFound,
                              self.plugin.create_l2_gateway_connection,
                              self.db_context, fake_l2gw_conn_dict)

    @mock.patch.object(db, 'get_physical_switch_by_name')
    @mock.patch.object(db, 'get_physical_port_by_name_and_ps')
    def test_create_l2gateway_connection_with_invalid_interface(
            self, phy_port, phy_switch):
        self.db_context = ctx.get_admin_context()
        fake_l2gw_conn_dict = {'l2_gateway_connection': {
            'id': 'fake_id', 'network_id': 'fake_network_id',
            'l2_gateway_id': 'fake_l2gw_id'}}
        fake_device = {'devices': [{'device_name': 'fake_device',
                       'interfaces': [{'name': 'fake_interface'}]}]}
        fake_physical_port = None
        fake_physical_switch = {'uuid': 'fake_id',
                                'name': 'fake_device',
                                'tunnel_ip': 'fake_tunnel_ip',
                                'ovsdb_identifier': 'fake_ovsdb_id',
                                'switch_fault_status': None}
        phy_switch.return_value = fake_physical_switch
        phy_port.return_value = fake_physical_port
        with mock.patch.object(self.service_plugin,
                               '_admin_check',
                               return_value=True), \
                mock.patch.object(self.service_plugin,
                                  'get_l2_gateway',
                                  return_value=fake_device), \
                mock.patch.object(self.service_plugin,
                                  '_get_network',
                                  return_value=True), \
                mock.patch.object(self.service_plugin,
                                  '_get_l2_gateway',
                                  return_value=True):
            self.assertRaises(l2gw_exc.L2GatewayInterfaceNotFound,
                              self.plugin.create_l2_gateway_connection,
                              self.db_context, fake_l2gw_conn_dict)
