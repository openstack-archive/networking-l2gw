# Copyright (c) 2016 Hewlett-Packard Enterprise Development Company, L.P.
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


from oslo_config import cfg

# L2Gateway related config information
L2GW_OPTS = [
    cfg.StrOpt('l2gw_switch',
               default='',
               help='Switch name ,interface and vlan id information '),
    cfg.StrOpt('l2gw_switch_2',
               default='',
               help='Switch name ,interface and vlan id information'),
    cfg.StrOpt('hosts',
               default='',
               help='Network node and compute node host names and IPs'),
    cfg.StrOpt('l2gw_switch_ip',
               default='',
               help='Switch IP'),
    cfg.StrOpt('ovsdb_ip',
               default='',
               help='IP of ovsdb server'),
    cfg.IntOpt('ovsdb_port',
               default=6632,
               help='Port of ovsdb server'),
    cfg.StrOpt('ovsdb_schema_name',
               default='',
               help='schema name of ovsdb')
]


l2gw_group = cfg.OptGroup(name='l2gw',
                          title='Neutron L2GW Options')
