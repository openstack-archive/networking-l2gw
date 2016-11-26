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

import abc

from neutron_lib.api import extensions as api_extensions
from neutron_lib.api import validators

from neutron.api import extensions
from neutron.api.v2 import resource_helper

from networking_l2gw import extensions as l2gw_extensions
from networking_l2gw.services.l2gateway.common import constants
from networking_l2gw.services.l2gateway.common import l2gw_validators

extensions.append_api_extensions_path(l2gw_extensions.__path__)

RESOURCE_ATTRIBUTE_MAP = {
    constants.L2_GATEWAYS: {
        'id': {'allow_post': False, 'allow_put': False,
               'is_visible': True},
        'name': {'allow_post': True, 'allow_put': True,
                 'validate': {'type:string': None},
                 'is_visible': True, 'default': ''},
        'devices': {'allow_post': True, 'allow_put': True,
                    'validate': {'type:l2gwdevice_list': None},
                    'is_visible': True},
        'tenant_id': {'allow_post': True, 'allow_put': False,
                      'validate': {'type:string': None},
                      'required_by_policy': True,
                      'is_visible': True}
    },
}

validators.add_validator('l2gwdevice_list',
                         l2gw_validators.validate_gwdevice_list)


class L2gateway(api_extensions.ExtensionDescriptor):

    """API extension for Layer-2 Gateway support."""

    @classmethod
    def get_name(cls):
        return "L2 Gateway"

    @classmethod
    def get_alias(cls):
        return "l2-gateway"

    @classmethod
    def get_description(cls):
        return "Connects Neutron networks with external networks at layer 2."

    @classmethod
    def get_updated(cls):
        return "2015-01-01T00:00:00-00:00"

    @classmethod
    def get_resources(cls):
        """Returns Ext Resources."""
        plural_mappings = resource_helper.build_plural_mappings(
            {}, RESOURCE_ATTRIBUTE_MAP)
        resources = resource_helper.build_resource_info(plural_mappings,
                                                        RESOURCE_ATTRIBUTE_MAP,
                                                        constants.L2GW)

        return resources

    def get_extended_resources(self, version):
        if version == "2.0":
            return RESOURCE_ATTRIBUTE_MAP
        else:
            return {}


class L2GatewayPluginBase(object):

    @abc.abstractmethod
    def create_l2_gateway(self, context, l2_gateway):
        pass

    @abc.abstractmethod
    def get_l2_gateway(self, context, id, fields=None):
        pass

    @abc.abstractmethod
    def delete_l2_gateway(self, context, id):
        pass

    @abc.abstractmethod
    def get_l2_gateways(self, context, filters=None, fields=None,
                        sorts=None, limit=None, marker=None,
                        page_reverse=False):
        pass

    @abc.abstractmethod
    def update_l2_gateway(self, context, id, l2_gateway):
        pass
