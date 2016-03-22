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


class L2RemoteGateway(extension.NeutronClientExtension):
    resource = 'l2_remote_gateway'
    resource_plural = 'l2_remote_gateways'
    path = 'l2-remote-gateways'
    object_path = '/%s' % path
    resource_path = '/%s/%%s' % path
    versions = ['2.0']


class L2RemoteGatewaysList(extension.ClientExtensionList, L2RemoteGateway):
    """List remote gateways."""

    shell_command = 'l2-remote-gateway-list'
    list_columns = ['id', 'name', 'ipaddr']
    pagination_support = True
    sorting_support = True


class L2RemoteGatewayCreate(extension.ClientExtensionCreate, L2RemoteGateway):
    """Create remote gateway information."""

    shell_command = 'l2-remote-gateway-create'

    def add_known_arguments(self, parser):
        parser.add_argument(
            'name', metavar='<REMOTE-GATEWAY-NAME>',
            help=_('Descriptive name for remote gateway.'))
        parser.add_argument(
            'ipaddr', metavar='<IP-ADDRESS>',
            help=_('IP Address of the remote gateway.'))

    def args2body(self, parsed_args):
        body = {'l2_remote_gateway': {'name': parsed_args.name,
                                      'ipaddr': parsed_args.ipaddr}, }
        return body


class L2RemoteGatewayShow(extension.ClientExtensionShow, L2RemoteGateway):
    """Show information of a given remote gateway."""

    shell_command = 'l2-remote-gateway-show'


class L2RemoteGatewayDelete(extension.ClientExtensionDelete, L2RemoteGateway):
    """Delete a given remote gateway."""

    shell_command = 'l2-remote-gateway-delete'


class L2RemoteGatewayUpdate(extension.ClientExtensionUpdate, L2RemoteGateway):
    """Update a given remote gateway."""

    shell_command = 'l2-remote-gateway-update'

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--name', metavar='name',
            help=_('Descriptive name of remote gateway.'))
        parser.add_argument(
            '--ipaddr', metavar='ipaddr',
            help=_('IP address of remote gateway.'))

    def args2body(self, parsed_args):
        params = {}
        body = {'l2_remote_gateway': params}

        if parsed_args.name:
            params['name'] = parsed_args.name
        if parsed_args.ipaddr:
            params['ipaddr'] = parsed_args.ipaddr

        return body
