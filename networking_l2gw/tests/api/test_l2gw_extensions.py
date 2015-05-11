# Copyright 2015 Hewlett-Packard Development Company, L.P.
# Copyright 2015 OpenStack Foundation
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

from neutron.tests.api import base
from neutron.tests.tempest import test

from tempest_lib.common.utils import data_utils

from networking_l2gw.tests.api import base_l2gw
from networking_l2gw.tests.tempest import config


CONF = config.CONF


class L2GatewayExtensionTestJSON(base.BaseAdminNetworkTest):
    _interface = 'json'

    """
    Tests the following operations in the Neutron API using the REST client for
    Neutron:
        Create l2gateway
        List l2gateways
        Show l2gateway
        Update l2gateway
        Delete l2gateway
        Create l2gatewayconnection
        List l2gatewayconnections
        Show l2gatewayconnection
        Delete l2gatewayconnection
    """

    @classmethod
    def resource_setup(cls):
        super(L2GatewayExtensionTestJSON, cls).resource_setup()
        # Atleast one switch detail should be provided to run the tests
        if (len(CONF.network.l2gw_switch) < 0):
            msg = ('Atleast one switch detail must be defined.')
            raise cls.skipException(msg)
        if not test.is_extension_enabled('l2gateway', 'network'):
            msg = "L2Gateway Extension not enabled."
            raise cls.skipException(msg)

    @test.idempotent_id('3ca07946-a3c9-49ac-b058-8be54abecf1f')
    def test_create_show_list_update_delete_l2gateway(self):
        # Create an L2Gateway
        gw_name = data_utils.rand_name('l2gw')
        devices = base_l2gw.get_l2gw_body(CONF.network.l2gw_switch)["devices"]
        body = self.admin_client.create_l2_gateway(
            name=gw_name, devices=devices)
        l2_gateway = body['l2_gateway']
        self.addCleanup(self.admin_client.delete_l2_gateway, l2_gateway['id'])
        # Show details of L2Gateway
        show_body = self.admin_client.show_l2_gateway(l2_gateway['id'])
        self.assertEqual(gw_name, show_body['l2_gateway']['name'])
        conf_devices = base_l2gw.form_dict_devices(devices)
        create_devices = base_l2gw.form_dict_devices(show_body['l2_gateway']
                                                     ['devices'])
        # Validate the resource provided in the conf and created
        for k, v in zip(conf_devices.items(), create_devices.items()):
            self.assertEqual(k, v)
        # List L2Gateways
        self.admin_client.list_l2_gateways()
        # Update the name of an L2Gateway and verify the same
        updated_name = 'updated ' + gw_name
        update_body = self.admin_client.update_l2_gateway(l2_gateway['id'],
                                                          name=updated_name)
        self.assertEqual(update_body['l2_gateway']['name'], updated_name)
        show_body = self.admin_client.show_l2_gateway(l2_gateway['id'])
        self.assertEqual(show_body['l2_gateway']['name'], updated_name)

    @test.idempotent_id('3ad5e945-2b42-4ea8-9c03-0bf41d4167f2')
    def test_create_show_list_delete_l2gateway_connection(self):
        # Create a network
        name = data_utils.rand_name('network')
        net_body = self.admin_client.create_network(name=name)
        net_id = net_body['network']['id']
        self.addCleanup(self.admin_client.delete_network, net_id)
        # Create an L2Gateway
        gw_name = data_utils.rand_name('l2gw')
        devices = base_l2gw.get_l2gw_body(CONF.network.l2gw_switch)["devices"]
        l2_gw_body = self.admin_client.create_l2_gateway(
            name=gw_name, devices=devices)
        l2_gw_id = l2_gw_body['l2_gateway']['id']
        self.addCleanup(self.admin_client.delete_l2_gateway, l2_gw_id)
        # Create an L2Gateway Connection
        l2_gw_conn_body = self.admin_client.create_l2_gateway_connection(
            l2_gateway_id=l2_gw_id, network_id=net_id)
        l2_gw_conn_id = l2_gw_conn_body['l2_gateway_connection']['id']
        self.addCleanup(self.admin_client.delete_l2_gateway_connection,
                        l2_gw_conn_id)
        # Show details of created L2 Gateway connection
        show_body = self.admin_client.show_l2_gateway_connection(l2_gw_conn_id)
        l2_gw_conn = show_body['l2_gateway_connection']
        self.assertEqual(net_id, l2_gw_conn['network_id'])
        self.assertEqual(l2_gw_id, l2_gw_conn['l2_gateway_id'])
        # List L2Gateway Connections
        self.admin_client.list_l2_gateway_connections()
