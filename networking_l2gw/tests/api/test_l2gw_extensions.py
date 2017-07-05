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

import random

from neutron.tests.tempest.api import base
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest import test

from networking_l2gw.tests.api import base_l2gw

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
        # At least one switch detail should be provided to run the tests
        if (len(CONF.l2gw.l2gw_switch) <= 0):
            msg = ('At least one switch detail must be defined.')
            raise cls.skipException(msg)
        if not test.is_extension_enabled('l2-gateway', 'network'):
            msg = "L2Gateway Extension not enabled."
            raise cls.skipException(msg)

    @decorators.idempotent_id('3ca07946-a3c9-49ac-b058-8be54abecf1f')
    def test_create_show_list_update_delete_l2gateway(self):
        # Create an L2Gateway
        gw_name = data_utils.rand_name('l2gw')
        devices = base_l2gw.get_l2gw_body(CONF.l2gw.l2gw_switch)["devices"]
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

    @decorators.idempotent_id('3ad5e945-2b42-4ea8-9c03-0bf41d4167f2')
    def test_create_show_list_delete_l2gateway_connection(self):
        # Create a network
        name = data_utils.rand_name('network')
        net_body = self.admin_client.create_network(name=name)
        net_id = net_body['network']['id']
        self.addCleanup(self.admin_client.delete_network, net_id)
        # Create an L2Gateway
        gw_name = data_utils.rand_name('l2gw')
        devices = base_l2gw.get_l2gw_body(CONF.l2gw.l2gw_switch)["devices"]
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

    def test_create_l2gw_conn_with_segid_when_l2gw_created_without_segid(self):
        # Create an L2Gateway
        gw_name = data_utils.rand_name('l2gw')
        devices = base_l2gw.get_l2gw_body(CONF.l2gw.l2gw_switch)["devices"]
        if devices[0]['interfaces'][0]['segmentation_id']:
            seg_id = devices[0]['interfaces'][0]['segmentation_id'][0]
            devices[0]['interfaces'][0].pop('segmentation_id')
        body = self.admin_client.create_l2_gateway(
            name=gw_name, devices=devices)
        l2_gateway = body['l2_gateway']
        l2_gw_id = l2_gateway['id']
        self.addCleanup(self.admin_client.delete_l2_gateway, l2_gw_id)
        # Create a network
        name = data_utils.rand_name('network')
        net_body = self.admin_client.create_network(name=name)
        net_id = net_body['network']['id']
        self.addCleanup(self.admin_client.delete_network, net_id)
        # Create an L2Gateway Connection
        l2_gw_conn_body = self.admin_client.create_l2_gateway_connection(
            l2_gateway_id=l2_gw_id, network_id=net_id,
            segmentation_id=seg_id)
        l2_gw_conn_id = l2_gw_conn_body['l2_gateway_connection']['id']
        l2_gw_seg_id = l2_gw_conn_body['l2_gateway_connection'][
            'segmentation_id']
        self.addCleanup(self.admin_client.delete_l2_gateway_connection,
                        l2_gw_conn_id)
        # Show details of created L2 Gateway connection
        show_body = self.admin_client.show_l2_gateway_connection(
            l2_gw_conn_id)
        l2_gw_conn = show_body['l2_gateway_connection']
        self.assertEqual(net_id, l2_gw_conn['network_id'])
        self.assertEqual(l2_gw_id, l2_gw_conn['l2_gateway_id'])
        self.assertEqual(str(l2_gw_seg_id),
                         str(l2_gw_conn['segmentation_id']))

    def test_create_update_l2gw_with_multiple_devices(self):
        # Generating name for multi-device L2Gateway
        gw_name = data_utils.rand_name('l2gw')
        # Generating a list consisting 3 random segmentation_ids
        seg_id = random.sample(range(2, 4095), 3)
        # Generating 3 device and interface names
        dev_name1 = data_utils.rand_name('device_name')
        interface_name1 = data_utils.rand_name('interface')
        dev_name2 = data_utils.rand_name('device_name')
        interface_name2 = data_utils.rand_name('interface')
        dev_name3 = data_utils.rand_name('device_name')
        interface_name3 = data_utils.rand_name('interface')
        device_name_list = [dev_name1, dev_name2, dev_name3]
        interface_name_list = [
            interface_name1, interface_name2, interface_name3]
        # Forming the device for multi-device L2Gateway
        devices_list = [{"device_name": device_name_list[0], "interfaces":[{
            "name": interface_name_list[0]}],
            "segmentation_id": str(seg_id[0])}, {
            "device_name": device_name_list[1], "interfaces":[{
                "name": interface_name_list[1]}],
            "segmentation_id": str(seg_id[1])}, {
            "device_name": device_name_list[2], "interfaces":[{
                "name": interface_name_list[2]}],
            "segmentation_id": str(seg_id[2])}]
        # Create the multi-device L2gateway
        body = self.admin_client.create_l2_gateway(
            name=gw_name, devices=devices_list)
        l2_gateway = body['l2_gateway']
        l2_gw_id = l2_gateway['id']
        self.addCleanup(self.admin_client.delete_l2_gateway, l2_gw_id)
        # Check the created multi-device L2Gateway
        device_list = range(3)
        interface_list = range(3)
        show_body = self.admin_client.show_l2_gateway(l2_gw_id)
        self.assertEqual(gw_name, show_body['l2_gateway']['name'])
        self.assertEqual(l2_gateway['id'], show_body['l2_gateway']['id'])
        for i in range(3):
            device_list[i] = show_body['l2_gateway']['devices'][i][
                'device_name']
            interface_list[i] = show_body['l2_gateway']['devices'][i][
                'interfaces'][0]['name']
        for j in [0, 1, 2]:
            self.assertIn(device_name_list[j], device_list)
            self.assertIn(interface_name_list[j], interface_list)
        # Update the gateway device name
        device_list_updated = range(3)
        interface_list_updated = range(3)
        device_updated = [{"device_name": device_name_list[0], "interfaces":[{
            "name": "intNameNew"}]}]
        interface_name_list = [
            interface_name_list[2], interface_name_list[1], "intNameNew"]
        body = self.admin_client.update_l2_gateway(
            l2_gateway['id'], devices=device_updated)
        show_body_updated = self.admin_client.show_l2_gateway(
            l2_gateway['id'])
        # Check updating of multi-device L2gateway
        self.assertEqual(gw_name, show_body_updated['l2_gateway']['name'])
        self.assertEqual(l2_gateway['id'],
                         show_body_updated['l2_gateway']['id'])
        for k in range(3):
            device_list_updated[k] = show_body_updated['l2_gateway'][
                'devices'][k]['device_name']
            interface_list_updated[k] = show_body_updated['l2_gateway'][
                'devices'][k]['interfaces'][0]['name']
        for l in range(3):
            self.assertIn(device_name_list[l], device_list_updated)
            self.assertIn(interface_name_list[l], interface_list_updated)
