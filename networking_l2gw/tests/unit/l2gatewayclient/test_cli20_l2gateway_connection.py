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

from networking_l2gw.l2gatewayclient.l2gateway.v2_0 import l2gateway_connection
from networking_l2gw.tests.unit.l2gatewayclient import test_cli20


class CLITestV20L2gatewayConnectionJSON(test_cli20.CLITestV20Base):
    def setUp(self):
        super(CLITestV20L2gatewayConnectionJSON, self).setUp(
            plurals={'tags': 'tag'})

    def test_create_l2gateway_connection(self):
        """Test Create l2gateway-connection."""

        resource = 'l2_gateway_connection'
        cmd = l2gateway_connection.Createl2gatewayConnection(test_cli20.MyApp(
                                                             sys.stdout), None)
        l2gw_id = 'l2gw-id'
        net_id = 'net-id'
        args = [l2gw_id, net_id, '--default-segmentation-id', 'seg-id']
        position_names = ['l2_gateway_id', 'network_id', 'segmentation_id']
        position_values = [l2gw_id, net_id, 'seg-id']
        self._test_create_resource(resource, cmd, l2gw_id, 'myid', args,
                                   position_names, position_values)

    def test_list_l2gateway_connection(self):
        """Test List l2gateway-connection."""

        resources = "l2_gateway_connections"
        cmd = l2gateway_connection.Listl2gatewayConnection(test_cli20.MyApp(
                                                           sys.stdout), None)
        self._test_list_resources(resources, cmd, True)

    def test_delete_l2gateway_connection(self):
        """Test Delete l2gateway-connection."""

        resource = 'l2_gateway_connection'
        cmd = l2gateway_connection.Deletel2gatewayConnection(test_cli20.MyApp(
                                                             sys.stdout), None)
        my_id = 'my-id'
        args = [my_id]
        self._test_delete_resource(resource, cmd, my_id, args)

    def test_show_l2gateway_connection(self):
        """Test Show l2gateway-connection: --fields id --fields name myid."""

        resource = 'l2_gateway_connection'
        cmd = l2gateway_connection.Showl2gatewayConnection(test_cli20.MyApp(
                                                           sys.stdout), None)
        args = ['--fields', 'id', '--fields', 'name', self.test_id]
        self._test_show_resource(resource, cmd, self.test_id, args,
                                 ['id', 'name'])

    def test_update_l2gateway_connection(self):
        """Test Update l2gateway-connection."""

        resource = 'l2_gateway_connection'
        cmd = l2gateway_connection.Updatel2gatewayConnection(test_cli20.MyApp(
                                                             sys.stdout), None)
        self._test_update_resource(resource, cmd, 'myid',
                                   ['myid', '--segmentation_id', 'seg-id', ],
                                   {'segmentation_id': 'seg-id', }
                                   )
