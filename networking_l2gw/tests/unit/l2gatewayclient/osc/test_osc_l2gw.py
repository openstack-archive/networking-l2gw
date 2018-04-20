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

import copy
import operator

import mock
from osc_lib import utils as osc_utils
from osc_lib.utils import columns as column_util

from neutronclient.tests.unit.osc.v2 import fakes as test_fakes

from networking_l2gw.l2gatewayclient.osc import l2gw as osc_l2gw
from networking_l2gw.tests.unit.l2gatewayclient.osc import fakes


columns_long = tuple(col for col, _, listing_mode in osc_l2gw._attr_map
                     if listing_mode in (column_util.LIST_BOTH,
                                         column_util.LIST_LONG_ONLY))
headers_long = tuple(head for _, head, listing_mode in osc_l2gw._attr_map
                     if listing_mode in (column_util.LIST_BOTH,
                                         column_util.LIST_LONG_ONLY))
sorted_attr_map = sorted(osc_l2gw._attr_map, key=operator.itemgetter(1))
sorted_columns = tuple(col for col, _, _ in sorted_attr_map)
sorted_headers = tuple(head for _, head, _ in sorted_attr_map)


def _get_data(attrs, columns=sorted_columns):
    return osc_utils.get_dict_properties(attrs, columns,
                                         formatters=osc_l2gw._formatters)


