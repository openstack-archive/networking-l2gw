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

import eventlet

from neutron.i18n import _LE
from neutron.i18n import _LW
from neutron.openstack.common import log as logging
import random
import socket
import ssl
import time

from oslo.serialization import jsonutils
from oslo_utils import excutils

from networking_l2gw.services.l2gateway.common import constants as n_const

LOG = logging.getLogger(__name__)
OVSDB_UNREACHABLE_MSG = _LW('Unable to reach OVSDB server %s')
OVSDB_CONNECTED_MSG = 'Connected to OVSDB server %s'
BUFFER_SIZE = 4096


class OVSDBConnection(object):
    """Connects to OVSDB server.

       Connects to an ovsdb server with/without SSL
       on a given host and TCP port.
    """
    def __init__(self, conf, gw_config, is_monitor, plugin_rpc=None):
        self.responses = []
        self.connected = False
        self._reset_variables()
        self.gw_config = gw_config
        self.plugin_rpc = plugin_rpc
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if gw_config.use_ssl:
            ssl_sock = ssl.wrap_socket(
                self.socket,
                server_side=False,
                keyfile=gw_config.private_key,
                certfile=gw_config.certificate,
                cert_reqs=ssl.CERT_REQUIRED,
                ssl_version=ssl.PROTOCOL_TLSv1,
                ca_certs=gw_config.ca_cert)
            self.socket = ssl_sock

        retryCount = 0
        while True:
            try:
                self.socket.connect((str(gw_config.ovsdb_ip),
                                     int(gw_config.ovsdb_port)))
                break
            except socket.error:
                LOG.warning(OVSDB_UNREACHABLE_MSG, gw_config.ovsdb_ip)
                if retryCount == conf.max_connection_retries:
                    # Retried for max_connection_retries times.
                    # Give up and return so that it can be tried in
                    # the next periodic interval.
                    with excutils.save_and_reraise_exception(reraise=True):
                        LOG.exception(_LE("Socket error in connecting to "
                                          "the OVSDB server"))
                else:
                    time.sleep(1)
                    retryCount += 1

        # Successfully connected to the socket
        LOG.debug(OVSDB_CONNECTED_MSG, gw_config.ovsdb_ip)
        self.connected = True
        self.callbacks = {}
        self._setup_dispatch_table()
        if is_monitor:
            self.read_on = True
            eventlet.greenthread.spawn_n(self._rcv_thread)

    def _reset_variables(self):
        self.new_local_macs = []
        self.deleted_local_macs = []
        self.modified_local_macs = []
        self.new_remote_macs = []
        self.deleted_remote_macs = []
        self.modified_remote_macs = []
        self.new_physical_ports = []
        self.deleted_physical_ports = []
        self.modified_physical_ports = []
        self.new_physical_switches = []
        self.deleted_physical_switches = []
        self.modified_physical_switches = []
        self.new_physical_locators = []
        self.deleted_physical_locators = []
        self.modified_physical_locators = []
        self.new_logical_switches = []
        self.deleted_logical_switches = []
        self.modified_logical_switches = []
        self.new_mlocal_macs = []
        self.modified_mlocal_macs = []
        self.deleted_mlocal_macs = []
        self.new_locator_sets = []
        self.modified_locator_sets = []
        self.deleted_locator_sets = []

    def _setup_dispatch_table(self):
        self.dispatch_table = {'Physical_Port': self._process_physical_port,
                               'Physical_Switch':
                               self._process_physical_switch,
                               'Logical_Switch': self._process_logical_switch,
                               'Ucast_Macs_Local':
                               self._process_ucast_macs_local,
                               'Physical_Locator':
                               self._process_physical_locator,
                               'Ucast_Macs_Remote':
                               self._process_ucast_macs_remote,
                               'Mcast_Macs_Local':
                               self._process_mcast_macs_local,
                               'Physical_Locator_Set':
                               self._process_physical_locator_set
                               }

    def set_monitor_response_handler(self):
        """Monitor OVSDB tables to receive events for any changes in OVSDB."""
        if self.connected:
                op_id = str(random.getrandbits(128))
                props = {'select': {'initial': True,
                                    'insert': True,
                                    'delete': True,
                                    'modify': True}}
                monitor_message = {'id': op_id,
                                   'method': 'monitor',
                                   'params': [n_const.OVSDB_SCHEMA_NAME,
                                              None,
                                              {'Logical_Switch': [props],
                                               'Physical_Switch': [props],
                                               'Physical_Port': [props],
                                               'Ucast_Macs_Local': [props],
                                               'Ucast_Macs_Remote': [props],
                                               'Physical_Locator': [props],
                                               'Mcast_Macs_Local': [props],
                                               'Physical_Locator_Set': [props]}
                                              ]}
                if not self.send(monitor_message):
                    # Return so that this will retried in the next iteration
                    return

    def _update_event_handler(self, message):
        pass

    def _default_echo_handler(self, message):
        """Message handler for the OVSDB server's echo request."""
        pass

    def send(self, message, callback=None):
        """Sends a message to the OVSDB server."""
        if callback:
            self.callbacks[message['id']] = callback
        try:
            self.socket.send(jsonutils.dumps(message))
            return True
        except Exception as ex:
            self.connected = False
            LOG.exception(_LE("Exception [%s] occurred while sending message "
                              "to the OVSDB server"), ex)
            return False

    def _on_remote_message(self, message):
        """Processes the message received on the socket."""
        pass

    def _rcv_thread(self):
        chunks = []
        lc = rc = 0
        prev_char = None
        while self.read_on:
            try:
                response = self.socket.recv(BUFFER_SIZE)
                if response:
                    response = response.decode('utf8')
                    message_mark = 0
                    for i, c in enumerate(response):
                        if c == '{' and not (prev_char and
                                             prev_char == '\\'):
                            lc += 1
                        elif c == '}' and not (prev_char and
                                               prev_char == '\\'):
                            rc += 1
                        if rc > lc:
                            raise Exception(_("json string not valid"))
                        elif lc == rc and lc is not 0:
                            chunks.append(response[message_mark:i + 1])
                            message = "".join(chunks)
                            self._on_remote_message(message)
                            lc = rc = 0
                            message_mark = i + 1
                            chunks = []
                        prev_char = c
                    chunks.append(response[message_mark:])
                else:
                    self.connected = False
                    self.read_on = False
                    self.socket.close()
            except Exception as ex:
                self.connected = False
                self.read_on = False
                self.socket.close()
                LOG.exception(_LE("Exception [%s] occurred while receiving"
                                  "message from the OVSDB server"), ex)

    def disconnect(self):
        self.socket.close()

    def _process_monitor_msg(self, message):
        """Process initial set of records in the OVSDB at startup."""
        result_dict = message.get('result')
        self._reset_variables()
        port_map = {}
        try:
            for table_name in result_dict.keys():
                table_dict = result_dict.get(table_name)
                for uuid in table_dict.keys():
                    uuid_dict = table_dict.get(uuid)
                    self.dispatch_table.get(table_name)(uuid,
                                                        uuid_dict, port_map)
        except Exception as e:
            LOG.exception(_LE("_process_monitor_msg:ERROR %s "), e)
        self.plugin_rpc.update_ovsdb_changes(self._form_ovsdb_data())

    def _get_list(self, resource_list):
        return [element.__dict__ for element in resource_list]

    def _form_ovsdb_data(self):
        return {n_const.OVSDB_IDENTIFIER: self.gw_config.ovsdb_identifier,
                'new_logical_switches': self._get_list(
                    self.new_logical_switches),
                'new_physical_switches': self._get_list(
                    self.new_physical_switches),
                'new_physical_ports': self._get_list(
                    self.new_physical_ports),
                'new_physical_locators': self._get_list(
                    self.new_physical_locators),
                'new_local_macs': self._get_list(
                    self.new_local_macs),
                'new_remote_macs': self._get_list(
                    self.new_remote_macs),
                'new_mlocal_macs': self._get_list(
                    self.new_mlocal_macs),
                'new_locator_sets': self._get_list(
                    self.new_locator_sets),
                'deleted_logical_switches': self._get_list(
                    self.deleted_logical_switches),
                'deleted_physical_switches': self._get_list(
                    self.deleted_physical_switches),
                'deleted_physical_ports': self._get_list(
                    self.deleted_physical_ports),
                'deleted_physical_locators': self._get_list(
                    self.deleted_physical_locators),
                'deleted_local_macs': self._get_list(
                    self.deleted_local_macs),
                'deleted_remote_macs': self._get_list(
                    self.deleted_remote_macs),
                'deleted_mlocal_macs': self._get_list(
                    self.deleted_mlocal_macs),
                'deleted_locator_sets': self._get_list(
                    self.deleted_locator_sets),
                'modified_logical_switches': self._get_list(
                    self.modified_logical_switches),
                'modified_physical_switches': self._get_list(
                    self.modified_physical_switches),
                'modified_physical_ports': self._get_list(
                    self.modified_physical_ports),
                'modified_physical_locators': self._get_list(
                    self.modified_physical_locators),
                'modified_local_macs': self._get_list(
                    self.modified_local_macs),
                'modified_remote_macs': self._get_list(
                    self.modified_remote_macs),
                'modified_mlocal_macs': self._get_list(
                    self.modified_mlocal_macs),
                'modified_locator_sets': self._get_list(
                    self.modified_locator_sets)}

    def _process_physical_port(self, uuid, uuid_dict, port_map=None):
        """Processes Physical_Port record from the OVSDB event."""
        pass

    def _process_physical_switch(self, uuid, uuid_dict, port_map=None):
        """Processes Physical_Switch record from the OVSDB event."""
        pass

    def _process_logical_switch(self, uuid, uuid_dict, port_map=None):
        """Processes Logical_Switch record from the OVSDB event."""
        pass

    def _process_ucast_macs_local(self, uuid, uuid_dict, port_map=None):
        """Processes Ucast_Macs_Local record from the OVSDB event."""
        pass

    def _process_ucast_macs_remote(self, uuid, uuid_dict, port_map=None):
        """Processes Ucast_Macs_Remote record from the OVSDB event."""
        pass

    def _process_physical_locator(self, uuid, uuid_dict, port_map=None):
        """Processes Physical_Locator record from the OVSDB event."""
        pass

    def _process_mcast_macs_local(self, uuid, uuid_dict, port_map=None):
        """Processes Mcast_Macs_Local record from the OVSDB event."""
        pass

    def _process_physical_locator_set(self, uuid, uuid_dict, port_map=None):
        """Processes Physical_Locator_Set record from the OVSDB event."""
        pass

    def insert_logical_switch(self, record_dict):
        """Insert an entry in Logical_Switch OVSDB table."""
        pass

    def delete_logical_switch(self, record_dict):
        """Delete an entry from Logical_Switch OVSDB table."""
        pass

    def insert_ucast_macs_remote(self, record_dict):
        """Insert an entry in Ucast_Macs_Remote OVSDB table."""
        pass

    def delete_ucast_macs_remote(self, record_dict):
        """Delete an entry from Ucast_Macs_Remote OVSDB table."""
        pass

    def update_connection_to_gateway(self, request_dict):
        """Updates Physical Port's VNI to VLAN binding."""
        pass
