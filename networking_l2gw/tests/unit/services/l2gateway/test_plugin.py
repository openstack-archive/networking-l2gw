# Copyright (c) 2016 Openstack Foundation
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

from neutron.tests import base

from networking_l2gw.db.l2gateway import l2gateway_db
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway import plugin as l2gw_plugin


class TestL2GatewayPlugin(base.BaseTestCase):

    def setUp(self):
        super(TestL2GatewayPlugin, self).setUp()
        mock.patch.object(config, 'register_l2gw_opts_helper')
        self.driver = mock.MagicMock()
        mock.patch('neutron.services.service_base.load_drivers',
                   return_value=({'dummyprovider': self.driver},
                                 'dummyprovider')).start()
        mock.patch.object(l2gateway_db.L2GatewayMixin, '__init__'),
        mock.patch.object(l2gateway_db, 'subscribe')
        mock.patch('neutron.db.servicetype_db.ServiceTypeManager.get_instance',
                   return_value=mock.MagicMock()).start()
        self.context = mock.MagicMock()
        self.plugin = l2gw_plugin.L2GatewayPlugin()
        self.ovsdb_identifier = 'fake_ovsdb_id'

    def _get_fake_l2_gateway(self):
        fake_l2_gateway_id = "5227c228-6bba-4bbe-bdb8-6942768ff0f1"
        fake_l2_gateway = {
            "tenant_id": "de0a7495-05c4-4be0-b796-1412835c6820",
            "id": "5227c228-6bba-4bbe-bdb8-6942768ff0f1",
            "name": "test-gateway",
            "devices": [
                {
                    "device_name": "switch1",
                    "interfaces": [
                        {
                            "name": "port1",
                            "segmentation_id": [100]
                        },
                        {
                            "name": "port2",
                            "segmentation_id": [151, 152]
                        }
                    ]
                }
            ]
        }
        return fake_l2_gateway_id, fake_l2_gateway

    def _get_fake_l2_gateway_connection(self):
        fake_l2_gateway_conn_id = "5227c228-6bba-4bbe-bdb8-6942768ff02f"
        fake_l2_gateway_conn = {
            "tenant_id": "de0a7495-05c4-4be0-b796-1412835c6820",
            "id": "5227c228-6bba-4bbe-bdb8-6942768ff02f",
            "default_segmentation_id": 77,
            "network_id": "5227c228-6bba-4bbe-bdb8-6942768ff077",
            "l2_gateway_id": "4227c228-6bba-4bbe-bdb8-6942768ff088"
        }
        return fake_l2_gateway_conn_id, fake_l2_gateway_conn

    def test_add_port_mac(self):
        self.plugin.add_port_mac(self.context, {})
        self.driver.add_port_mac.assert_called_once_with(self.context, {})

    def test_delete_port_mac(self):
        self.plugin.delete_port_mac(self.context, {})
        self.driver.delete_port_mac.assert_called_once_with(self.context, {})

    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'validate_l2_gateway_for_create')
    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'create_l2_gateway')
    def test_create_l2_gateway(self, mock_create_l2gw_db,
                               mock_validate_for_create):
        fake_l2gw_id, fake_l2gw = self._get_fake_l2_gateway()
        mock_create_l2gw_db.return_value = fake_l2gw
        self.plugin.create_l2_gateway(self.context, fake_l2gw)
        mock_validate_for_create.assert_called_with(self.context,
                                                    fake_l2gw)
        mock_create_l2gw_db.assert_called_with(self.context, fake_l2gw)
        self.driver.create_l2_gateway.assert_called_once_with(self.context,
                                                              fake_l2gw)
        self.driver.create_l2_gateway_precommit.assert_called_once_with(
            self.context, fake_l2gw)
        self.driver.create_l2_gateway_postcommit.assert_called_once_with(
            self.context, fake_l2gw)

    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'validate_l2_gateway_for_delete')
    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'delete_l2_gateway')
    def test_delete_l2_gateway(self, mock_delete_l2gw_db,
                               mock_validate_for_delete):
        fake_l2gw_id, fake_l2gw = self._get_fake_l2_gateway()
        self.plugin.delete_l2_gateway(self.context, fake_l2gw_id)
        mock_validate_for_delete.assert_called_with(self.context,
                                                    fake_l2gw_id)
        mock_delete_l2gw_db.assert_called_with(self.context, fake_l2gw_id)
        self.driver.delete_l2_gateway.assert_called_once_with(self.context,
                                                              fake_l2gw_id)
        self.driver.delete_l2_gateway_precommit.assert_called_once_with(
            self.context, fake_l2gw_id)
        self.driver.delete_l2_gateway_postcommit.assert_called_once_with(
            self.context, fake_l2gw_id)

    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'validate_l2_gateway_for_update')
    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'update_l2_gateway')
    def test_update_l2_gateway(self, mock_update_l2gw_db,
                               mock_validate_for_update):
        fake_l2gw_id, fake_l2gw = self._get_fake_l2_gateway()
        mock_update_l2gw_db.return_value = fake_l2gw
        self.plugin.update_l2_gateway(self.context,
                                      fake_l2gw_id,
                                      fake_l2gw)
        mock_validate_for_update.assert_called_with(self.context,
                                                    fake_l2gw_id,
                                                    fake_l2gw)
        mock_update_l2gw_db.assert_called_with(self.context, fake_l2gw_id,
                                               fake_l2gw)
        self.driver.update_l2_gateway.assert_called_once_with(self.context,
                                                              fake_l2gw_id,
                                                              fake_l2gw)
        self.driver.update_l2_gateway_precommit.assert_called_once_with(
            self.context, fake_l2gw)
        self.driver.update_l2_gateway_postcommit.assert_called_once_with(
            self.context, fake_l2gw)

    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'validate_l2_gateway_connection_for_create')
    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'create_l2_gateway_connection')
    def test_create_l2_gateway_connection(self, mock_conn_create_l2gw_db,
                                          mock_validate_for_conn_create):
        fake_l2gw_conn_id, fake_l2gw_conn = (
            self._get_fake_l2_gateway_connection())
        mock_conn_create_l2gw_db.return_value = fake_l2gw_conn
        self.plugin.create_l2_gateway_connection(self.context,
                                                 fake_l2gw_conn)
        mock_validate_for_conn_create.assert_called_with(self.context,
                                                         fake_l2gw_conn)
        mock_conn_create_l2gw_db.assert_called_with(self.context,
                                                    fake_l2gw_conn)
        self.driver.create_l2_gateway_connection.assert_called_once_with(
            self.context, fake_l2gw_conn)
        (self.driver.create_l2_gateway_connection_precommit.
            assert_called_once_with(self.context, fake_l2gw_conn))
        (self.driver.create_l2_gateway_connection_postcommit.
            assert_called_once_with(self.context, fake_l2gw_conn))

    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'validate_l2_gateway_connection_for_delete')
    @mock.patch.object(l2gateway_db.L2GatewayMixin,
                       'delete_l2_gateway_connection')
    def test_delete_l2_gateway_connection(self, mock_conn_delete_l2gw_db,
                                          mock_validate_for_conn_delete):
        fake_l2gw_conn_id, fake_l2gw_conn = (
            self._get_fake_l2_gateway_connection())
        self.plugin.delete_l2_gateway_connection(self.context,
                                                 fake_l2gw_conn_id)
        mock_validate_for_conn_delete.assert_called_with(self.context,
                                                         fake_l2gw_conn_id)
        mock_conn_delete_l2gw_db.assert_called_with(self.context,
                                                    fake_l2gw_conn_id)
        self.driver.delete_l2_gateway_connection.assert_called_once_with(
            self.context, fake_l2gw_conn_id)
        (self.driver.delete_l2_gateway_connection_precommit.
            assert_called_once_with(self.context, fake_l2gw_conn_id))
        (self.driver.delete_l2_gateway_connection_postcommit.
            assert_called_once_with(self.context, fake_l2gw_conn_id))
