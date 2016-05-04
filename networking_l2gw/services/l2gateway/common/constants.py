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
# service type constants:
L2GW = "L2GW"
l2gw = "l2gw"

AGENT_TYPE_L2GATEWAY = 'L2 Gateway agent'

L2GW_INVALID_OVSDB_IDENTIFIER = 101

ERROR_DICT = {L2GW_INVALID_OVSDB_IDENTIFIER: "Invalid ovsdb_identifier in the "
              "request"}

MONITOR = 'monitor'
OVSDB_SCHEMA_NAME = 'hardware_vtep'
OVSDB_IDENTIFIER = 'ovsdb_identifier'
L2GW_AGENT_TYPE = 'l2gw_agent_type'
NETWORK_ID = 'network_id'
SEG_ID = 'segmentation_id'
L2GATEWAY_ID = 'l2_gateway_id'
GATEWAY_RESOURCE_NAME = 'l2_gateway'
L2_GATEWAYS = 'l2-gateways'
DEVICE_ID_ATTR = 'device_name'
IFACE_NAME_ATTR = 'interfaces'
CONNECTION_RESOURCE_NAME = 'l2_gateway_connection'
EXT_ALIAS = 'l2-gateway-connection'
L2_GATEWAYS_CONNECTION = "%ss" % EXT_ALIAS
BUFFER_SIZE = 4096
MAX_RETRIES = 1000
L2_GATEWAY_SERVICE_PLUGIN = "Neutron L2 gateway Service Plugin"
PORT_FAULT_STATUS_UP = "UP"
SWITCH_FAULT_STATUS_UP = "UP"
VXLAN = "vxlan"
CREATE = "CREATE"
DELETE = "DELETE"
