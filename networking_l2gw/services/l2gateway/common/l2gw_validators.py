# Copyright 2015 OpenStack Foundation
# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from neutron.api.v2 import attributes
from neutron.common import exceptions

from networking_l2gw.services.l2gateway.common import constants

ALLOWED_CONNECTION_ATTRIBUTES = set((constants.NETWORK_ID,
                                     constants.SEG_ID,
                                     constants.L2GATEWAY_ID
                                     ))


def validate_gwdevice_list(data, valid_values=None):
    """Validate the list of devices."""
    if not data:
        # Devices must be provided
        msg = _("Cannot create a gateway with an empty device list")
        return msg
    try:
        for device in data:
            interface_data = device.get(constants.IFACE_NAME_ATTR)
            device_name = device.get(constants.DEVICE_ID_ATTR)
            if not interface_data:
                msg = _("Cannot create a gateway with an empty interfaces")
                return msg
            if not device_name:
                msg = _("Cannot create a gateway with an empty device_name")
                return msg
            for int_dict in interface_data:
                err_msg = attributes._validate_dict(int_dict, None)
                if not int_dict.get('name'):
                    msg = _("Cannot create a gateway with an empty"
                            "interface name")
                    return msg
                segmentation_id_list = int_dict.get(constants.SEG_ID)
                if type(segmentation_id_list) is not list:
                    msg = _("segmentation_id type should be of list type ")
                    return msg
                if not segmentation_id_list:
                    msg = _("segmentation_id_list should not be empty")
                    return msg
                if err_msg:
                    return err_msg
    except TypeError:
        return (_("%s: provided data are not iterable") %
                validate_gwdevice_list.__name__)


def validate_network_mapping_list(network_mapping, check_vlan):
    """Validate network mapping list in connection."""
    if not network_mapping.get('segmentation_id'):
        if check_vlan is False:
            raise exceptions.InvalidInput(
                error_message=_("Segmentation id must be specified in create"
                                "l2gateway connections"))
    network_id = network_mapping.get(constants.NETWORK_ID)
    if not network_id:
        raise exceptions.InvalidInput(
            error_message=_("A valid network identifier must be specified "
                            "when connecting a network to a network "
                            "gateway. Unable to complete operation"))
    connection_attrs = set(network_mapping.keys())
    if not connection_attrs.issubset(ALLOWED_CONNECTION_ATTRIBUTES):
        raise exceptions.InvalidInput(
            error_message=(_("Invalid keys found among the ones provided "
                             "in request : %(connection_attrs)s."),
                           connection_attrs))
    seg_id = network_mapping.get(constants.SEG_ID)
    if seg_id:
        if int(seg_id) < 0 or int(seg_id) > 4095:
            msg = _("Segmentation id is invalid")
            raise exceptions.InvalidInput(error_message=msg)
    return network_id
