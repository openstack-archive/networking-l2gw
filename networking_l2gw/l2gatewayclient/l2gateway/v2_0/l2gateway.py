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

from neutronclient.common import utils
from neutronclient.i18n import _
from neutronclient.neutron import v2_0 as l2gatewayV20
from oslo.serialization import jsonutils


L2_GW = 'l2_gateway'


def _format_devices(l2_gateway):
    try:
        return '\n'.join([jsonutils.dumps(gateway) for gateway in
                          l2_gateway['devices']])
    except (TypeError, KeyError):
        return ''


class Listl2gateway(l2gatewayV20.ListCommand):
    """List l2gateways that belongs to a given tenant."""

    resource = L2_GW
    _formatters = {'devices': _format_devices, }
    list_columns = ['id', 'name', 'devices']
    pagination_support = True
    sorting_support = True


class Showl2gateway(l2gatewayV20.ShowCommand):
    """Show information of a given l2gateway."""

    resource = L2_GW


class Deletel2gateway(l2gatewayV20.DeleteCommand):
    """Delete a given l2gateway."""

    resource = L2_GW


class Createl2gateway(l2gatewayV20.CreateCommand):
    """Create l2gateway information."""

    resource = L2_GW

    def add_known_arguments(self, parser):
        parser.add_argument(
            'name', metavar='<GATEWAY-NAME>',
            help=_('Descriptive name for logical gateway.'))
        parser.add_argument(
            '--device', metavar='name=name,interface_name=interface_name',
            action='append', dest='devices', type=utils.str2dict,
            help=_('names or identifiers of the	L2 gateways.'
                   '(This option can be repeated)'))

    def args2body(self, parsed_args):

        body = {'l2_gateway': {'name': parsed_args.name,
                               'devices': parsed_args.devices}, }
        return body


class Updatel2gateway(l2gatewayV20.UpdateCommand):
    """Update a given l2gateway."""

    resource = L2_GW
