# Copyright (c) 2016 OpenStack Foundation
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

from neutron_lib import exceptions

from neutron.tests import base

from networking_l2gw.services.l2gateway.common import l2gw_validators


class TestL2gwValidators(base.BaseTestCase):

    def test_validate_gwdevice_list(self):
        ret_msg = l2gw_validators.validate_gwdevice_list(None)
        msg = "Cannot create a gateway with an empty device list"
        self.assertEqual(msg, ret_msg)

    def test_for_empty_device_name(self):
        test_device = [{"interfaces": "port"}]
        ret_msg = l2gw_validators.validate_gwdevice_list(test_device)
        msg = "Cannot create a gateway with an empty device_name"
        self.assertEqual(msg, ret_msg)

    def test_for_empty_interface(self):
        test_device = [{"device_name": "switch1"}]
        ret_msg = l2gw_validators.validate_gwdevice_list(test_device)
        msg = "Cannot create a gateway with an empty interfaces"
        self.assertEqual(msg, ret_msg)

    def test_for_interfaces_type_list_of_dicts(self):
        test_device = [{"device_name": "switch1", "interfaces": "port"}]
        ret_msg = l2gw_validators.validate_gwdevice_list(test_device)
        msg = "interfaces format is not a type list of dicts"
        self.assertEqual(msg, ret_msg)

    def test_for_interface_type_dict(self):
        test_device = [{"device_name": "switch1", "interfaces": ["port"]}]
        ret_msg = l2gw_validators.validate_gwdevice_list(test_device)
        msg = "interfaces format is not a type dict"
        self.assertEqual(msg, ret_msg)

    def test_for_empty_interface_name(self):
        test_device = [{"device_name": "switch1",
                        "interfaces": [{'name': ""}]}]
        ret_msg = l2gw_validators.validate_gwdevice_list(test_device)
        msg = "Cannot create a gateway with an empty interface name"
        self.assertEqual(msg, ret_msg)

    def test_segmentation_id_in_interface(self):
        test_device = [{"device_name": "switch1",
                        "interfaces": [{'name': "i1", 'segmentation_id': ''}]}]
        ret_msg = l2gw_validators.validate_gwdevice_list(test_device)
        msg = "segmentation_id_list should not be empty"
        self.assertEqual(msg, ret_msg)

    def test_segmentation_id_type(self):
        test_device = [{"device_name": "switch1",
                        "interfaces": [{'name': "i1",
                                        'segmentation_id': '67'}]}]
        ret_msg = l2gw_validators.validate_gwdevice_list(test_device)
        msg = "segmentation_id type should be of list type "
        self.assertEqual(msg, ret_msg)

    def test_validate_network_mapping_list_with_seg_id(self):
        network_mapping = {'segmentation_id': 67}
        check_vlan = True
        self.assertRaises(exceptions.InvalidInput,
                          l2gw_validators.validate_network_mapping_list,
                          network_mapping, check_vlan)

    def test_validate_network_mapping_list_without_seg_id(self):
        network_mapping = {'segmentation_id': ''}
        check_vlan = False
        self.assertRaises(exceptions.InvalidInput,
                          l2gw_validators.validate_network_mapping_list,
                          network_mapping, check_vlan)

    def test_validate_network_mapping_list_for_empty_network_id(self):
        network_mapping = {'segmentation_id': '', 'network_id': ''}
        check_vlan = True
        self.assertRaises(exceptions.InvalidInput,
                          l2gw_validators.validate_network_mapping_list,
                          network_mapping, check_vlan)

    def test_is_valid_vlan_id_for_non_integer_value(self):
        seg_id = 'a'
        self.assertRaises(exceptions.InvalidInput,
                          l2gw_validators.is_valid_vlan_id,
                          seg_id)

    def test_is_valid_vlan_id_for_value_less_than_0(self):
        seg_id = -1
        self.assertRaises(exceptions.InvalidInput,
                          l2gw_validators.is_valid_vlan_id,
                          seg_id)

    def test_is_valid_vlan_id_for_value_greater_than_4095(self):
        seg_id = 4096
        self.assertRaises(exceptions.InvalidInput,
                          l2gw_validators.is_valid_vlan_id,
                          seg_id)
