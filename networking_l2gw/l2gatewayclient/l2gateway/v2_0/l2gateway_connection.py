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

from neutronclient.i18n import _
from neutronclient.neutron import v2_0 as l2gatewayV20

L2_GW_CONNECTION = 'l2_gateway_connection'


class Listl2gatewayConnection(l2gatewayV20.ListCommand):
    """List l2gateway-connections."""

    resource = L2_GW_CONNECTION
    list_columns = ['id', 'l2_gateway_id', 'network_id', 'segmentation_id']
    pagination_support = True
    sorting_support = True


class Showl2gatewayConnection(l2gatewayV20.ShowCommand):
    """Show information of a given l2gateway-connection."""

    resource = L2_GW_CONNECTION


class Deletel2gatewayConnection(l2gatewayV20.DeleteCommand):
    """Delete a given l2gateway-connection."""

    resource = L2_GW_CONNECTION


class Createl2gatewayConnection(l2gatewayV20.CreateCommand):
    """Create l2gateway-connection information."""

    resource = L2_GW_CONNECTION

    def add_known_arguments(self, parser):
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

    def args2body(self, parsed_args):

        body = {'l2_gateway_connection':
                {'l2_gateway_id': parsed_args.gateway_name,
                 'network_id': parsed_args.network,
                 'segmentation_id': parsed_args.seg_id}}
        return body


class Updatel2gatewayConnection(l2gatewayV20.UpdateCommand):
    """Update a given l2gateway-connection."""

    resource = L2_GW_CONNECTION
