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

from oslo_config import cfg

from networking_l2gw._i18n import _


OVSDB_OPTS = [
    cfg.StrOpt('ovsdb_hosts',
               default='host1:127.0.0.1:6632',
               help=_("OVSDB server name:host/IP:port")),
    cfg.StrOpt('l2_gw_agent_priv_key_base_path',
               help=_('L2 gateway agent private key')),
    cfg.StrOpt('l2_gw_agent_cert_base_path',
               help=_('L2 gateway agent public certificate')),
    cfg.StrOpt('l2_gw_agent_ca_cert_base_path',
               help=_('Trusted issuer CA cert')),
    cfg.IntOpt('periodic_interval',
               default=20,
               help=_('Seconds between periodic task runs')),
    cfg.IntOpt('socket_timeout',
               default=30,
               help=_('Socket timeout in seconds. '
                      'If there is no echo request on the socket for '
                      'socket_timeout seconds, the agent can safely '
                      'assume that the connection with the remote '
                      'OVSDB server is lost')),
    cfg.BoolOpt('enable_manager',
                default=False,
                help=_('Set to True if ovsdb Manager manages the client')),
    cfg.PortOpt('manager_table_listening_port',
                default=6632,
                help=_('Set port number for l2gw agent, so that it can '
                       'listen to whenever its IP is entered in manager '
                       'table of ovsdb server, For Ex: tcp:x.x.x.x:6640, '
                       'where x.x.x.x is IP of l2gw agent')),
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
                      '-1 for unlimited')),
    cfg.IntOpt('periodic_monitoring_interval',
               default=5,
               help=_('Periodic interval at which the plugin '
                      'checks for the monitoring L2 gateway agent')),
    cfg.StrOpt('l2gw_callback_class',
               default='networking_l2gw.services.l2gateway.ovsdb.'
                       'data.L2GatewayOVSDBCallbacks',
               help=_('L2 gateway plugin callback class where the '
                      'RPCs from the agent are going to get invoked'))
]


def register_l2gw_opts_helper():
    cfg.CONF.register_opts(L2GW_OPTS)


def register_ovsdb_opts_helper(conf):
    conf.register_opts(OVSDB_OPTS, 'ovsdb')


# add a logging setup method here for convenience
setup_logging = config.setup_logging
