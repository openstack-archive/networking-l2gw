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

import random
import socket
import ssl

import mock

from neutron.tests import base

from networking_l2gw.services.l2gateway.agent import l2gateway_config as conf
from networking_l2gw.services.l2gateway.agent.ovsdb import base_connection
from networking_l2gw.services.l2gateway.agent.ovsdb import ovsdb_writer
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import constants as n_const
from networking_l2gw.services.l2gateway.common import ovsdb_schema
from networking_l2gw.services.l2gateway import exceptions
from networking_l2gw.tests.unit.services.l2gateway.agent.ovsdb import (
    test_base_connection as base_test)

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

LOG = logging.getLogger(__name__)


class TestOVSDBWriter(base.BaseTestCase):
    def setUp(self):
        super(TestOVSDBWriter, self).setUp()
        self.conf = mock.patch.object(conf, 'L2GatewayConfig').start()
        config.register_ovsdb_opts_helper(cfg.CONF)
        cfg.CONF.set_override('max_connection_retries', 0, 'ovsdb')

        self.sock = mock.patch('socket.socket').start()
        self.ssl_sock = mock.patch.object(ssl, 'wrap_socket').start()
        self.op_id = 'abcd'
        self.l2gw_ovsdb = ovsdb_writer.OVSDBWriter(mock.Mock(),
                                                   self.conf)
        self.fake_message = {'id': self.op_id,
                             'fake_key': 'fake_value'}

        self.l2gw_ovsdb.responses = [self.fake_message]

    def test_process_response(self):
        """Test case to test _process_response."""
        expected_result = {'fake_key': 'fake_value'}
        with mock.patch.object(base_connection.BaseConnection,
                               '_response',
                               return_value={'fake_key': 'fake_value'}
                               ) as resp:
            result = self.l2gw_ovsdb._process_response(self.op_id)
            self.assertEqual(result, expected_result)
            resp.assert_called_with(self.op_id)

    def test_process_response_with_error(self):
        """Test case to test _process_response with error."""
        foo_dict = {'fake_key': 'fake_value',
                    'error': 'fake_error'}
        with mock.patch.object(base_connection.BaseConnection,
                               '_response',
                               return_value=foo_dict) as resp:
            self.assertRaises(exceptions.OVSDBError,
                              self.l2gw_ovsdb._process_response,
                              self.op_id)
            resp.assert_called_with(self.op_id)

    def test_process_response_with_error1(self):
        """Test case to test _process_response with errors in the

           subqueries.
        """
        fake_dict = {"id": "295366252499790541931626006259650283530",
                     "result":
                     [{"uuid":
                       ["uuid", "be236bbf-8f83-4bf0-816b-629c7e5b5609"
                        ]},
                      {},
                      {"error": "referential integrity violation",
                       "details": "Table Ucast_Macs_Remote column "
                                  "locator row "
                                  "be236bbf-8f83-4bf0-816b-629c7e5b5609 "
                                  "references nonexistent row "
                                  "1b143819-45a6-44ec-826a-ac75243a07ce in "
                                  "table Physical_Locator."
                       }],
                     "error": None}
        with mock.patch.object(base_connection.BaseConnection,
                               '_response',
                               return_value=fake_dict) as resp:
            self.assertRaises(exceptions.OVSDBError,
                              self.l2gw_ovsdb._process_response,
                              self.op_id)
            resp.assert_called_with(self.op_id)

    def test_get_reply(self):
        """Test case to test _get_reply."""
        ret_value = jsonutils.dumps({self.op_id:
                                     'foo_value'})
        with mock.patch.object(
            ovsdb_writer.OVSDBWriter,
            '_recv_data',
            return_value=jsonutils.dumps({self.op_id:
                                          'foo_value'})) as recv_data, \
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              '_process_response',
                              return_value=(ret_value, None)) as proc_response, \
            mock.patch.object(ovsdb_writer.LOG,
                              'debug'):
            self.l2gw_ovsdb._get_reply(self.op_id, mock.ANY)
            self.assertTrue(recv_data.called)
            self.assertTrue(proc_response.called)

    def test_send_and_receive(self):
        """Test case to test _send_and_receive."""
        with mock.patch.object(base_connection.BaseConnection,
                               'send', return_value=True
                               ) as mock_send:
            with mock.patch.object(ovsdb_writer.OVSDBWriter,
                                   '_get_reply') as mock_reply:
                self.l2gw_ovsdb._send_and_receive('some_query',
                                                  self.op_id, mock.ANY, True)
                mock_send.assert_called_with('some_query', addr=mock.ANY)
                mock_reply.assert_called_with(self.op_id, mock.ANY)

    def test_send_and_receive_with_rcv_required_false(self):
        """Test case to test _send_and_receive."""
        with mock.patch.object(base_connection.BaseConnection,
                               'send', return_value=True
                               ) as mock_send:
            with mock.patch.object(ovsdb_writer.OVSDBWriter,
                                   '_get_reply') as mock_reply:
                self.l2gw_ovsdb._send_and_receive('some_query',
                                                  self.op_id, mock.ANY, False)
                mock_send.assert_called_with('some_query', addr=mock.ANY)
                mock_reply.assert_not_called()

    def test_delete_logical_switch(self):
        """Test case to test delete_logical_switch."""
        commit_dict = {"op": "commit", "durable": True}
        query = {"method": "transact",
                 "params": [n_const.OVSDB_SCHEMA_NAME,
                            {"op": "delete",
                             "table": "Logical_Switch",
                             "where": [["_uuid", "==",
                                        ["uuid",
                                         'fake_logical_switch_uuid']]]},
                            commit_dict],
                 "id": self.op_id}
        with mock.patch.object(random,
                               'getrandbits',
                               return_value=self.op_id
                               ) as get_rand:
            with mock.patch.object(ovsdb_writer.OVSDBWriter,
                                   '_send_and_receive'
                                   ) as send_n_receive:
                with mock.patch.object(ovsdb_writer.LOG,
                                       'debug'):
                    self.l2gw_ovsdb.delete_logical_switch(
                        'fake_logical_switch_uuid', mock.ANY)
                    get_rand.assert_called_with(128)
                    send_n_receive.assert_called_with(query, self.op_id,
                                                      mock.ANY, True)

    def test_insert_ucast_macs_remote(self):
        """Test case to test insert ucast_macs_remote."""
        with mock.patch.object(ovsdb_writer.OVSDBWriter,
                               '_get_ucast_macs_remote_dict') as get_ucast_mac_remote, \
                mock.patch.object(random,
                                  'getrandbits',
                                  return_value=self.op_id
                                  ) as get_rand, \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_send_and_receive'
                                  ) as send_n_receive, \
                mock.patch.object(ovsdb_writer.LOG,
                                  'debug'), \
                mock.patch.object(ovsdb_schema, 'LogicalSwitch'), \
                mock.patch.object(ovsdb_schema, 'PhysicalLocator'), \
                mock.patch.object(ovsdb_schema, 'UcastMacsRemote'):
            self.l2gw_ovsdb.insert_ucast_macs_remote(mock.MagicMock(),
                                                     mock.MagicMock(),
                                                     mock.MagicMock(),
                                                     mock.ANY)
            get_rand.assert_called_with(128)
            send_n_receive.assert_called_with(mock.ANY,
                                              self.op_id, mock.ANY, True)

            self.assertTrue(get_ucast_mac_remote.called)

    def test_insert_ucast_macs_remote_with_no_locator_id(self):
        """Test case to test insert ucast_macs_remote

           without locator_id and logical_switch_id.
        """
        with mock.patch.object(ovsdb_writer.OVSDBWriter,
                               '_get_ucast_macs_remote_dict') as get_ucast_mac_remote, \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_get_physical_locator_dict') as get_physical_locator_dict, \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_get_logical_switch_dict') as get_logical_switch_dict, \
                mock.patch.object(random,
                                  'getrandbits',
                                  return_value=self.op_id
                                  ), \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_send_and_receive'
                                  ), \
                mock.patch.object(ovsdb_writer.LOG,
                                  'debug'), \
                mock.patch.object(ovsdb_schema, 'LogicalSwitch') as mock_ls, \
                mock.patch.object(ovsdb_schema, 'PhysicalLocator') as mock_pl, \
                mock.patch.object(ovsdb_schema, 'UcastMacsRemote'):
            locator = mock_pl.return_value
            locator.uuid = None
            ls = mock_ls.return_value
            ls.uuid = None
            ls.name = 'ab-cd'
            self.l2gw_ovsdb.insert_ucast_macs_remote(mock.MagicMock(),
                                                     mock.MagicMock(),
                                                     mock.MagicMock(),
                                                     mock.ANY)
            self.assertTrue(get_ucast_mac_remote.called)
            self.assertTrue(get_physical_locator_dict.called)
            self.assertTrue(get_logical_switch_dict.called)

    def test_update_ucast_macs_remote(self):
        """Test case to test update ucast_macs_remote."""
        with mock.patch.object(ovsdb_writer.OVSDBWriter,
                               '_get_dict_for_update_ucast_mac_remote') as get_update_ucast_mac_remote, \
                mock.patch.object(random,
                                  'getrandbits',
                                  return_value=self.op_id
                                  ) as get_rand, \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_send_and_receive'
                                  ) as send_n_receive, \
                mock.patch.object(ovsdb_writer.LOG,
                                  'debug'), \
                mock.patch.object(ovsdb_schema, 'PhysicalLocator'), \
                mock.patch.object(ovsdb_schema, 'UcastMacsRemote'):
            self.l2gw_ovsdb.update_ucast_macs_remote(mock.MagicMock(),
                                                     mock.MagicMock(),
                                                     mock.ANY)
            get_rand.assert_called_with(128)
            send_n_receive.assert_called_with(mock.ANY,
                                              self.op_id, mock.ANY, True)

            self.assertTrue(get_update_ucast_mac_remote.called)

    def test_update_ucast_macs_remote_with_no_locator_id(self):
        """Test case to test update ucast_macs_remote

           without locator_id and logical_switch_id.
        """
        with mock.patch.object(ovsdb_writer.OVSDBWriter,
                               '_get_dict_for_update_ucast_mac_remote') as get_update_ucast_mac_remote, \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_get_physical_locator_dict') as get_physical_locator_dict, \
                mock.patch.object(random,
                                  'getrandbits',
                                  return_value=self.op_id
                                  ), \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_send_and_receive'
                                  ), \
                mock.patch.object(ovsdb_writer.LOG,
                                  'debug'), \
                mock.patch.object(ovsdb_schema, 'PhysicalLocator') as mock_pl, \
                mock.patch.object(ovsdb_schema, 'UcastMacsRemote'):
            locator = mock_pl.return_value
            locator.uuid = None
            self.l2gw_ovsdb.update_ucast_macs_remote(mock.MagicMock(),
                                                     mock.MagicMock(),
                                                     mock.ANY)
            self.assertTrue(get_update_ucast_mac_remote.called)
            self.assertTrue(get_physical_locator_dict.called)

    def test_delete_ucast_macs_remote(self):
        """Test case to test delete_ucast_macs_remote."""
        with mock.patch.object(random,
                               'getrandbits',
                               return_value=self.op_id
                               ) as get_rand, \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_send_and_receive'
                                  ) as send_n_receive, \
                mock.patch.object(ovsdb_writer.LOG,
                                  'debug'):
            self.l2gw_ovsdb.delete_ucast_macs_remote(mock.Mock(),
                                                     mock.MagicMock(),
                                                     mock.ANY)
            get_rand.assert_called_with(128)
            send_n_receive.assert_called_with(mock.ANY,
                                              self.op_id, mock.ANY, True)

    def test_update_connection_to_gateway(self):
        """Test case to test update_connection_to_gateway."""
        with mock.patch.object(ovsdb_writer.OVSDBWriter,
                               '_get_bindings_to_update') as get_bindings, \
                mock.patch.object(random,
                                  'getrandbits',
                                  return_value=self.op_id
                                  ) as get_rand, \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_send_and_receive'
                                  ) as send_n_receive, \
                mock.patch.object(ovsdb_writer.LOG,
                                  'debug'):
            self.l2gw_ovsdb.update_connection_to_gateway(
                mock.Mock(), mock.Mock(), mock.Mock(), mock.Mock(),
                mock.ANY, mock.ANY)
            get_rand.assert_called_with(128)
            send_n_receive.assert_called_with(mock.ANY,
                                              self.op_id, mock.ANY, True)
            self.assertTrue(get_bindings.called)

    def test_get_bindings_to_update1(self):
        """Test case to test _get_bindings_to_update."""
        fake_op_method = 'CREATE'
        with mock.patch.object(ovsdb_writer.OVSDBWriter,
                               '_form_logical_switch') as form_ls, \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_form_physical_locators') as form_pl, \
                mock.patch.object(ovsdb_writer.OVSDBWriter,
                                  '_form_ports') as form_pp, \
                mock.patch.object(ovsdb_schema, 'LogicalSwitch') as mock_ls, \
                mock.patch.object(ovsdb_schema, 'PhysicalLocator') as mock_pl, \
                mock.patch.object(ovsdb_schema, 'UcastMacsRemote') as mock_ucmr, \
                mock.patch.object(ovsdb_schema, 'PhysicalPort') as mock_pp:
            ls = mock_ls.return_value = ovsdb_schema.LogicalSwitch(
                'ls_uuid', 'ls_name', 'ls_key', 'ls_desc')
            pl = mock_pl.return_value = ovsdb_schema.PhysicalLocator(
                'pl_uuid', 'pl_dst_ip')
            mock_ucmr.return_value = ovsdb_schema.UcastMacsRemote(
                'ucmr_uuid', 'ucmr_mac', 'ucmr_ls_id', 'ucmr_pl_id', 'ucmr_ip')
            pp = mock_pp.return_value = ovsdb_schema.PhysicalPort(
                'pp_uuid', 'pp_name', 'pp_ps_id', 'pp_vlan_bindings')
            form_ls.return_value = ['uuid', ls.uuid]
            self.l2gw_ovsdb._get_bindings_to_update(mock.MagicMock(),
                                                    [{'uuid': 'uuid',
                                                      'dst_ip': 'dst_ip'}],
                                                    mock.MagicMock(),
                                                    [{'uuid': 'uuid',
                                                      'name': 'name',
                                                      'physical_switch_id':
                                                      'physical_switch_id',
                                                      'vlan_bindings':
                                                      'vlan_bindings',
                                                      'port_fault_status':
                                                      'port_fault_status'}],
                                                    fake_op_method)

            form_ls.assert_called_with(ls, mock.ANY)
            form_pl.assert_called_with(['uuid', ls.uuid], [pl],
                                       mock.ANY, mock.ANY)
            form_pp.assert_called_with(['uuid', ls.uuid], [pp], mock.ANY,
                                       fake_op_method)

    def test_get_physical_locator_dict(self):
        """Test case to test _get_physical_locator_dict."""
        fake_locator = mock.Mock()
        fake_locator.uuid = 'fake_uuid'
        fake_locator.dst_ip = 'fake_dst_ip'
        phy_loc_dict = self.l2gw_ovsdb._get_physical_locator_dict(
            fake_locator)
        self.assertEqual(phy_loc_dict['row']['dst_ip'], fake_locator.dst_ip)
        self.assertEqual(phy_loc_dict['uuid-name'], fake_locator.uuid)

    def test_get_logical_switch_dict(self):
        """Test case to test _get_logical_switch_dict."""
        fake_ls = mock.Mock()
        fake_ls.uuid = 'fake_uuid'
        fake_ls.description = 'fake_desc'
        fake_ls.name = 'fake_name'
        fake_ls.key = 100
        logical_switch_dict = self.l2gw_ovsdb._get_logical_switch_dict(
            fake_ls)
        self.assertEqual(logical_switch_dict['uuid-name'], fake_ls.uuid)
        self.assertEqual(logical_switch_dict['row']['description'],
                         fake_ls.description)
        self.assertEqual(logical_switch_dict['row']['name'],
                         fake_ls.name)
        self.assertEqual(logical_switch_dict['row']['tunnel_key'],
                         fake_ls.key)

    def test_get_ucast_macs_remote_dict(self):
        """Test case to test _get_ucast_macs_remote_dict."""
        fake_mac = mock.Mock()
        fake_mac.mac = 'fake_mac'
        fake_mac.ip_address = 'fake_ip'
        locator_list = ['fake_list']
        logical_switch_list = ['fake_switch_list']
        ucast_mac_remote_dict = self.l2gw_ovsdb._get_ucast_macs_remote_dict(
            fake_mac, locator_list, logical_switch_list)
        self.assertEqual(ucast_mac_remote_dict['row']['MAC'], fake_mac.mac)
        self.assertEqual(ucast_mac_remote_dict['row']['ipaddr'],
                         fake_mac.ip_address)
        self.assertEqual(ucast_mac_remote_dict['row']['locator'], locator_list)
        self.assertEqual(ucast_mac_remote_dict['row']['logical_switch'],
                         logical_switch_list)

    def test_get_dict_for_update_ucast_mac_remote(self):
        """Test case to test _get_dict_for_update_ucast_mac_remote."""
        fake_mac = mock.Mock()
        fake_mac.uuid = 'fake_uuid'
        fake_mac.ip_address = 'fake_ip'
        locator_list = ['fake_list']
        temp_method = self.l2gw_ovsdb._get_dict_for_update_ucast_mac_remote
        ucast_mac_remote_dict = temp_method(
            fake_mac, locator_list)
        self.assertEqual(ucast_mac_remote_dict['row']['locator'], locator_list)
        self.assertEqual(ucast_mac_remote_dict['where'],
                         [["_uuid", "==", ["uuid", fake_mac.uuid]]])

    def test_recv_data(self):
        """Test case to test _recv_data with a valid data."""
        fake_data = {"fake_key": "fake_value"}
        fake_socket = base_test.SocketClass(None,
                                            None,
                                            None,
                                            base_test.FakeDecodeClass(
                                                jsonutils.dumps(fake_data)))
        with mock.patch.object(socket, 'socket', return_value=fake_socket):
                ovsdb_conf = base_test.FakeConf()
                l2gw_obj = ovsdb_writer.OVSDBWriter(
                    cfg.CONF.ovsdb, ovsdb_conf)
                result = l2gw_obj._recv_data(mock.ANY)
                self.assertEqual(jsonutils.dumps(fake_data), result)

    def test_recv_data_with_empty_data(self):
        """Test case to test _recv_data with empty data."""
        fake_socket = base_test.SocketClass(None,
                                            None,
                                            None,
                                            '')
        with mock.patch.object(socket, 'socket',
                               return_value=fake_socket):
            with mock.patch.object(ovsdb_writer.LOG, 'warning'):
                ovsdb_conf = base_test.FakeConf()
                l2gw_obj = ovsdb_writer.OVSDBWriter(
                    cfg.CONF.ovsdb, ovsdb_conf)
                result = l2gw_obj._recv_data(mock.ANY)
                self.assertIsNone(result)

    def test_recv_data_with_socket_error(self):
        """Test case to test _recv_data with socket error."""

        fake_socket = base_test.SocketClass(None,
                                            None,
                                            socket.error)
        with mock.patch.object(socket, 'socket', return_value=fake_socket):
            with mock.patch.object(ovsdb_writer.LOG,
                                   'warning') as fake_warn:
                ovsdb_conf = base_test.FakeConf()
                l2gw_obj = ovsdb_writer.OVSDBWriter(
                    cfg.CONF.ovsdb, ovsdb_conf)
                result = l2gw_obj._recv_data(mock.ANY)
                self.assertIsNone(result)
                fake_warn.assert_called_with(
                    "Did not receive any reply from the OVSDB server")
