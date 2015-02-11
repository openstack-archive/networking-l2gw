# Copyright (c) 2015 OpenStack Foundation.
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
from contextlib import contextmanager

import eventlet

from neutron.i18n import _LE
from neutron.i18n import _LW
from neutron.openstack.common import log as logging
from neutron.openstack.common import periodic_task

from networking_l2gw.services.l2gateway.agent import base_agent_manager
from networking_l2gw.services.l2gateway.agent import l2gateway_config
from networking_l2gw.services.l2gateway.agent.ovsdb import connection
from networking_l2gw.services.l2gateway.common import constants as n_const

from oslo.config import cfg
from oslo_utils import excutils

LOG = logging.getLogger(__name__)


class OVSDBManager(base_agent_manager.BaseAgentManager):
    """OVSDB variant of agent manager.

       Listens to state change notifications from OVSDB servers and
       handles transactions (RPCs) destined to OVSDB servers.
    """
    def __init__(self, conf=None):
        super(OVSDBManager, self).__init__(conf)
        self._extract_ovsdb_config(conf)

    def _extract_ovsdb_config(self, conf):
        self.conf = conf.ovsdb or cfg.CONF.ovsdb
        ovsdb_hosts = self.conf.ovsdb_hosts
        if ovsdb_hosts != '':
            ovsdb_hosts = ovsdb_hosts.split(',')
            for host in ovsdb_hosts:
                self._process_ovsdb_host(host)

    def _process_ovsdb_host(self, host):
        try:
            host_splits = str(host).split(':')
            ovsdb_identifier = str(host_splits[0]).strip()
            ovsdb_conf = {n_const.OVSDB_IDENTIFIER: ovsdb_identifier,
                          'ovsdb_ip': str(host_splits[1]).strip(),
                          'ovsdb_port': str(host_splits[2]).strip()}
            priv_key_path = self.conf.l2_gw_agent_priv_key_base_path
            cert_path = self.conf.l2_gw_agent_cert_base_path
            ca_cert_path = self.conf.l2_gw_agent_ca_cert_base_path
            use_ssl = priv_key_path and cert_path and ca_cert_path
            if use_ssl:
                ssl_ovsdb = {'use_ssl': True,
                             'private_key':
                                 "/".join([str(priv_key_path),
                                           '.'.join([str(host_splits[0]).
                                                     strip(),
                                                     'key'])]),
                             'certificate':
                                 "/".join([str(cert_path),
                                           '.'.join([str(host_splits[0]).
                                                     strip(), 'cert'])]),
                             'ca_cert':
                                 "/".join([str(ca_cert_path),
                                           '.'.join([str(host_splits[0]).
                                                     strip(), 'ca_cert'])])
                             }
                ovsdb_conf.update(ssl_ovsdb)
            LOG.debug("ovsdb_conf = %s", str(ovsdb_conf))
            gateway = l2gateway_config.L2GatewayConfig(ovsdb_conf)
            self.gateways[ovsdb_identifier] = gateway
        except Exception as ex:
            LOG.exception(_LE("Exception %(ex)s occurred while processing "
                              "host %(host)s"), {'ex': ex, 'host': host})

    @periodic_task.periodic_task(run_immediately=True)
    def _connect_to_ovsdb_server(self, context):
        """Initializes the connection to the OVSDB servers."""
        if self.gateways and n_const.MONITOR in self.l2gw_agent_type:
            for key in self.gateways.keys():
                gateway = self.gateways.get(key)
                ovsdb_fd = gateway.ovsdb_fd
                if not (ovsdb_fd and ovsdb_fd.connected):
                    LOG.debug("OVSDB server %s is disconnected",
                              str(gateway.ovsdb_ip))
                    try:
                        ovsdb_fd = connection.OVSDBConnection(self.conf,
                                                              gateway,
                                                              True,
                                                              self.plugin_rpc)
                    except Exception:
                        with excutils.save_and_reraise_exception(reraise=False
                                                                 ):
                            # Log a warning and continue so that it can retried
                            # in the next iteration
                            LOG.warning(_LW("OVSDB server %s is not "
                                            "reachable"), gateway.ovsdb_ip)
                    gateway.ovsdb_fd = ovsdb_fd
                    eventlet.greenthread.spawn_n(ovsdb_fd.
                                                 set_monitor_response_handler)

    @contextmanager
    def _open_connection(self, ovsdb_identifier):
        ovsdb_fd = None
        gateway = self.gateways.get(ovsdb_identifier)
        try:
            ovsdb_fd = connection.OVSDBConnection(self.conf,
                                                  gateway,
                                                  False,
                                                  self.plugin_rpc)
            yield ovsdb_fd
        finally:
            if ovsdb_fd:
                ovsdb_fd.disconnect()

    def _is_valid_request(self, ovsdb_identifier):
        val_req = ovsdb_identifier and ovsdb_identifier in self.gateways.keys()
        if not val_req:
            LOG.warning(n_const.ERROR_DICT
                        [n_const.L2GW_INVALID_OVSDB_IDENTIFIER])
        return val_req

    def delete_network(self, context, record_dict):
        """Handle RPC cast from plugin to delete a network."""
        ovsdb_identifier = record_dict.get(n_const.OVSDB_IDENTIFIER, None)
        if self._is_valid_request(ovsdb_identifier):
            with self._open_connection(ovsdb_identifier) as ovsdb_fd:
                ovsdb_fd.delete_logical_switch(record_dict)

    def add_vif_to_gateway(self, context, record_dict):
        """Handle RPC cast from plugin to insert neutron port MACs."""
        ovsdb_identifier = record_dict.get(n_const.OVSDB_IDENTIFIER, None)
        if self._is_valid_request(ovsdb_identifier):
            with self._open_connection(ovsdb_identifier) as ovsdb_fd:
                ovsdb_fd.insert_ucast_macs_remote(record_dict)

    def delete_vif_from_gateway(self, context, record_dict):
        """Handle RPC cast from plugin to delete neutron port MACs."""
        ovsdb_identifier = record_dict.get(n_const.OVSDB_IDENTIFIER, None)
        if self._is_valid_request(ovsdb_identifier):
            with self._open_connection(ovsdb_identifier) as ovsdb_fd:
                ovsdb_fd.delete_ucast_macs_remote(record_dict)

    def update_connection_to_gateway(self, context, record_dict):
        """Handle RPC cast from plugin.

        Handle RPC cast from plugin to connect/disconnect a network
        to/from an L2 gateway.
        """
        ovsdb_identifier = record_dict.get(n_const.OVSDB_IDENTIFIER, None)
        if self._is_valid_request(ovsdb_identifier):
            with self._open_connection(ovsdb_identifier) as ovsdb_fd:
                ovsdb_fd.update_connection_to_gateway(record_dict)
