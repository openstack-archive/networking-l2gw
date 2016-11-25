# Copyright (c) 2016 OpenStack Foundation.
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


class OvsdbObject(object):
    def __init__(self, uuid):
        self.uuid = uuid


class LogicalSwitch(OvsdbObject):
    def __init__(self, uuid, name, description, tunnel_key):
        super(LogicalSwitch, self).__init__(uuid)
        self.name = name
        self.description = description
        self.tunnel_key = tunnel_key


class PhysicalLocatorSet(OvsdbObject):
    def __init__(self, uuid, locator_uuid_list):
        super(PhysicalLocatorSet, self).__init__(uuid)
        self.locator_uuid_list = locator_uuid_list


class PhysicalLocator(OvsdbObject):
    def __init__(self, uuid,
                 dst_ip, tunnel_key=None,
                 encapsulation_type='vxlan_over_ipv4'):
        super(PhysicalLocator, self).__init__(uuid)
        self.dst_ip = dst_ip
        self.encapsulation_type = encapsulation_type
        self.tunnel_key = tunnel_key


class UcastMacs(OvsdbObject):
    def __init__(self, uuid, mac, ipaddr, logical_switch_uuid, locator_uuid):
        super(UcastMacs, self).__init__(uuid)
        self.mac = mac
        self.ipaddr = ipaddr
        self.logical_switch_uuid = logical_switch_uuid
        self.locator_uuid = locator_uuid


class McastMacs(OvsdbObject):
    def __init__(self, uuid, mac, dst_ip, logical_switch_uuid,
                 locator_set__uuid):
        super(McastMacs, self).__init__(uuid)
        self.mac = mac
        self.dst_ip = dst_ip
        self.logical_switch_uuid = logical_switch_uuid
        self.locator_set__uuid = locator_set__uuid


class PhysicalPort(OvsdbObject):
    def __init__(self, uuid, name, description, vlan_bindings_dict):
        super(PhysicalPort, self).__init__(uuid)
        self.name = name
        self.description = description
        self.vlan_bindings_dict = vlan_bindings_dict
