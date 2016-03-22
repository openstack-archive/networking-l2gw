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


from neutronclient.common import extension
from neutronclient.i18n import _
from neutronclient.neutron import v2_0 as l2gatewayV20


class L2RemoteGatewayConnection(extension.NeutronClientExtension):
    resource = 'l2_remote_gateway_connection'
    resource_plural = 'l2_remote_gateway_connections'
    path = 'l2-remote-gateway-connections'
    object_path = '/%s' % path
    resource_path = '/%s/%%s' % path
    versions = ['2.0']


class L2RemoteGatewaysConnectionList(extension.ClientExtensionList,
                                     L2RemoteGatewayConnection):

    shell_command = 'l2-remote-gateway-connection-list'
    list_columns = ['id', 'gateway', 'network', 'remote_gateway',
                    'seg_id', 'flood']
    pagination_support = True
    sorting_support = True


class L2RemoteGatewayConnectionCreate(extension.ClientExtensionCreate,
                                      L2RemoteGatewayConnection):

    shell_command = 'l2-remote-gateway-connection-create'

    @staticmethod
    def retrieve_ids(client, args):
        gateway_id = l2gatewayV20.find_resourceid_by_name_or_id(
            client, 'l2_gateway', args.gateway)
        remote_gateway_id = l2gatewayV20.find_resourceid_by_name_or_id(
            client, 'l2_remote_gateway', args.remote_gateway)
        network_id = l2gatewayV20.find_resourceid_by_name_or_id(
            client, 'network', args.network)
        return gateway_id, remote_gateway_id, network_id

    def add_known_arguments(self, parser):
        parser.add_argument(
            'gateway', metavar='<GATEWAY-NAME/UUID>',
            help=_('Descriptive name/UUID for local gateway.'))
        parser.add_argument(
            'network', metavar='<NETWORK-NAME/UUID>',
            help=_('Name of local network to connect to the remote gateway'))
        parser.add_argument(
            'remote_gateway', metavar='<REMOTE-GATEWAY-NAME/UUID>',
            help=_('Descriptive name/UUID for remote gateway.'))
        parser.add_argument(
            '--seg-id', metavar='seg_id',
            help=_('Segmentation ID for the connection to the remote gateway'))
        parser.add_argument(
            '--flood', metavar='flood',
            help=_('Whether to flood un-known MACs and broadcasts '
                   'to remote connection'))

    def args2body(self, parsed_args):

        neutron_client = self.get_client()
        gateway_id, remote_gateway_id, network_id = self.retrieve_ids(
            neutron_client, parsed_args)
        body = {'l2_remote_gateway_connection': {
            'gateway': gateway_id,
            'network': network_id,
            'remote_gateway': remote_gateway_id,
            'seg_id': parsed_args.seg_id,
            'flood': parsed_args.flood},
            }
        return body


class L2RemoteGatewayConnectionShow(extension.ClientExtensionShow,
                                    L2RemoteGatewayConnection):
    shell_command = 'l2-remote-gateway-connection-show'


class L2RemoteGatewayConnectionDelete(extension.ClientExtensionDelete,
                                      L2RemoteGatewayConnection):
    shell_command = 'l2-remote-gateway-connection-delete'
