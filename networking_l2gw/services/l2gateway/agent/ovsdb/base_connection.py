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

import copy
import socket
import ssl
import time

import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import excutils

from neutron.i18n import _LE
from neutron.i18n import _LW

from networking_l2gw.services.l2gateway.common import constants as n_const

LOG = logging.getLogger(__name__)
OVSDB_UNREACHABLE_MSG = _LW('Unable to reach OVSDB server %s')
OVSDB_CONNECTED_MSG = 'Connected to OVSDB server %s'


class BaseConnection(object):
    """Connects to OVSDB server.

       Connects to an ovsdb server with/without SSL
       on a given host and TCP port.
    """
    def __init__(self, conf, gw_config):
        self.responses = []
        self.connected = False
        self.enable_manager = cfg.CONF.ovsdb.enable_manager
        if self.enable_manager:
            self.s = None
            self.check_c_sock = None
            self.check_sock_rcv = False
            eventlet.greenthread.spawn(self._rcv_socket)
            self.ovsdb_dicts = {}
            self.ovsdb_fd_states = {}
        else:
            self.gw_config = gw_config
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
                except (socket.error, socket.timeout):
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

    def _rcv_socket(self):
        # Create a socket object.
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = ''                  # Get local machine name
        port = 6632                # Reserve a port for your service.
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((host, port))        # Bind to the port
        self.s.listen(5)                 # Now wait for client connection.
        while True:
            # Establish connection with client.
            c_sock, ip_addr = self.s.accept()
            addr = ip_addr[0]
            c_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            LOG.debug("Got connection from %s ", addr)
            self.connected = True
            self.ovsdb_dicts[addr] = c_sock
            eventlet.greenthread.spawn(self._common_sock_rcv_thread, addr)

    def _common_sock_rcv_thread(self, addr):
        chunks = []
        lc = rc = 0
        prev_char = None
        self._echo_response(addr)
        if self.enable_manager and self.check_c_sock:
            while self.read_on:
                response = self.ovsdb_dicts.get(addr).recv(n_const.BUFFER_SIZE)
                self.ovsdb_fd_states[addr] = 'connected'
                eventlet.greenthread.sleep(0)
                self.check_sock_rcv = True
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
                            raise Exception(_LE("json string not valid"))
                        elif lc == rc and lc is not 0:
                            chunks.append(response[message_mark:i + 1])
                            message = "".join(chunks)
                            eventlet.greenthread.spawn_n(
                                self._on_remote_message, message, addr)
                            eventlet.greenthread.sleep(0)
                            lc = rc = 0
                            message_mark = i + 1
                            chunks = []
                        prev_char = c
                    chunks.append(response[message_mark:])
                else:
                    self.read_on = False
                    self.disconnect(addr)
                    self.ovsdb_fd_states[addr] = 'disconnected'

    def _echo_response(self, addr):
        while True:
            try:
                if self.enable_manager:
                    eventlet.greenthread.sleep(0)
                    response = self.ovsdb_dicts.get(addr).recv(
                        n_const.BUFFER_SIZE)
                    sock_json_m = jsonutils.loads(response)
                    sock_handler_method = sock_json_m.get('method', None)
                    if sock_handler_method == 'echo':
                        self.check_c_sock = True
                        self.ovsdb_dicts.get(addr).send(jsonutils.dumps(
                            {"result": sock_json_m.get("params", None),
                             "error": None, "id": sock_json_m['id']}))
                        break
            except Exception:
                continue

    def send(self, message, callback=None, addr=None):
        """Sends a message to the OVSDB server."""
        if callback:
            self.callbacks[message['id']] = callback
        retry_count = 0
        bytes_sent = 0
        while retry_count <= n_const.MAX_RETRIES:
            try:
                if self.enable_manager:
                    bytes_sent = self.ovsdb_dicts.get(addr).send(
                        jsonutils.dumps(message))
                else:
                    bytes_sent = self.socket.send(jsonutils.dumps(message))
                if bytes_sent:
                    return True
            except Exception as ex:
                LOG.exception(_LE("Exception [%s] occurred while sending "
                                  "message to the OVSDB server"), ex)
            retry_count += 1

        LOG.warning(_LW("Could not send message to the "
                        "OVSDB server."))
        self.disconnect(addr)
        return False

    def disconnect(self, addr=None):
        """disconnects the connection from the OVSDB server."""
        if self.enable_manager:
            self.ovsdb_dicts.get(addr).close()
            del self.ovsdb_dicts[addr]
        else:
            self.socket.close()
        self.connected = False

    def _response(self, operation_id):
        x_copy = None
        to_delete = None
        for x in self.responses:
            if x['id'] == operation_id:
                x_copy = copy.deepcopy(x)
                to_delete = x
                break
        if to_delete:
            self.responses.remove(to_delete)
        return x_copy
