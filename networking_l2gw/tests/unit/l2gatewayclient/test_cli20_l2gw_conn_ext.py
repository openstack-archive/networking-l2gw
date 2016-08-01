# Copyright 2015 OpenStack Foundation.
# All Rights Reserved
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
#

import sys

import mock

from networking_l2gw.l2gatewayclient.l2gw_client_ext import (
    _l2_gateway_connection as l2_gateway_connection)
from networking_l2gw.tests.unit.l2gatewayclient import test_cli20

from neutronclient import shell


class CLITestV20ExtensionL2GWJSON(test_cli20.CLITestV20Base):
    def setUp(self):
        # need to mock before super because extensions loaded on instantiation
        self._mock_extension_loading()
        super(CLITestV20ExtensionL2GWJSON, self).setUp(plurals={'tags': 'tag'})

    def _create_patch(self, name, func=None):
        patcher = mock.patch(name)
        thing = patcher.start()
        return thing

    def _mock_extension_loading(self):
        ext_pkg = 'neutronclient.common.extension'
        contrib = self._create_patch(ext_pkg + '._discover_via_entry_points')
        contrib.return_value = [("_l2_gateway_connection",
                                 l2_gateway_connection)]
        return contrib

    def test_ext_cmd_loaded(self):
        """Tests l2gw-connection commands loaded."""
        shell.NeutronShell('2.0')
        ext_cmd = {'l2-gateway-connection-list':
                   l2_gateway_connection.L2GatewayConnectionList,
                   'l2-gateway-connection-create':
                   l2_gateway_connection.L2GatewayConnectionCreate,
                   'l2-gateway-connection-delete':
                   l2_gateway_connection.L2GatewayConnectionDelete,
                   'l2-gateway-connection-show':
                   l2_gateway_connection.L2GatewayConnectionShow}
        self.assertDictContainsSubset(ext_cmd, shell.COMMANDS['2.0'])

    def test_create_l2gateway_connection(self):
        """Test Create l2gateway-connection."""

        resource = 'l2_gateway_connection'
        cmd = l2_gateway_connection.L2GatewayConnectionCreate(
            test_cli20.MyApp(sys.stdout), None)
        l2gw_id = 'l2gw-id'
        net_id = 'net-id'
        args = [l2gw_id, net_id, '--default-segmentation-id', 'seg-id']
        position_names = ['l2_gateway_id', 'network_id', 'segmentation_id']
        position_values = [l2gw_id, net_id, 'seg-id']
        self._test_create_resource(resource, cmd, l2gw_id, 'myid', args,
                                   position_names, position_values)

    def test_list_l2gateway_connection(self):
        """Test List l2gateway-connections."""

        resources = "l2_gateway_connections"
        cmd = l2_gateway_connection.L2GatewayConnectionList(
            test_cli20.MyApp(sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_delete_l2gateway_connection(self):
        """Test Delete l2gateway-connection."""

        resource = 'l2_gateway_connection'
        cmd = l2_gateway_connection.L2GatewayConnectionDelete(
            test_cli20.MyApp(sys.stdout), None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)

    def test_show_l2gateway_connection(self):
        """Test Show l2gateway-connection: --fields id --fields name myid."""

        resource = 'l2_gateway_connection'
        cmd = l2_gateway_connection.L2GatewayConnectionShow(
            test_cli20.MyApp(sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args,
                                 ['id', 'name'])
