# Copyright 2015 OpenStack Foundation
# Copyright 2015 Hewlett-Packard Development Company, L.P.
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

import collections
import json
import logging
import random
import socket
import threading
import time

logging.basicConfig(level=logging.DEBUG)


def default_echo_handler(message, ovsconn):
    logging.debug("responding to echo")
    ovsconn.send({"result": message.get("params", None),
                  "error": None, "id": message['id']})


def default_message_handler(message, ovsconn):
    ovsconn.responses.append(message)


class OVSDBConnection(threading.Thread):
    """Connects to an ovsdb server that has manager set using

        ovs-vsctl set-manager ptcp:5000

        clients can make calls and register a callback for results, callbacks
         are linked based on the message ids.

        clients can also register methods which they are interested in by
        providing a callback.
    """

    def __init__(self, IP, PORT, **handlers):
        super(OVSDBConnection, self).__init__()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((IP, PORT))
        self.responses = []
        self.callbacks = {}
        self.read_on = True
        self.handlers = handlers or {"echo": default_echo_handler}
        self.start()

    def send(self, message, callback=None):
        if callback:
            self.callbacks[message['id']] = callback
        self.socket.send(json.dumps(message))

    def response(self, id):
        return [x for x in self.responses if x['id'] == id]

    def set_handler(self, method_name, handler):
        self.handlers[method_name] = handler

    def _on_remote_message(self, message):
        try:
            json_m = json.loads(message,
                                object_pairs_hook=collections.OrderedDict)
            handler_method = json_m.get('method', None)
            if handler_method:
                self.handlers.get(handler_method, default_message_handler)(
                    json_m, self)
            elif json_m.get("result", None) and json_m['id'] in self.callbacks:
                id = json_m['id']
                if not self.callbacks[id](json_m, self):
                    self.callbacks.pop(id)

            else:
                default_message_handler(message, self)
        except Exception as e:
            logging.exception(
                "exception [%s] in handling message [%s]", e.message, message)

    def __echo_response(message, self):
        self.send({"result": message.get("params", None),
                   "error": None, "id": message['id']})

    def run(self):

        chunks = []
        lc = rc = 0
        while self.read_on:
            try:
                response = self.socket.recv(4096)
                if response:
                    response = response.decode('utf8')
                    message_mark = 0
                    for i, c in enumerate(response):
                        if c == '{':
                            lc += 1
                        elif c == '}':
                            rc += 1

                        if rc > lc:
                            raise Exception("json string not valid")

                        elif lc == rc and lc is not 0:
                            chunks.append(response[message_mark:i + 1])
                            message = "".join(chunks)
                            self._on_remote_message(message)
                            lc = rc = 0
                            message_mark = i + 1
                            chunks = []

                    chunks.append(response[message_mark:])
            except Exception:
                # Pass to avoid EOF error
                pass

    def stop(self, force=False):
        self.read_on = False
        if force:
            self.socket.close()

    def select_table(self, table):
        select_dict = {"op": "select", "table": table, "where": []}
        op_id = str(random.getrandbits(128))
        params = ['hardware_vtep']
        params.append(select_dict)
        query_select = {"method": "transact",
                        "params": params,
                        "id": op_id}
        return query_select

    def find_row(self, net_id, count, resp_dec):
        for i in range(count):
            row = str(resp_dec['result'][0]['rows'][i])
            if net_id in row:
                return row

    def get_response(self, OVSDB_IP, OVSDB_PORT, table):
        query = self.select_table(table)
        self.send(query)
        time.sleep(2)
        resp = self.responses
        resp = str(resp[0])
        return resp
