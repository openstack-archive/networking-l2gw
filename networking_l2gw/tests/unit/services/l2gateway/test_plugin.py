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
from neutron.common import rpc as n_rpc
from neutron import context as ctx
from neutron.db import agents_db
from neutron.tests import base

from networking_l2gw.db.l2gateway import db_query
from networking_l2gw.db.l2gateway import l2gateway_db
from networking_l2gw.db.l2gateway.ovsdb import lib as db
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import l2gw_validators
from networking_l2gw.services.l2gateway.common import ovsdb_schema
from networking_l2gw.services.l2gateway import exceptions as l2gw_exc
from networking_l2gw.services.l2gateway.ovsdb import data
from networking_l2gw.services.l2gateway import plugin as l2gw_plugin

import oslo_messaging as messaging
from oslo_utils import importutils


class TestL2GatewayAgentApi(base.BaseTestCase):

    def setUp(self):
        self.client_mock_p = mock.patch.object(n_rpc, 'get_client')
        self.client_mock = self.client_mock_p.start()
        self.context = mock.ANY
        self.topic = 'foo_topic'
        self.host = 'foo_host'

        self.plugin_rpc = l2gw_plugin.L2gatewayAgentApi(
            self.topic, self.host)
        super(TestL2GatewayAgentApi, self).setUp()

    def test_add_vif_to_gateway(self):
        cctxt = mock.Mock()
        fake_ovsdb_identifier = 'fake_ovsdb_id'
        fake_logical_switch = {}
        fake_physical_locator = {}
        fake_mac_remote = {}
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.add_vif_to_gateway(
            self.context, fake_ovsdb_identifier, fake_logical_switch,
            fake_physical_locator, fake_mac_remote)
        cctxt.call.assert_called_with(
            self.context, 'add_vif_to_gateway',
            ovsdb_identifier=fake_ovsdb_identifier,
            logical_switch_dict=fake_logical_switch,
            locator_dict=fake_physical_locator,
            mac_dict=fake_mac_remote)

    def test_update_vif_to_gateway(self):
        cctxt = mock.Mock()
        fake_ovsdb_identifier = 'fake_ovsdb_id'
        fake_physical_locator = {}
        fake_mac_remote = {}
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.update_vif_to_gateway(
            self.context, fake_ovsdb_identifier,
            fake_physical_locator, fake_mac_remote)
        cctxt.call.assert_called_with(
            self.context, 'update_vif_to_gateway',
            ovsdb_identifier=fake_ovsdb_identifier,
            locator_dict=fake_physical_locator,
            mac_dict=fake_mac_remote)

    def test_delete_vif_from_gateway(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.delete_vif_from_gateway(self.context,
                                                mock.ANY,
                                                mock.ANY,
                                                mock.ANY)
        cctxt.call.assert_called_with(
            self.context, 'delete_vif_from_gateway',
            ovsdb_identifier=mock.ANY, logical_switch_uuid=mock.ANY,
            mac=mock.ANY)

    def test_delete_network(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.delete_network(self.context, mock.ANY, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'delete_network', ovsdb_identifier=mock.ANY,
            logical_switch_uuid=mock.ANY)

    def test_update_connection_to_gateway(self):
        cctxt = mock.Mock()
        fake_ovsdb_identifier = 'fake_ovsdb_id'
        fake_logical_switch = {}
        fake_physical_locator_list = []
        fake_mac_dicts = [{}]
        fake_port_dicts = [{}]
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.update_connection_to_gateway(
            self.context, fake_ovsdb_identifier, fake_logical_switch,
            fake_physical_locator_list, fake_mac_dicts, fake_port_dicts)
        cctxt.call.assert_called_with(
            self.context, 'update_connection_to_gateway',
            ovsdb_identifier=fake_ovsdb_identifier,
            logical_switch_dict=fake_logical_switch,
            locator_dicts=fake_physical_locator_list,
            mac_dicts=fake_mac_dicts,
            port_dicts=fake_port_dicts)

    def test_update_connection_to_gateway_with_error(self):
        cctxt = mock.Mock()
        fake_ovsdb_identifier = 'fake_ovsdb_id'
        fake_logical_switch = {}
        fake_physical_locator_list = []
        fake_mac_dicts = [{}]
        fake_port_dicts = [{}]
        self.plugin_rpc.client.prepare.return_value = cctxt

        # Test with a timeout exception
        with mock.patch.object(cctxt,
                               'call',
                               side_effect=messaging.MessagingTimeout):
            self.assertRaises(
                l2gw_exc.OVSDBError,
                self.plugin_rpc.update_connection_to_gateway,
                self.context, fake_ovsdb_identifier, fake_logical_switch,
                fake_physical_locator_list, fake_mac_dicts, fake_port_dicts)

        # Test with a remote exception
        with mock.patch.object(cctxt,
                               'call',
                               side_effect=Exception):
            self.assertRaises(
                l2gw_exc.OVSDBError,
                self.plugin_rpc.update_connection_to_gateway,
                self.context, fake_ovsdb_identifier, fake_logical_switch,
                fake_physical_locator_list, fake_mac_dicts, fake_port_dicts)


class TestL2GatewayPlugin(base.BaseTestCase):

    def setUp(self):
        super(TestL2GatewayPlugin, self).setUp()
        self.plugin = l2gw_plugin.L2GatewayPlugin()
        self.ovsdb_identifier = 'fake_ovsdb_id'
        self.ovsdb_data = data.OVSDBData(self.ovsdb_identifier)
        self.context = mock.ANY

    def test_l2gatewayplugin_init(self):
        with contextlib.nested(
            mock.patch.object(config,
                              'register_l2gw_opts_helper'),
            mock.patch.object(importutils,
                              'import_object'),
            mock.patch.object(agents_db,
                              'AgentExtRpcCallback'),
            mock.patch.object(n_rpc,
                              'create_connection'),
            mock.patch.object(n_rpc.Connection,
                              'create_consumer'),
            mock.patch.object(n_rpc.Connection,
                              'consume_in_threads'),
            mock.patch.object(ctx,
                              'get_admin_context'),
            mock.patch.object(l2gw_plugin,
                              'L2gatewayAgentApi'),
            mock.patch.object(l2gw_plugin.LOG,
                              'debug'),
            mock.patch.object(l2gw_plugin.L2GatewayPlugin,
                              'start_l2gateway_agent_scheduler'),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '__init__'),
            mock.patch.object(l2gateway_db,
                              'subscribe')
        ) as (reg_l2gw_opts,
              import_obj,
              agent_calback,
              create_conn,
              create_consum,
              consume_in_thread,
              get_admin_ctx,
              l2gw_api,
              debug,
              scheduler,
              super_init,
              subscribe):
            l2gw_plugin.L2GatewayPlugin()
            self.assertTrue(reg_l2gw_opts.called)
            self.assertTrue(import_obj.called)
            self.assertTrue(agent_calback.called)
            self.assertTrue(create_conn.called)
            self.assertTrue(l2gw_api.called)
            self.assertTrue(debug.called)
            self.assertTrue(scheduler.called)
            self.assertTrue(super_init.called)
            self.assertTrue(subscribe.called)

    def test_validate_connection(self):
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100L}
        fake_net_seg_list = [{'id': 'fake_id',
                              'network_type': 'fake_vxlan',
                              'physical_network': 'fake_phy_net',
                              'segmentation_id': 100L}]
        fake_l2_gw = {'id': 'fake_l2gw_id'}
        fake_tenant_id = 'fake_tenant_id'
        fake_filters = {'network_id': ['fake_network_id'],
                        'tenant_id': [fake_tenant_id],
                        'l2_gateway_id': ['fake_l2gw_id']}
        with contextlib.nested(
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_is_vlan_configured_on_any_interface_for_l2gw',
                              return_value=False),
            mock.patch.object(l2gw_validators,
                              'validate_network_mapping_list',
                              return_value='fake_network_id'),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_get_network_segments',
                              return_value=fake_net_seg_list),
            mock.patch.object(db_query.L2GatewayCommonDbMixin,
                              '_get_network',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_get_l2_gateway',
                              return_value=fake_l2_gw),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_retrieve_gateway_connections',
                              return_value=False),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_get_tenant_id_for_create',
                              return_value=fake_tenant_id),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2_gateway_connections',
                              return_value=False),
            mock.patch.object(
                self.plugin,
                '_check_port_fault_status_and_switch_fault_status')
            ) as (is_vlan, val_ntwk, get_net_seg, get_network, get_l2gw,
                  ret_gw_conn, get_ten_id, get_l2_gw_conn, check_pf_sf):
            self.plugin._validate_connection(self.context, fake_connection)
            is_vlan.assert_called_with(self.context, 'fake_l2gw_id')
            val_ntwk.assert_called_with(fake_connection, False)
            get_net_seg.assert_called_with(self.context,
                                           'fake_network_id')
            get_network.assert_called_with(self.context, 'fake_network_id')
            get_l2gw.assert_called_with(self.context, 'fake_l2gw_id')
            check_pf_sf.assert_called_with(self.context, 'fake_l2gw_id')
            ret_gw_conn.assert_called_with(self.context,
                                           'fake_l2gw_id',
                                           fake_connection)
            get_ten_id.assert_called_with(self.context, fake_l2_gw)
            get_l2_gw_conn.assert_called_with(self.context,
                                              filters=fake_filters)

    def test_process_port_list(self):
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100L}
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
        with contextlib.nested(
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2gateway_interfaces_by_device_id',
                              return_value=fake_interface_list),
            mock.patch.object(db,
                              'get_physical_switch_by_name',
                              return_value=fake_physical_switch),
            mock.patch.object(db,
                              'get_logical_switch_by_name',
                              return_value=fake_logical_switch),
            mock.patch.object(db,
                              'get_physical_port_by_name_and_ps',
                              return_value=fake_physical_port),
            mock.patch.object(self.plugin,
                              '_generate_port_list')) as (
                get_intf, get_ps, get_ls, get_pp, gen_port_list):
            self.plugin._process_port_list(self.context, fake_device,
                                           fake_connection,
                                           fake_method)
            get_intf.assert_called_with(self.context, 'fake_device_id')
            get_ps.assert_called_with(self.context, 'fake_device_name')
            get_pp.assert_called_with(self.context, fake_pp_dict)
            get_ls.assert_called_with(self.context, fake_pp_dict)
            gen_port_list.assert_called_with(
                self.context, fake_method, 100L, fake_interface,
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
        fake_vlan_binding = {'vlan': 100L,
                             'logical_switch_uuid': 'fake_uuid'}
        fake_vlan_binding_list = [fake_vlan_binding]
        with mock.patch.object(
            db, 'get_all_vlan_bindings_by_physical_port',
            return_value=fake_vlan_binding_list) as (
                get_vlan):
            self.plugin._generate_port_list(
                self.context, fake_method, 101L, fake_interface,
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
        fake_vlan_binding = {'vlan': 100L,
                             'logical_switch_uuid': 'fake_uuid'}
        fake_vlan_binding_list = [fake_vlan_binding]
        with mock.patch.object(
            db, 'get_all_vlan_bindings_by_physical_port',
            return_value=fake_vlan_binding_list) as (
                get_vlan):
            self.assertRaises(l2gw_exc.L2GatewayDuplicateSegmentationID,
                              self.plugin._generate_port_list,
                              self.context, fake_method, 100L,
                              fake_interface, fake_pp_dict, 'fake_uuid')
            get_vlan.assert_called_with(self.context, fake_pp_dict)

    def test_generate_port_list_for_delete(self):
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 200L}
        fake_method = 'DELETE'
        fake_interface = {'interface_name': 'fake_interface_name'}
        fake_pp_dict = {'interface_name': 'fake_interface_name',
                        'ovsdb_identifier': 'fake_ovsdb_id',
                        'physical_switch_id': 'fake_uuid',
                        'logical_switch_name': 'fake_network_id',
                        'uuid': 'fake_uuid'}
        fake_vlan_binding = {'vlan': 100L,
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
                self.context, fake_method, 100L, fake_interface,
                fake_pp_dict, 'fake_uuid1', fake_connection)
            get_vlan.assert_called_with(self.context, fake_pp_dict)
            self.assertEqual(port, phys_port_dict)

    def test_get_ip_details(self):
        fake_port = {'binding:host_id': 'fake_host',
                     'fixed_ips': [{'ip_address': 'fake_ip'}]}
        fake_agent = [{'configurations': {'tunneling_ip': 'fake_tun_ip'}}]
        with mock.patch.object(self.plugin,
                               '_get_agent_details',
                               return_value=fake_agent) as get_agent:
            (ret_dst_ip, ret_ip_add) = self.plugin._get_ip_details(
                self.context, fake_port)
            get_agent.assert_called_with(self.context, 'fake_host')
            self.assertEqual(ret_dst_ip, 'fake_tun_ip')
            self.assertEqual(ret_ip_add, 'fake_ip')

    def test_get_network_details(self):
        fake_network = {'id': 'fake_network_id',
                        'name': 'fake_network_name',
                        'provider:segmentation_id': 'fake_key'}
        core_plugin = mock.PropertyMock()
        type(self.plugin)._core_plugin = core_plugin
        (self.plugin._core_plugin.get_network.return_value) = fake_network

    def test_get_port_details(self):
        fake_port = {'binding:host_id': 'fake_host',
                     'fixed_ips': [{'ip_address': 'fake_ip'}],
                     'mac_address': 'fake_mac_add'}
        fake_port_list = [fake_port]
        core_plugin = mock.PropertyMock()
        type(self.plugin)._core_plugin = core_plugin
        (self.plugin._core_plugin.get_ports.return_value) = fake_port_list

    def test_get_agent_details(self):
        fake_agent = [{'configurations': {'tunneling_ip': 'fake_tun_ip'}}]
        core_plugin = mock.PropertyMock()
        type(self.plugin)._core_plugin = core_plugin
        (self.plugin._core_plugin.get_agents.return_value) = fake_agent

    def test_get_logical_switch_dict(self):
        fake_logical_switch = {'uuid': 'fake_uuid',
                               'name': 'fake_network_id'}
        fake_ls = None
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100L}
        fake_network = {'id': 'fake_network_id',
                        'name': 'fake_network_name',
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
            self.assertEqual(ret_ls_dict, fake_ls_dict)
            self.assertEqual(ret_ls_dict_without_ls, fake_ls_dict_without_ls)

    def test_get_locator_list(self):
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
        with contextlib.nested(
            mock.patch.object(db,
                              'get_physical_locator_by_dst_ip',
                              return_value=fake_pl),
            mock.patch.object(self.plugin,
                              '_get_physical_locator_dict',
                              return_value=fake_locator_dict)) as (
                get_pl_by_dst_ip, get_pl_dict):
            ret_pl_list = self.plugin._get_locator_list(
                self.context, fake_dst_ip, fake_ovsdb_id,
                fake_mac_list, fake_locator_list)
            get_pl_by_dst_ip.assert_called_with(self.context,
                                                fake_locator_dict)
            get_pl_dict.assert_called_with(fake_dst_ip,
                                           'fake_uuid', fake_mac_list)
            self.assertEqual(ret_pl_list, fale_pl_list)

    def test_get_identifer_list(self):
        fake_connection = {'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100L}
        fake_device = {'id': 'fake_device_id',
                       'device_name': 'fake_device_name'}
        fake_device_list = [fake_device]
        fake_physical_switch = {'uuid': 'fake_uuid',
                                'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_identifier_set = set(['fake_ovsdb_id'])
        with contextlib.nested(
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2gateway_devices_by_gateway_id',
                              return_value=fake_device_list),
            mock.patch.object(db,
                              'get_physical_switch_by_name',
                              return_value=fake_physical_switch)) as (
                get_l2_gw, get_ps):
            ret_value = self.plugin._get_identifer_list(self.context,
                                                        fake_connection)
            get_l2_gw.assert_called_with(self.context, 'fake_l2gw_id')
            get_ps.assert_called_with(self.context, 'fake_device_name')
            self.assertEqual(ret_value, fake_identifier_set)

    def test_get_set_of_ovsdb_ids(self):
        fake_connection = {'id': 'fake_id',
                           'l2_gateway_id': 'fake_l2gw_id',
                           'network_id': 'fake_network_id',
                           'segmentation_id': 100L}
        fake_gw_conn_ovsdb_set = set(['fake_ovsdb_id'])
        fake_connection_list = [fake_connection]
        fake_filters = {'network_id': ['fake_network_id']}
        with mock.patch.object(l2gateway_db.L2GatewayMixin,
                               'get_l2_gateway_connections',
                               return_value=fake_connection_list) as get_conn:
            ret_value = self.plugin._get_set_of_ovsdb_ids(
                self.context, fake_connection,
                fake_gw_conn_ovsdb_set)
            get_conn.assert_called_with(self.context, filters=fake_filters)
            self.assertEqual(ret_value, fake_gw_conn_ovsdb_set)

    def test_remove_vm_macs(self):
        fake_network_id = 'fake_network_id'
        fake_ovsdb_id_set = set(['fake_ovsdb_id'])
        fake_port = {'binding:host_id': 'fake_host',
                     'fixed_ips': [{'ip_address': 'fake_ip'}],
                     'mac_address': 'fake_mac_add'}
        fake_port_list = [fake_port]
        with contextlib.nested(
            mock.patch.object(self.plugin,
                              '_get_port_details',
                              return_value=fake_port_list),
            mock.patch.object(self.plugin,
                              'delete_port_mac')) as (
                get_port, delete_mac):
            self.plugin._remove_vm_macs(self.context,
                                        fake_network_id,
                                        fake_ovsdb_id_set)
            get_port.assert_called_with(self.context, fake_network_id)
            delete_mac.assert_called_with(self.context,
                                          fake_port_list)

    def test_add_port_mac(self):
        fake_ip1 = "fake_ip1"
        fake_ip2 = "fake_ip2"
        fake_network_dict = {'provider:segmentation_id': 100L,
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
        type(self.plugin)._core_plugin = core_plugin
        (self.plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        ovsdb_identifier = 'fake_ovsdb_id'
        with contextlib.nested(
            mock.patch.object(self.plugin,
                              '_get_ip_details',
                              return_value=(fake_ip1,
                                            fake_ip2)),
            mock.patch.object(self.plugin,
                              '_get_network_details',
                              return_value=fake_network_dict),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2_gateway_connections',
                              return_value=fake_conn_list),
            mock.patch.object(self.plugin,
                              '_form_physical_locator_schema',
                              return_value=fake_locator_dict),
            mock.patch.object(ovsdb_schema,
                              'UcastMacsRemote'),
            mock.patch.object(self.plugin,
                              '_get_dict',
                              return_value=fake_dict),
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=False),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'add_vif_to_gateway'),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'update_vif_to_gateway'),
            mock.patch.object(db,
                              'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_list)) as (
                get_ip, get_network, get_l2gw_conn,
                get_pl, mock_ucmr, get_dict, get_ucast_mac, add_rpc,
                update_rpc, get_all_ls):
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

    def test_delete_port_mac_for_multiple_vlan_bindings(self):
        fake_port_list = [{'network_id': 'fake_network_id',
                           'device_owner': 'fake_owner',
                           'mac_address': 'fake_mac',
                           'ovsdb_identifier': 'fake_ovsdb_id'}]
        fake_logical_switch_dict = {'uuid': 'fake_uuid',
                                    'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_logical_switch_list = [fake_logical_switch_dict]
        lg_dict = {'logical_switch_name': 'fake_network_id',
                   'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_rec_dict = {'logical_switch_id': 'fake_uuid',
                         'ovsdb_identifier': 'fake_ovsdb_id'}
        with contextlib.nested(
            mock.patch.object(db,
                              'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_list),
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=True),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'delete_vif_from_gateway'),
            mock.patch.object(db,
                              'get_logical_switch_by_name',
                              return_value=fake_logical_switch_dict),
            mock.patch.object(db,
                              'get_all_vlan_bindings_by_logical_switch',
                              return_value=[1, 2]),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2_gateway_connections',
                              return_value=[1, 2])) as (
                get_all_ls, get_mac, delete_rpc, get_ls, get_vlan_binding,
                get_l2gw_conn):
            self.plugin.delete_port_mac(self.context, fake_port_list)
            self.assertFalse(get_all_ls.called)
            get_ls.assert_called_with(self.context, lg_dict)
            get_vlan_binding.assert_called_with(self.context, fake_rec_dict)
            self.assertFalse(get_mac.called)
            self.assertFalse(delete_rpc.called)

    def test_add_port_mac_with_ovsdb_server_down(self):
        "Test case to test add_port_mac when the OVSDB server is down."
        fake_ip1 = "fake_ip1"
        fake_ip2 = "fake_ip2"
        fake_network_dict = {'provider:segmentation_id': 100L,
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
        type(self.plugin)._core_plugin = core_plugin
        (self.plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        ovsdb_identifier = 'fake_ovsdb_id'
        with contextlib.nested(
            mock.patch.object(self.plugin,
                              '_get_ip_details',
                              return_value=(fake_ip1,
                                            fake_ip2)),
            mock.patch.object(self.plugin,
                              '_get_network_details',
                              return_value=fake_network_dict),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2_gateway_connections',
                              return_value=fake_conn_list),
            mock.patch.object(self.plugin,
                              '_form_physical_locator_schema',
                              return_value=fake_locator_dict),
            mock.patch.object(ovsdb_schema,
                              'UcastMacsRemote'),
            mock.patch.object(self.plugin,
                              '_get_dict',
                              return_value=fake_dict),
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=False),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'add_vif_to_gateway',
                              side_effect=RuntimeError),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'update_vif_to_gateway'),
            mock.patch.object(db, 'add_pending_ucast_mac_remote'),
            mock.patch.object(db, 'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_list)
        ) as (get_ip, get_network, get_l2gw_conn,
              get_pl, mock_ucmr, get_dict, get_ucast_mac, add_rpc,
              update_rpc, add_pending_mac, get_all_ls):
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
            self.assertTrue(add_pending_mac.called)

    def test_add_port_mac_vm_migrate(self):
        fake_ip1 = "fake_ip1"
        fake_ip2 = "fake_ip2"
        fake_network_dict = {'provider:segmentation_id': 100L,
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
        type(self.plugin)._core_plugin = core_plugin
        (self.plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        ovsdb_identifier = 'fake_ovsdb_id'
        with contextlib.nested(
            mock.patch.object(self.plugin,
                              '_get_ip_details',
                              return_value=(fake_ip1,
                                            fake_ip2)),
            mock.patch.object(self.plugin,
                              '_get_network_details',
                              return_value=fake_network_dict),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2_gateway_connections',
                              return_value=fake_conn_list),
            mock.patch.object(self.plugin,
                              '_form_physical_locator_schema',
                              return_value=fake_locator_dict),
            mock.patch.object(self.plugin,
                              '_get_dict',
                              return_value=fake_dict),
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=fake_mac_dict),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'add_vif_to_gateway'),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'update_vif_to_gateway'),
            mock.patch.object(db,
                              'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_list)) as (
                get_ip, get_network, get_l2gw_conn,
                get_pl, get_dict, get_ucast_mac, add_rpc, update_rpc,
                get_all_ls):
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
        fake_network_dict = {'provider:segmentation_id': 100L,
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
        type(self.plugin)._core_plugin = core_plugin
        (self.plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        with contextlib.nested(
            mock.patch.object(self.plugin,
                              '_get_ip_details',
                              return_value=(fake_ip1,
                                            fake_ip2)),
            mock.patch.object(self.plugin,
                              '_get_network_details',
                              return_value=fake_network_dict),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2_gateway_connections',
                              return_value=fake_conn_list),
            mock.patch.object(self.plugin,
                              '_form_physical_locator_schema',
                              return_value=fake_locator_dict),
            mock.patch.object(self.plugin,
                              '_get_dict',
                              return_value=fake_dict),
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=fake_mac_dict),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'add_vif_to_gateway'),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'update_vif_to_gateway',
                              side_effect=RuntimeError),
            mock.patch.object(db, 'add_pending_ucast_mac_remote'),
            mock.patch.object(db, 'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_list)
        ) as (get_ip, get_network, get_l2gw_conn,
              get_pl, get_dict, get_ucast_mac, add_rpc, update_rpc,
              add_pending_mac, get_all_ls):
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
        fake_network_dict = {'provider:segmentation_id': 100L,
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
        type(self.plugin)._core_plugin = core_plugin
        (self.plugin._core_plugin.get_port.
         return_value) = {'device_owner': 'fake_owner',
                          'network_id': 'fake_network_id',
                          'mac_address': 'fake_mac'}
        with contextlib.nested(
            mock.patch.object(self.plugin,
                              '_get_ip_details',
                              return_value=(fake_ip1,
                                            fake_ip2)),
            mock.patch.object(self.plugin,
                              '_get_network_details',
                              return_value=fake_network_dict),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2_gateway_connections',
                              return_value=fake_conn_list),
            mock.patch.object(self.plugin,
                              '_form_physical_locator_schema',
                              return_value=fake_locator_dict),
            mock.patch.object(self.plugin,
                              '_get_dict',
                              return_value=fake_dict),
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=fake_mac_dict),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'add_vif_to_gateway'),
            mock.patch.object(data.L2GatewayOVSDBCallbacks,
                              'get_ovsdbdata_object'),
            mock.patch.object(db,
                              'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_list)) as (
                get_ip, get_network, get_l2gw_conn,
                get_pl, get_dict, get_ucast_mac, add_rpc,
                get_ovsdbdata_obj, get_all_ls):
            self.plugin.add_port_mac(self.context, fake_dict)
            get_network.assert_called_with(self.context, 'fake_network_id')
            get_l2gw_conn.assert_called_with(
                self.context, filters={'network_id': ['fake_network_id']})
            get_pl.assert_called_with(self.context, fake_pl_dict)
            get_ucast_mac.assert_called_with(self.context, fake_dict)
            self.assertFalse(add_rpc.called)
            self.assertTrue(get_ovsdbdata_obj.called)

    def test_delete_port_mac_with_list(self):
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
        fake_rec_dict = {'logical_switch_id': 'fake_uuid',
                         'ovsdb_identifier': 'fake_ovsdb_id'}
        with contextlib.nested(
            mock.patch.object(db,
                              'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_list),
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=True),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'delete_vif_from_gateway'),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2_gateway_connections',
                              return_value=True),
            mock.patch.object(db,
                              'get_all_vlan_bindings_by_logical_switch',
                              return_value=[1])) as (
                get_ls, get_mac, delete_rpc, get_l2gw_conn, get_vlan_binding):
            self.plugin.delete_port_mac(self.context, fake_port_dict)
            get_ls.assert_called_with(self.context, network_id)
            get_mac.assert_called_with(self.context, fake_dict)
            get_vlan_binding.assert_called_with(self.context, fake_rec_dict)
            delete_rpc.assert_called_with(
                self.context, 'fake_ovsdb_id', 'fake_uuid', ['fake_mac'])

    def test_delete_port_mac(self):
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
        fake_rec_dict = {'logical_switch_id': 'fake_uuid',
                         'ovsdb_identifier': 'fake_ovsdb_id'}
        with contextlib.nested(
            mock.patch.object(db,
                              'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_dict),
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=True),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'delete_vif_from_gateway'),
            mock.patch.object(db,
                              'get_all_vlan_bindings_by_logical_switch',
                              return_value=[1]),
            mock.patch.object(db,
                              'get_logical_switch_by_name',
                              return_value=fake_logical_switch_dict)) as (
                get_all_ls, get_mac, delete_rpc, get_vlan_binding, get_ls):
            self.plugin.delete_port_mac(self.context, fake_port_list)
            self.assertFalse(get_all_ls.called)
            get_ls.assert_called_with(self.context, lg_dict)
            get_mac.assert_called_with(self.context, fake_dict)
            get_vlan_binding.assert_called_with(self.context, fake_rec_dict)
            delete_rpc.assert_called_with(
                self.context, 'fake_ovsdb_id', 'fake_uuid', ['fake_mac'])

    def test_delete_port_mac_with_ovsdb_server_down(self):
        "Test case to test delete_port_mac when the OVSDB server is down."
        fake_port_list = [{'network_id': 'fake_network_id',
                           'device_owner': 'fake_owner',
                           'mac_address': 'fake_mac',
                           'ovsdb_identifier': 'fake_ovsdb_id'}]
        fake_logical_switch_dict = {'uuid': 'fake_uuid',
                                    'ovsdb_identifieir': 'fake_ovsdb_id'}
        lg_dict = {'logical_switch_name': 'fake_network_id',
                   'ovsdb_identifier': 'fake_ovsdb_id'}
        fake_dict = {'mac': 'fake_mac',
                     'logical_switch_uuid': 'fake_uuid',
                     'ovsdb_identifier': 'fake_ovsdb_id'}
        with contextlib.nested(
            mock.patch.object(db,
                              'get_all_logical_switches_by_name',
                              return_value=fake_logical_switch_dict),
            mock.patch.object(db,
                              'get_ucast_mac_remote_by_mac_and_ls',
                              return_value=True),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'delete_vif_from_gateway',
                              side_effect=RuntimeError),
            mock.patch.object(db, 'add_pending_ucast_mac_remote'),
            mock.patch.object(db, 'get_logical_switch_by_name',
                              return_value=fake_logical_switch_dict),
            mock.patch.object(db,
                              'get_all_vlan_bindings_by_logical_switch')
        ) as (get_all_ls, get_mac, delete_rpc, add_pending_mac, get_ls,
              get_vlan_binding):
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
                          'ovsdb_identifier': 'fake_ovsdb_id'}
        ovsdb_id = mock.ANY
        logical_switch = mock.ANY
        fake_device_dict = {'id': 'fake_device_id',
                            'device_name': 'fake_device_name'}
        fake_device_list = [fake_device_dict]
        fake_identifier_list = ['fake_ovsdb_id']
        fake_ovsdb_list = ['fake_ovsdb_id']
        fake_port_dict = {}
        DELETE = "DELETE"
        with contextlib.nested(
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_admin_check',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2_gateway_connection',
                              return_value=fake_conn_dict),
            mock.patch.object(self.plugin,
                              '_get_identifer_list',
                              return_value=fake_identifier_list),
            mock.patch.object(self.plugin,
                              '_get_set_of_ovsdb_ids',
                              return_value=fake_ovsdb_list),
            mock.patch.object(self.plugin, '_remove_vm_macs'),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2gateway_devices_by_gateway_id',
                              return_value=fake_device_list),
            mock.patch.object(self.plugin,
                              '_process_port_list',
                              return_value=(ovsdb_id, logical_switch,
                                            fake_port_dict)),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'update_connection_to_gateway'),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'delete_l2_gateway_connection'),
            mock.patch.object(db,
                              'get_all_vlan_bindings_by_logical_switch',
                              return_value=1)
            ) as (admin_check, get_con, get_id_list, get_ovsdb_id, rm_mac,
                  get_devices, port_list, update_rpc, del_conn,
                  get_vlan_binding):
            self.plugin.delete_l2_gateway_connection(self.db_context,
                                                     fake_conn_dict)
            admin_check.assert_called_with(self.db_context, 'DELETE')
            get_con.assert_called_with(self.db_context, fake_conn_dict)
            get_id_list.assert_called_with(self.db_context, fake_conn_dict)
            get_ovsdb_id.assert_called_with(
                self.db_context, fake_conn_dict,
                fake_identifier_list)
            rm_mac.assert_called_with(self.db_context, None, fake_ovsdb_list)
            get_devices.assert_called_with(self.db_context, 'fake_l2gw_id')
            port_list.assert_called_with(
                self.db_context, fake_device_dict,
                fake_conn_dict, DELETE, fake_identifier_list)
            self.assertTrue(update_rpc.called)
            del_conn.assert_called_with(self.db_context, fake_conn_dict)

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
        with contextlib.nested(
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_admin_check',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin, 'get_l2_gateway',
                              return_value=fake_device),
            mock.patch.object(db, 'get_physical_port_by_name_and_ps',
                              return_value=fake_physical_port),
            mock.patch.object(db, 'get_physical_switch_by_name',
                              return_value=fake_physical_switch),
            mock.patch.object(db_query.L2GatewayCommonDbMixin,
                              '_get_network',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_get_l2_gateway',
                              return_value=True)
        ) as (get_l2gw, admin_check, phy_port, phy_switch, get_network,
              get_l2gateway):
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
        with contextlib.nested(
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_admin_check',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin, 'get_l2_gateway',
                              return_value=fake_device),
            mock.patch.object(db, 'get_physical_port_by_name_and_ps',
                              return_value=fake_physical_port),
            mock.patch.object(db, 'get_physical_switch_by_name',
                              return_value=fake_physical_switch),
            mock.patch.object(db_query.L2GatewayCommonDbMixin,
                              '_get_network',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_get_l2_gateway',
                              return_value=True)
        ) as (get_l2gw, admin_check, phy_port, phy_switch, get_network,
              get_l2gateway):
            self.assertRaises(l2gw_exc.L2GatewayPhysicalPortFaultStatus,
                              self.plugin.create_l2_gateway_connection,
                              self.db_context, fake_l2gw_conn_dict)

    def test_check_port_fault_status_and_switch_fault_status(self):
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
        with contextlib.nested(
            mock.patch.object(self.plugin,
                              'get_l2_gateway',
                              return_value=fake_device),
            mock.patch.object(db, 'get_physical_port_by_name_and_ps',
                              return_value=fake_physical_port),
            mock.patch.object(db, 'get_physical_switch_by_name',
                              return_value=fake_physical_switch)
        ) as (get_l2gw, phy_port, phy_switch):
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
        with contextlib.nested(
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_admin_check',
                              return_value=True),
            mock.patch.object(self.plugin,
                              '_validate_connection'),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'get_l2gateway_devices_by_gateway_id',
                              return_value=fake_device_list),
            mock.patch.object(self.plugin,
                              '_process_port_list',
                              return_value=(ovsdb_id,
                                            logical_switch,
                                            fake_port)),
            mock.patch.object(self.plugin,
                              '_get_logical_switch_dict',
                              return_value=fake_ls_dict),
            mock.patch.object(self.plugin,
                              '_get_port_details',
                              return_value=fake_port_list),
            mock.patch.object(self.plugin,
                              '_get_ip_details',
                              return_value=('fake_ip1', 'fake_ip2')),
            mock.patch.object(self.plugin, '_get_dict', return_value=mock.ANY),
            mock.patch.object(db, 'get_ucast_mac_remote_by_mac_and_ls'),
            mock.patch.object(self.plugin,
                              '_get_locator_list',
                              return_value=fake_pl_list),
            mock.patch.object(l2gw_plugin.L2gatewayAgentApi,
                              'update_connection_to_gateway'),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              'create_l2_gateway_connection')) as (
                admin_check, validate, get_devices, port_list, get_ls,
                get_port, get_ip, get_ucast_mac, get_dict, get_pl, update_rpc,
                create_conn):
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
            self.assertTrue(get_ucast_mac.called)
            self.assertTrue(get_pl.called)
            self.assertTrue(update_rpc.called)
            create_conn.assert_called_with(self.db_context,
                                           fake_l2gw_conn_dict)

    def test_create_l2gateway_connection_with_invalid_device(self):
        self.db_context = ctx.get_admin_context()
        fake_l2gw_conn_dict = {'l2_gateway_connection': {
            'id': 'fake_id', 'network_id': 'fake_network_id',
            'l2_gateway_id': 'fake_l2gw_id'}}
        fake_device = {'devices': [{'device_name': 'fake_device',
                       'interfaces': [{'name': 'fake_interface'}]}]}
        fake_physical_switch = None
        with contextlib.nested(
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_admin_check',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin, 'get_l2_gateway',
                              return_value=fake_device),
            mock.patch.object(db, 'get_physical_switch_by_name',
                              return_value=fake_physical_switch),
            mock.patch.object(db_query.L2GatewayCommonDbMixin,
                              '_get_network',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_get_l2_gateway',
                              return_value=True)
        ) as (get_l2gw, admin_check, phy_switch, get_network, get_l2gateway):
            self.assertRaises(l2gw_exc.L2GatewayDeviceNotFound,
                              self.plugin.create_l2_gateway_connection,
                              self.db_context, fake_l2gw_conn_dict)

    def test_create_l2gateway_connection_with_invalid_interface(self):
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
        with contextlib.nested(
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_admin_check',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin, 'get_l2_gateway',
                              return_value=fake_device),
            mock.patch.object(db, 'get_physical_switch_by_name',
                              return_value=fake_physical_switch),
            mock.patch.object(db, 'get_physical_port_by_name_and_ps',
                              return_value=fake_physical_port),
            mock.patch.object(db_query.L2GatewayCommonDbMixin,
                              '_get_network',
                              return_value=True),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '_get_l2_gateway',
                              return_value=True)
        ) as (get_l2gw, admin_check, phy_port, phy_switch, get_network,
              get_l2gateway):
            self.assertRaises(l2gw_exc.L2GatewayInterfaceNotFound,
                              self.plugin.create_l2_gateway_connection,
                              self.db_context, fake_l2gw_conn_dict)
