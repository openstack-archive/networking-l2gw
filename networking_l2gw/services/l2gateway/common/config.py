# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
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

from neutron.common import config
from neutron.openstack.common import log as logging

from oslo.config import cfg

LOG = logging.getLogger(__name__)

AGENT_STATE_OPTS = [
    cfg.FloatOpt('report_interval', default=30,
                 help=_('Seconds between nodes reporting state to server; '
                        'should be less than agent_down_time, best if it '
                        'is half or less than agent_down_time.'))
]

OVSDB_OPTS = [
    cfg.StrOpt('ovsdb_hosts',
               default='host1:127.0.0.1:6632',
               help=_("OVSDB server name:host/IP:port")),
    cfg.StrOpt('l2_gw_agent_priv_key_base_path',
               default=None,
               help=_('L2 gateway agent private key')),
    cfg.StrOpt('l2_gw_agent_cert_base_path',
               default=None,
               help=_('L2 gateway agent public certificate')),
    cfg.StrOpt('l2_gw_agent_ca_cert_base_path',
               default=None,
               help=_('Trusted issuer CA cert')),
    cfg.IntOpt('periodic_interval',
               default=20,
               help=_('Seconds between periodic task runs')),
    cfg.IntOpt('max_connection_retries',
               default=10,
               help=_('Maximum number of retries to open a socket '
                      'with the OVSDB server'))
]

L2GW_OPTS = [
    cfg.StrOpt('default_interface_name',
               default='FortyGigE1/0/1',
               help=_('default_interface_name of the l2 gateway')),
    cfg.StrOpt('default_device_name',
               default='Switch1',
               help=_('default_device_name of the l2 gateway')),
    cfg.IntOpt('quota_l2_gateway',
               default=5,
               help=_('Number of l2 gateways allowed per tenant, '
                      '-1 for unlimited'))
]


def register_l2gw_opts_helper():
    cfg.CONF.register_opts(L2GW_OPTS)


def register_ovsdb_opts_helper(conf):
    conf.register_opts(OVSDB_OPTS, 'ovsdb')


def register_agent_state_opts_helper(conf):
    conf.register_opts(AGENT_STATE_OPTS, 'AGENT')


# add a logging setup method here for convenience
setup_logging = config.setup_logging