class TestCreateL2gw(test_fakes.TestNeutronClientOSCV2):

    columns = (
        'Devices',
        'ID',
        'Name',
        'Tenant'
    )

    def setUp(self):
        super(TestCreateL2gw, self).setUp()
        self.cmd = osc_l2gw.CreateL2gw(self.app, self.namespace)

    def _assert_create_succeeded(self, fake_l2gw, arg_list, verify_list):
        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)
        columns, data = self.cmd.take_action(parsed_args)
        self.neutronclient.post.assert_called_once_with(
            osc_l2gw.object_path,
            {osc_l2gw.L2_GATEWAY:
                {'name': fake_l2gw['name'], 'devices': fake_l2gw['devices']}}
        )
        self.assertEqual(self.columns, columns)
        self.assertItemEqual(_get_data(fake_l2gw), data)

    def test_create_l2gw(self):
        """Test Create l2gateway."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()

        self.neutronclient.post = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: fake_l2gw})
        l2gw_device = fake_l2gw['devices'][0]
        arg_list = [
            '--device', 'name=' + l2gw_device['device_name'] +
            ',interface_names=' + l2gw_device['interfaces'][0]['name'],
            fake_l2gw['name']
        ]

        verify_list = [
            ('devices', [
                {'interface_names': l2gw_device['interfaces'][0]['name'],
                 'name': l2gw_device['device_name']}]),
            ('name', fake_l2gw['name']),
        ]

        self._assert_create_succeeded(fake_l2gw, arg_list, verify_list)

    def test_create_l2gateway_with_multiple_devices(self):
        """Test Create l2gateway for multiple devices."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw(num_dev=2)

        self.neutronclient.post = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: fake_l2gw})
        l2gw_device_1 = fake_l2gw['devices'][0]
        l2gw_device_2 = fake_l2gw['devices'][1]
        arg_list = [
            '--device', 'name=' + l2gw_device_1['device_name'] +
            ',interface_names=' +
            l2gw_device_1['interfaces'][0]['name'],
            '--device', 'name=' + l2gw_device_2['device_name'] +
            ',interface_names=' +
            l2gw_device_2['interfaces'][0]['name'],
            fake_l2gw['name']
        ]
        verify_list = [
            ('devices', [
                {'interface_names': l2gw_device_1['interfaces'][0]['name'],
                 'name': l2gw_device_1['device_name']},
                {'interface_names': l2gw_device_2['interfaces'][0]['name'],
                 'name': l2gw_device_2['device_name']},
            ]),
            ('name', fake_l2gw['name']),
        ]

        self._assert_create_succeeded(fake_l2gw, arg_list, verify_list)

    def test_create_l2gateway_with_multiple_interfaces(self):
        """Test Create l2gateway with multiple interfaces."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw(num_if=2)

        self.neutronclient.post = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: fake_l2gw})
        l2gw_device = fake_l2gw['devices'][0]
        l2gw_interface_1 = l2gw_device['interfaces'][0]
        l2gw_interface_2 = l2gw_device['interfaces'][1]
        arg_list = [
            '--device', 'name=' + l2gw_device['device_name'] +
            ',interface_names=' + l2gw_interface_1['name'] + ';' +
            l2gw_interface_2['name'],
            fake_l2gw['name']
        ]
        verify_list = [
            ('devices', [
                {
                    'interface_names':
                        l2gw_interface_1['name'] + ';' +
                        l2gw_interface_2['name'],
                    'name': l2gw_device['device_name']
                }
            ]),
            ('name', fake_l2gw['name']),
        ]

        self._assert_create_succeeded(fake_l2gw, arg_list, verify_list)

    def test_create_l2gateway_with_segmentation_id(self):
        """Test Create l2gateway with segmentation-id."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()
        fake_l2gw['devices'][0]['interfaces'][0]['segmentation_id'] = ['42']

        self.neutronclient.post = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: fake_l2gw})
        l2gw_device = fake_l2gw['devices'][0]
        l2gw_interface = l2gw_device['interfaces'][0]
        arg_list = [
            '--device', 'name=' + l2gw_device['device_name'] +
            ',interface_names=' + l2gw_interface['name'] + '|' +
            '#'.join(l2gw_interface['segmentation_id']),
            fake_l2gw['name']
        ]

        verify_list = [
            ('devices', [
                {'interface_names': l2gw_device['interfaces'][0]['name'] +
                 '|' + '#'.join(l2gw_interface['segmentation_id']),
                 'name': l2gw_device['device_name']}]),
            ('name', fake_l2gw['name']),
        ]

        self._assert_create_succeeded(fake_l2gw, arg_list, verify_list)

    def test_create_l2gateway_with_mul_segmentation_id(self):
        """Test Create l2gateway with multiple segmentation-ids."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()
        fake_l2gw['devices'][0]['interfaces'][0]['segmentation_id'] = ['42',
                                                                       '43']

        self.neutronclient.post = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: fake_l2gw})
        l2gw_device = fake_l2gw['devices'][0]
        l2gw_interface = l2gw_device['interfaces'][0]
        arg_list = [
            '--device', 'name=' + l2gw_device['device_name'] +
            ',interface_names=' + l2gw_interface['name'] + '|' +
            '#'.join(l2gw_interface['segmentation_id']),
            fake_l2gw['name'],
        ]

        verify_list = [
            ('devices', [
                {'interface_names': l2gw_device['interfaces'][0]['name'] +
                 '|' + '#'.join(l2gw_interface['segmentation_id']),
                 'name': l2gw_device['device_name']}]),
            ('name', fake_l2gw['name']),
        ]

        self._assert_create_succeeded(fake_l2gw, arg_list, verify_list)


class TestListL2gw(test_fakes.TestNeutronClientOSCV2):
    def setUp(self):
        super(TestListL2gw, self).setUp()
        self.cmd = osc_l2gw.ListL2gw(self.app, self.namespace)

    def test_list_l2gateway(self):
        """Test List l2gateways."""

        fake_l2gws = fakes.FakeL2GW.create_l2gws(count=4)
        self.neutronclient.list = mock.Mock(return_value=fake_l2gws)
        arg_list = []
        verify_list = []

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)

        headers, data = self.cmd.take_action(parsed_args)

        self.neutronclient.list.assert_called_once()
        self.assertEqual(headers, list(headers_long))
        self.assertListItemEqual(
            list(data),
            [_get_data(fake_l2gw, columns_long) for fake_l2gw
             in fake_l2gws[osc_l2gw.L2_GATEWAYS]]
        )


class TestDeleteL2gw(test_fakes.TestNeutronClientOSCV2):
    def setUp(self):
        super(TestDeleteL2gw, self).setUp()
        self.neutronclient.find_resource = mock.Mock(
            side_effect=lambda _, name_or_id: {'id': name_or_id})
        self.cmd = osc_l2gw.DeleteL2gw(self.app, self.namespace)

    def test_delete_l2gateway(self):
        """Test Delete l2gateway."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()
        self.neutronclient.delete = mock.Mock()

        arg_list = [
            fake_l2gw['id'],
        ]
        verify_list = [
            (osc_l2gw.L2_GATEWAYS, [fake_l2gw['id']]),
        ]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)

        result = self.cmd.take_action(parsed_args)

        self.neutronclient.delete.assert_called_once_with(
            osc_l2gw.resource_path % fake_l2gw['id'])
        self.assertIsNone(result)


