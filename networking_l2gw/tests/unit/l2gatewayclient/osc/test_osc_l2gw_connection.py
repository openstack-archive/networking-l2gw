# All Rights Reserved 2018
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

import operator

import mock
from osc_lib import utils as osc_utils
from osc_lib.utils import columns as column_util

from neutronclient.tests.unit.osc.v2 import fakes as test_fakes

from networking_l2gw.l2gatewayclient.osc import l2gw_connection as \
    osc_l2gw_conn
from networking_l2gw.tests.unit.l2gatewayclient.osc import fakes

columns_long = tuple(col for col, _, listing_mode in osc_l2gw_conn._attr_map
                     if listing_mode in (column_util.LIST_BOTH,
                                         column_util.LIST_LONG_ONLY))
headers_long = tuple(head for _, head, listing_mode in osc_l2gw_conn._attr_map
                     if listing_mode in (column_util.LIST_BOTH,
                                         column_util.LIST_LONG_ONLY))
sorted_attr_map = sorted(osc_l2gw_conn._attr_map, key=operator.itemgetter(1))
sorted_columns = tuple(col for col, _, _ in sorted_attr_map)
sorted_headers = tuple(head for _, head, _ in sorted_attr_map)


def _get_data(attrs, columns=sorted_columns):
    return osc_utils.get_dict_properties(attrs, columns)


class TestCreateL2gwConnection(test_fakes.TestNeutronClientOSCV2):
    columns = (
        'ID',
        'L2 GateWay ID',
        'Network ID',
        'Segmentation ID',
        'Tenant'
    )

    def setUp(self):
        super(TestCreateL2gwConnection, self).setUp()
        self.cmd = osc_l2gw_conn.CreateL2gwConnection(
            self.app, self.namespace)
        self.neutronclient.find_resource = mock.Mock(
            side_effect=lambda _, name_or_id, *x: {'id': name_or_id})

    def test_create_l2gateway_connection(self):
        """Test Create l2gateway-connection."""

        fake_connection = fakes.FakeL2GWConnection.create_l2gw_connection()
        self.neutronclient.post = mock.Mock(
            return_value={
                osc_l2gw_conn.L2_GATEWAY_CONNECTION: fake_connection
            })

        arg_list = [
            fake_connection['l2_gateway_id'],
            fake_connection['network_id'],
            '--default-segmentation-id', fake_connection['segmentation_id']
        ]
        verify_list = [
            ('gateway_name', fake_connection['l2_gateway_id']),
            ('network', fake_connection['network_id']),
            ('seg_id', fake_connection['segmentation_id'])
        ]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)
        columns, data = self.cmd.take_action(parsed_args)
        self.neutronclient.post.assert_called_once_with(
            osc_l2gw_conn.object_path,
            {osc_l2gw_conn.L2_GATEWAY_CONNECTION:
                {'segmentation_id': fake_connection['segmentation_id'],
                 'network_id': fake_connection['network_id'],
                 'l2_gateway_id': fake_connection['l2_gateway_id']
                 }
             }
        )
        self.assertEqual(self.columns, columns)
        self.assertItemEqual(_get_data(fake_connection), data)


class TestListL2gwConnection(test_fakes.TestNeutronClientOSCV2):
    def setUp(self):
        super(TestListL2gwConnection, self).setUp()
        self.cmd = osc_l2gw_conn.ListL2gwConnection(self.app, self.namespace)

    def test_list_l2gateway_connection(self):
        """Test List l2gateway-connections."""

        fake_connections = fakes.FakeL2GWConnection.create_l2gw_connections(
            count=3)
        self.neutronclient.list = mock.Mock(return_value=fake_connections)
        arg_list = []
        verify_list = []

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)

        headers, data = self.cmd.take_action(parsed_args)

        self.neutronclient.list.assert_called_once()
        self.assertEqual(headers, list(headers_long))
        self.assertListItemEqual(
            list(data),
            [_get_data(fake_connection, columns_long) for fake_connection
             in fake_connections[osc_l2gw_conn.L2_GATEWAY_CONNECTIONS]]
        )


class TestShowL2gwConnection(test_fakes.TestNeutronClientOSCV2):
    def setUp(self):
        super(TestShowL2gwConnection, self).setUp()
        self.cmd = osc_l2gw_conn.ShowL2gwConnection(self.app, self.namespace)
        self.neutronclient.find_resource = mock.Mock(
            side_effect=lambda _, name_or_id, *x: {'id': name_or_id})

    def test_show_l2gateway_connection(self):
        """Test Show l2gateway-connection."""

        fake_connection = fakes.FakeL2GWConnection.create_l2gw_connection()
        self.neutronclient.get = mock.Mock(
            return_value={
                osc_l2gw_conn.L2_GATEWAY_CONNECTION: fake_connection
            })
        arg_list = [fake_connection['id']]
        verify_list = [
            (osc_l2gw_conn.L2_GATEWAY_CONNECTION, fake_connection['id'])
        ]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)

        headers, data = self.cmd.take_action(parsed_args)

        self.neutronclient.get.assert_called_once_with(
            osc_l2gw_conn.resource_path % fake_connection['id'])
        self.assertEqual(sorted_headers, headers)
        self.assertItemEqual(_get_data(fake_connection), data)


class TestDeleteL2gwConnection(test_fakes.TestNeutronClientOSCV2):
    def setUp(self):
        super(TestDeleteL2gwConnection, self).setUp()
        self.neutronclient.find_resource = mock.Mock(
            side_effect=lambda _, name_or_id: {'id': name_or_id})
        self.cmd = osc_l2gw_conn.DeleteL2gwConnection(self.app, self.namespace)

    def test_delete_l2gateway_connection(self):
        """Test Delete l2gateway-connection."""

        fake_connection = fakes.FakeL2GWConnection.create_l2gw_connection()
        self.neutronclient.delete = mock.Mock(return_value=fake_connection)
        arg_list = [fake_connection['id']]
        verify_list = [
            (osc_l2gw_conn.L2_GATEWAY_CONNECTIONS, [fake_connection['id']])
        ]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)

        result = self.cmd.take_action(parsed_args)

        self.neutronclient.delete.assert_called_once_with(
            osc_l2gw_conn.resource_path % fake_connection['id'])
        self.assertIsNone(result)
