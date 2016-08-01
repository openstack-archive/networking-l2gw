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

from neutronclient.common import extension
from neutronclient.neutron import v2_0 as l2gatewayV20

from networking_l2gw._i18n import _


class L2GatewayConnection(extension.NeutronClientExtension):
    resource = 'l2_gateway_connection'
    resource_plural = 'l2_gateway_connections'
    path = 'l2-gateway-connections'
    object_path = '/%s' % path
    resource_path = '/%s/%%s' % path
    versions = ['2.0']


class L2GatewayConnectionCreate(extension.ClientExtensionCreate,
                                L2GatewayConnection):
    """Create l2gateway-connection information."""

    shell_command = 'l2-gateway-connection-create'

    def retrieve_ids(self, client, args):
        gateway_id = l2gatewayV20.find_resourceid_by_name_or_id(
            client, 'l2_gateway', args.gateway_name)
        network_id = l2gatewayV20.find_resourceid_by_name_or_id(
            client, 'network', args.network)
        return (gateway_id, network_id)

    def get_parser(self, parser):
        parser = super(l2gatewayV20.CreateCommand,
                       self).get_parser(parser)
        parser.add_argument(
            'gateway_name', metavar='<GATEWAY-NAME/UUID>',
            help=_('Descriptive name for logical gateway.'))
        parser.add_argument(
            'network', metavar='<NETWORK-NAME/UUID>',
            help=_('Network name or uuid.'))
        parser.add_argument(
            '--default-segmentation-id',
            dest='seg_id',
            help=_('default segmentation-id that will '
                   'be applied to the interfaces for which '
                   'segmentation id was not specified '
                   'in l2-gateway-create command.'))
        return parser

    def args2body(self, args):

        neutron_client = self.get_client()
        (gateway_id, network_id) = self.retrieve_ids(neutron_client,
                                                     args)

        body = {'l2_gateway_connection':
                {'l2_gateway_id': gateway_id,
                 'network_id': network_id}}
        if args.seg_id:
            body['l2_gateway_connection']['segmentation_id'] = args.seg_id

        return body


class L2GatewayConnectionList(extension.ClientExtensionList,
                              L2GatewayConnection):
    """List l2gateway-connections."""

    shell_command = 'l2-gateway-connection-list'
    list_columns = ['id', 'l2_gateway_id', 'network_id', 'segmentation_id']
    pagination_support = True
    sorting_support = True


class L2GatewayConnectionShow(extension.ClientExtensionShow,
                              L2GatewayConnection):
    """Show information of a given l2gateway-connection."""

    shell_command = 'l2-gateway-connection-show'
    allow_names = False


class L2GatewayConnectionDelete(extension.ClientExtensionDelete,
                                L2GatewayConnection):
    """Delete a given l2gateway-connection."""

    shell_command = 'l2-gateway-connection-delete'
    allow_names = False