class TestShowL2gw(test_fakes.TestNeutronClientOSCV2):
    def setUp(self):
        super(TestShowL2gw, self).setUp()
        self.neutronclient.find_resource = mock.Mock(
            side_effect=lambda _, name_or_id: {'id': name_or_id})
        self.cmd = osc_l2gw.ShowL2gw(self.app, self.namespace)

    def test_show_l2gateway(self):
        """Test Show l2gateway: --fields id --fields name myid."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()
        self.neutronclient.get = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: fake_l2gw})
        arg_list = [
            fake_l2gw['id'],
        ]
        verify_list = [
            (osc_l2gw.L2_GATEWAY, fake_l2gw['id']),
        ]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)

        headers, data = self.cmd.take_action(parsed_args)

        self.neutronclient.get.assert_called_once_with(
            osc_l2gw.resource_path % fake_l2gw['id'])
        self.assertEqual(sorted_headers, headers)
        self.assertItemEqual(_get_data(fake_l2gw), data)


class TestUpdateL2gw(test_fakes.TestNeutronClientOSCV2):
    _new_device_name = 'new_device'
    _new_interface = 'new_interface'
    _new_name = 'new_name'

    columns = (
        'Devices',
        'ID',
        'Name',
        'Tenant'
    )

    def setUp(self):
        super(TestUpdateL2gw, self).setUp()
        self.cmd = osc_l2gw.UpdateL2gw(self.app, self.namespace)
        self.neutronclient.find_resource = mock.Mock(
            side_effect=lambda _, name_or_id: {'id': name_or_id})

    def _assert_update_succeeded(self, new_l2gw, attrs, columns, data):
        self.neutronclient.put.assert_called_once_with(
            osc_l2gw.resource_path % new_l2gw['id'],
            {osc_l2gw.L2_GATEWAY: attrs})
        self.assertEqual(self.columns, columns)
        self.assertItemEqual(_get_data(new_l2gw), data)

    def test_update_l2gateway(self):
        """Test Update l2gateway."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()
        new_l2gw = copy.deepcopy(fake_l2gw)
        new_l2gw['name'] = self._new_name
        new_l2gw['devices'][0]['device_name'] = self._new_device_name
        new_l2gw['devices'][0]['interfaces'][0]['name'] = self._new_interface

        self.neutronclient.put = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: new_l2gw})

        arg_list = [
            fake_l2gw['id'],
            '--name', self._new_name,
            '--device', 'name=' + self._new_device_name +
                        ',interface_names=' + self._new_interface,
        ]
        verify_list = [
            ('name', self._new_name),
            ('devices', [
                {'interface_names': self._new_interface,
                 'name': self._new_device_name}]),
        ]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)
        columns, data = self.cmd.take_action(parsed_args)
        attrs = {
            'name': self._new_name,
            'devices': [
                {'interfaces': [
                    {'name': self._new_interface}],
                 'device_name': self._new_device_name}
            ]
        }

        self._assert_update_succeeded(new_l2gw, attrs, columns, data)

    def test_update_l2gateway_name(self):
        """Test Update l2gateway name."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()
        new_l2gw = copy.deepcopy(fake_l2gw)
        new_l2gw['name'] = self._new_name

        self.neutronclient.put = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: new_l2gw})

        arg_list = [
            fake_l2gw['id'],
            '--name', self._new_name,
        ]
        verify_list = [('name', self._new_name)]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)
        columns, data = self.cmd.take_action(parsed_args)
        attrs = {'name': self._new_name}

        self._assert_update_succeeded(new_l2gw, attrs, columns, data)

    def test_update_l2gateway_with_multiple_interfaces(self):
        """Test Update l2gateway with multiple interfaces."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()
        new_l2gw = copy.deepcopy(fake_l2gw)
        new_l2gw['devices'][0]['interfaces'].append(
            {'name': self._new_interface})

        self.neutronclient.put = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: new_l2gw})

        l2gw_device = new_l2gw['devices'][0]
        l2gw_interface_1 = l2gw_device['interfaces'][0]
        l2gw_interface_2 = l2gw_device['interfaces'][1]
        arg_list = [
            fake_l2gw['id'],
            '--device', 'name=' + l2gw_device['device_name'] +
                        ',interface_names=' + l2gw_interface_1['name'] + ';' +
                        l2gw_interface_2['name']
        ]

        verify_list = [
            ('devices', [
                {
                    'interface_names':
                        l2gw_interface_1['name'] + ';' +
                        l2gw_interface_2['name'],
                    'name': l2gw_device['device_name']
                }
            ]),
        ]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)
        columns, data = self.cmd.take_action(parsed_args)
        attrs = {
            'devices': [
                {'device_name': l2gw_device['device_name'],
                 'interfaces': [
                     {'name': l2gw_interface_1['name']},
                     {'name': self._new_interface}]}
            ]
        }

        self._assert_update_succeeded(new_l2gw, attrs, columns, data)

    def test_update_l2gateway_with_segmentation_id(self):
        """Test Update l2gateway with segmentation-id."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()

        new_l2gw = copy.deepcopy(fake_l2gw)
        new_l2gw['devices'][0]['interfaces'][0]['segmentation_id'] = ['42']

        self.neutronclient.put = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: new_l2gw})

        l2gw_device = new_l2gw['devices'][0]
        l2gw_interface = l2gw_device['interfaces'][0]
        arg_list = [
            fake_l2gw['id'],
            '--device', 'name=' + l2gw_device['device_name'] +
            ',interface_names=' + l2gw_interface['name'] + '|' +
            '#'.join(l2gw_interface['segmentation_id']),
        ]

        verify_list = [
            ('devices', [
                {'interface_names': l2gw_device['interfaces'][0]['name'] +
                 '|' + '#'.join(l2gw_interface['segmentation_id']),
                 'name': l2gw_device['device_name']}]),
        ]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)
        columns, data = self.cmd.take_action(parsed_args)
        attrs = {
            'devices': [
                {'device_name': l2gw_device['device_name'],
                 'interfaces': [
                     {'name': l2gw_interface['name'],
                      'segmentation_id': l2gw_interface['segmentation_id']}]
                 }
            ]
        }

        self._assert_update_succeeded(new_l2gw, attrs, columns, data)

    def test_update_l2gateway_with_mul_segmentation_ids(self):
        """Test Update l2gateway with multiple segmentation-ids."""

        fake_l2gw = fakes.FakeL2GW.create_l2gw()

        new_l2gw = copy.deepcopy(fake_l2gw)
        new_l2gw['devices'][0]['interfaces'][0]['segmentation_id'] = ['42',
                                                                      '43']
        self.neutronclient.put = mock.Mock(
            return_value={osc_l2gw.L2_GATEWAY: new_l2gw})

        l2gw_device = new_l2gw['devices'][0]
        l2gw_interface = l2gw_device['interfaces'][0]
        arg_list = [
            fake_l2gw['id'],
            '--device', 'name=' + l2gw_device['device_name'] +
            ',interface_names=' + l2gw_interface['name'] + '|' +
            '#'.join(l2gw_interface['segmentation_id']),
        ]

        verify_list = [
            ('devices', [
                {'interface_names': l2gw_device['interfaces'][0]['name'] +
                 '|' + '#'.join(l2gw_interface['segmentation_id']),
                 'name': l2gw_device['device_name']}]),
        ]

        parsed_args = self.check_parser(self.cmd, arg_list, verify_list)
        columns, data = self.cmd.take_action(parsed_args)
        attrs = {
            'devices': [
                {'device_name': l2gw_device['device_name'],
                 'interfaces': [
                     {'name': l2gw_interface['name'],
                      'segmentation_id': l2gw_interface['segmentation_id']}]
                 }
            ]
        }

        self._assert_update_succeeded(new_l2gw, attrs, columns, data)
