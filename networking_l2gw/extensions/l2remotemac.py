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
from neutron.api import extensions
from neutron.api.v2 import attributes
from neutron.api.v2 import resource_helper

from networking_l2gw.services.l2gateway.common import constants

RESOURCE_ATTRIBUTE_MAP = {
    constants.L2_REMOTE_MACS: {
        'uuid': {'allow_post': False, 'allow_put': False,
                 'validate': {'type:uuid': None},
                 'is_visible': True,
                 'primary_key': True},
        'mac': {'allow_post': True, 'allow_put': True,
                'validate': {'type:string': None},
                'is_visible': True, 'default': ''},
        'ipaddr': {'allow_post': True, 'allow_put': True,
                   'validate': {'type:string': None},
                   'is_visible': True, 'default': ''},
        'rgw_connection': {'allow_post': True, 'allow_put': True,
                           'validate': {'type:string': None},
                           'is_visible': True, 'default': ''},
        'tenant_id': {'allow_post': True, 'allow_put': False,
                      'validate': {'type:string': None},
                      'required_by_policy': True,
                      'is_visible': True}
    },
}


class L2remotemac(extensions.ExtensionDescriptor):

    @classmethod
    def get_name(cls):
        return "L2 Remote MAC"

    @classmethod
    def get_alias(cls):
        return "l2-remote-mac"

    @classmethod
    def get_description(cls):
        return "MAC addresses of hosts reachable via remote gateway connection"

    @classmethod
    def get_updated(cls):
        return "2015-12-31T00:00:00-00:00"

    @classmethod
    def get_resources(cls):
        """Returns Ext Resources."""
        mem_actions = {}
        plural_mappings = resource_helper.build_plural_mappings(
            {}, RESOURCE_ATTRIBUTE_MAP)
        attributes.PLURALS.update(plural_mappings)
        resources = resource_helper.build_resource_info(plural_mappings,
                                                        RESOURCE_ATTRIBUTE_MAP,
                                                        constants.L2GW,
                                                        action_map=mem_actions,
                                                        register_quota=True,
                                                        translate_name=True)
        return resources

    def get_extended_resources(self, version):
        if version == "2.0":
            return RESOURCE_ATTRIBUTE_MAP
        else:
            return {}


class L2RemoteMacPluginBase(extensions.PluginInterface):

    @abc.abstractmethod
    def get_l2_remote_macs(self, context, filters=None,
                           fields=None,
                           sorts=None, limit=None, marker=None,
                           page_reverse=False):
        pass

    @abc.abstractmethod
    def get_l2_remote_mac(self, context, id, fields=None):
        pass

    @abc.abstractmethod
    def create_l2_remote_mac(self, context, remote_gateway_conn):
        pass

    @abc.abstractmethod
    def delete_l2_remote_mac(self, context, id):
        pass
