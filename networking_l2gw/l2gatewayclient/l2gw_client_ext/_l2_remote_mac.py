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


class L2RemoteMac(extension.NeutronClientExtension):
    resource = 'l2_remote_mac'
    resource_plural = 'l2_remote_macs'
    path = 'l2-remote-macs'
    object_path = '/%s' % path
    resource_path = '/%s/%%s' % path
    versions = ['2.0']


class L2RemoteMacList(extension.ClientExtensionList,
                      L2RemoteMac):

    shell_command = 'l2-remote-mac-list'
    list_columns = ['uuid', 'mac', 'ipaddr', 'rgw_connection']
    pagination_support = True
    sorting_support = True


class L2RemoteMacCreate(extension.ClientExtensionCreate,
                        L2RemoteMac):

    shell_command = 'l2-remote-mac-create'

    def add_known_arguments(self, parser):
        parser.add_argument(
            'mac', metavar='<MAC>',
            help=_('MAC address of remote host'))
        parser.add_argument(
            'rgw_connection', metavar='<REMOTE-GATEWAY-CONN-UUID>',
            help=_('Remote Gateway Connection UUID.'))
        parser.add_argument(
            '--ipaddr', metavar='ipaddr',
            help=_('Remote host IP address'))

    def args2body(self, parsed_args):
        body = {'l2_remote_mac': {
            'mac': parsed_args.mac,
            'rgw_connection': parsed_args.rgw_connection,
            'ipaddr': parsed_args.ipaddr},
            }
        return body


class L2RemoteMacShow(extension.ClientExtensionShow, L2RemoteMac):

    shell_command = 'l2-remote-mac-show'
    allow_names = False


class L2RemoteMacDelete(extension.ClientExtensionDelete, L2RemoteMac):

    shell_command = 'l2-remote-mac-delete'
    allow_names = False
