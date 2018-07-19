# All Rights Reserved 2018
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

import copy

from oslo_utils import uuidutils

from networking_l2gw.l2gatewayclient.osc import l2gw as osc_l2gw
from networking_l2gw.l2gatewayclient.osc import l2gw_connection as \
    osc_l2gw_conn


class FakeL2GW(object):

    @staticmethod
    def create_l2gw(num_dev=1, num_if=1, attrs=None):
        """Create one fake L2 Gateway."""
        attrs = attrs or {}
        interfaces = [{'name': 'interface' +
                               uuidutils.generate_uuid(dashed=False)} for
                      iface in range(num_if)]
        devices = [{'device_name': 'device' +
                                   uuidutils.generate_uuid(dashed=False),
                    'interfaces': interfaces} for dev in range(num_dev)]
        l2gw_attrs = {
            'id': uuidutils.generate_uuid(),
            'name': 'test-l2gw' + uuidutils.generate_uuid(dashed=False),
            'tenant_id': uuidutils.generate_uuid(),
            'devices': devices
        }

        l2gw_attrs.update(attrs)
        return copy.deepcopy(l2gw_attrs)

    @staticmethod
    def create_l2gws(attrs=None, count=1):
        """Create multiple fake L2 Gateways."""

        l2gws = []
        for i in range(0, count):
            if attrs is None:
                attrs = {'id': 'fake_id%d' % i}
            elif getattr(attrs, 'id', None) is None:
                attrs['id'] = 'fake_id%d' % i
            l2gws.append(FakeL2GW.create_l2gw(attrs=attrs))

        return {osc_l2gw.L2_GATEWAYS: l2gws}


class FakeL2GWConnection(object):

    @staticmethod
    def create_l2gw_connection(attrs=None):
        """Create a fake l2gw connection."""

        attrs = attrs or {}
        l2gw_connection_attrs = {
            'network_id': uuidutils.generate_uuid(),
            'l2_gateway_id': uuidutils.generate_uuid(),
            'segmentation_id': '42',
            'tenant_id': uuidutils.generate_uuid(),
            'id': uuidutils.generate_uuid()
        }

        l2gw_connection_attrs.update(attrs)
        return copy.deepcopy(l2gw_connection_attrs)

    @staticmethod
    def create_l2gw_connections(attrs=None, count=1):
        l2gw_connections = []

        for i in range(0, count):
            if attrs is None:
                attrs = {'id': 'fake_id%d' % i}
            elif getattr(attrs, 'id', None) is None:
                attrs['id'] = 'fake_id%d' % i
            l2gw_connections.append(FakeL2GWConnection.create_l2gw_connection(
                attrs=attrs))

        return {osc_l2gw_conn.L2_GATEWAY_CONNECTIONS: l2gw_connections}
