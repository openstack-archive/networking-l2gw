# Copyright (c) 2015 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_log import log as logging
from sqlalchemy.orm import exc

from networking_l2gw.db.l2gateway.ovsdb import models

LOG = logging.getLogger(__name__)


def add_vlan_binding(context, record_dict):
    """Insert a vlan binding of a given physical port."""
    session = context.session
    with session.begin(subtransactions=True):
        binding = models.VlanBindings(
            port_uuid=record_dict['port_uuid'],
            vlan=record_dict['vlan'],
            logical_switch_uuid=record_dict['logical_switch_uuid'],
            ovsdb_identifier=record_dict['ovsdb_identifier'])
        session.add(binding)


def delete_vlan_binding(context, record_dict):
    """Delete vlan bindings of a given physical port."""
    session = context.session
    with session.begin(subtransactions=True):
        if(record_dict['vlan'] and record_dict['logical_switch_uuid']):
            session.query(models.VlanBindings).filter_by(
                port_uuid=record_dict['port_uuid'], vlan=record_dict['vlan'],
                logical_switch_uuid=record_dict['logical_switch_uuid'],
                ovsdb_identifier=record_dict['ovsdb_identifier']).delete()


def add_physical_locator(context, record_dict):
    """Insert a new physical locator."""
    session = context.session
    with session.begin(subtransactions=True):
        locator = models.PhysicalLocators(
            uuid=record_dict['uuid'],
            dst_ip=record_dict['dst_ip'],
            ovsdb_identifier=record_dict['ovsdb_identifier'])
        session.add(locator)


def delete_physical_locator(context, record_dict):
    """Delete physical locator that matches the supplied uuid."""
    session = context.session
    with session.begin(subtransactions=True):
        if(record_dict['uuid']):
            session.query(models.PhysicalLocators).filter_by(
                uuid=record_dict['uuid'],
                ovsdb_identifier=record_dict['ovsdb_identifier']).delete()


def add_physical_switch(context, record_dict):
    """Insert a new physical switch."""
    session = context.session
    with session.begin(subtransactions=True):
        physical_switch = models.PhysicalSwitches(
            uuid=record_dict['uuid'],
            name=record_dict['name'],
            tunnel_ip=record_dict['tunnel_ip'],
            ovsdb_identifier=record_dict['ovsdb_identifier'],
            switch_fault_status=record_dict['switch_fault_status'])
        session.add(physical_switch)


def delete_physical_switch(context, record_dict):
    """Delete physical switch that matches the supplied uuid."""
    session = context.session
    with session.begin(subtransactions=True):
        if(record_dict['uuid']):
            session.query(models.PhysicalSwitches).filter_by(
                uuid=record_dict['uuid'],
                ovsdb_identifier=record_dict['ovsdb_identifier']).delete()


def add_logical_switch(context, record_dict):
    """Insert a new logical switch."""
    session = context.session
    with session.begin(subtransactions=True):
        logical_switch = models.LogicalSwitches(
            uuid=record_dict['uuid'],
            name=record_dict['name'],
            key=record_dict['key'],
            ovsdb_identifier=record_dict['ovsdb_identifier'])
        session.add(logical_switch)


def delete_logical_switch(context, record_dict):
    """delete logical switch that matches the supplied uuid."""
    session = context.session
    with session.begin(subtransactions=True):
        if(record_dict['uuid']):
            session.query(models.LogicalSwitches).filter_by(
                uuid=record_dict['uuid'],
                ovsdb_identifier=record_dict['ovsdb_identifier']).delete()


def add_physical_port(context, record_dict):
    """Insert a new physical port."""
    session = context.session
    with session.begin(subtransactions=True):
        physical_port = models.PhysicalPorts(
            uuid=record_dict['uuid'],
            name=record_dict['name'],
            physical_switch_id=record_dict['physical_switch_id'],
            ovsdb_identifier=record_dict['ovsdb_identifier'],
            port_fault_status=record_dict['port_fault_status'])
        session.add(physical_port)


def update_physical_ports_status(context, record_dict):
    """Update physical port fault status."""
    with context.session.begin(subtransactions=True):
        (context.session.query(models.PhysicalPorts).
         filter(models.PhysicalPorts.uuid == record_dict['uuid']).
         update({'port_fault_status': record_dict['port_fault_status']},
         synchronize_session=False))


def update_physical_switch_status(context, record_dict):
    """Update physical switch fault status."""
    with context.session.begin(subtransactions=True):
        (context.session.query(models.PhysicalSwitches).
         filter(models.PhysicalSwitches.uuid == record_dict['uuid']).
         update({'switch_fault_status': record_dict['switch_fault_status']},
         synchronize_session=False))


def delete_physical_port(context, record_dict):
    """Delete physical port that matches the supplied uuid."""
    session = context.session
    with session.begin(subtransactions=True):
        if(record_dict['uuid']):
            session.query(models.PhysicalPorts).filter_by(
                uuid=record_dict['uuid'],
                ovsdb_identifier=record_dict['ovsdb_identifier']).delete()


def add_ucast_mac_local(context, record_dict):
    """Insert a new ucast mac local."""
    session = context.session
    with session.begin(subtransactions=True):
        ucast_mac_local = models.UcastMacsLocals(
            uuid=record_dict['uuid'],
            mac=record_dict['mac'],
            logical_switch_id=record_dict['logical_switch_id'],
            physical_locator_id=record_dict['physical_locator_id'],
            ip_address=record_dict['ip_address'],
            ovsdb_identifier=record_dict['ovsdb_identifier'])
        session.add(ucast_mac_local)


def delete_ucast_mac_local(context, record_dict):
    """Delete ucast mac local that matches the supplied uuid."""
    session = context.session
    with session.begin(subtransactions=True):
        if(record_dict['uuid']):
            session.query(models.UcastMacsLocals).filter_by(
                uuid=record_dict['uuid'],
                ovsdb_identifier=record_dict['ovsdb_identifier']).delete()


def add_ucast_mac_remote(context, record_dict):
    """Insert a new ucast mac remote."""
    session = context.session
    with session.begin(subtransactions=True):
        ucast_mac_remote = models.UcastMacsRemotes(
            uuid=record_dict['uuid'],
            mac=record_dict['mac'],
            logical_switch_id=record_dict['logical_switch_id'],
            physical_locator_id=record_dict['physical_locator_id'],
            ip_address=record_dict['ip_address'],
            ovsdb_identifier=record_dict['ovsdb_identifier'])
        session.add(ucast_mac_remote)


def delete_ucast_mac_remote(context, record_dict):
    """Delete ucast mac remote that matches the supplied uuid."""
    session = context.session
    with session.begin(subtransactions=True):
        if(record_dict['uuid']):
            session.query(models.UcastMacsRemotes).filter_by(
                uuid=record_dict['uuid'],
                ovsdb_identifier=record_dict['ovsdb_identifier']).delete()


def get_physical_port(context, record_dict):
    """Get physical port that matches the uuid and ovsdb_identifier."""
    try:
        query = context.session.query(models.PhysicalPorts)
        physical_port = query.filter_by(
            uuid=record_dict['uuid'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no physical port found for %s and %s',
                  record_dict['uuid'],
                  record_dict['ovsdb_identifier'])
        return
    return physical_port


def get_logical_switch(context, record_dict):
    """Get logical switch that matches the uuid and ovsdb_identifier."""
    try:
        query = context.session.query(models.LogicalSwitches)
        logical_switch = query.filter_by(
            uuid=record_dict['uuid'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no logical switch found for %s and %s',
                  record_dict['uuid'],
                  record_dict['ovsdb_identifier'])
        return
    return logical_switch


def get_all_logical_switches_by_name(context, name):
    """Get logical switch that matches the supplied name."""
    query = context.session.query(models.LogicalSwitches)
    return query.filter_by(name=name).all()


def get_ucast_mac_remote(context, record_dict):
    """Get ucast macs remote that matches the uuid and ovsdb_identifier."""
    try:
        query = context.session.query(models.UcastMacsRemotes)
        remote_mac = query.filter_by(
            uuid=record_dict['uuid'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no Remote mac found for %s and %s',
                  record_dict['uuid'],
                  record_dict['ovsdb_identifier'])
        return
    return remote_mac


def get_ucast_mac_local(context, record_dict):
    """Get ucast macs local that matches the uuid and ovsdb_identifier."""
    try:
        query = context.session.query(models.UcastMacsLocals)
        local_mac = query.filter_by(
            uuid=record_dict['uuid'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no Local mac found for %s and %s',
                  record_dict['uuid'],
                  record_dict['ovsdb_identifier'])
        return
    return local_mac


def get_ucast_mac_remote_by_mac_and_ls(context, record_dict):
    """Get ucast macs remote that matches the MAC addres and

       ovsdb_identifier.
    """
    try:
        query = context.session.query(models.UcastMacsRemotes)
        remote_mac = query.filter_by(
            mac=record_dict['mac'],
            ovsdb_identifier=record_dict['ovsdb_identifier'],
            logical_switch_id=record_dict['logical_switch_uuid']).one()
    except exc.NoResultFound:
        LOG.debug('no Remote mac found for %s and %s',
                  record_dict['mac'],
                  record_dict['logical_switch_uuid'])
        return
    return remote_mac


def get_physical_switch(context, record_dict):
    """Get physical switch that matches the uuid and ovsdb_identifier."""
    try:
        query = context.session.query(models.PhysicalSwitches)
        physical_switch = query.filter_by(
            uuid=record_dict['uuid'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no physical switch found for %s and %s',
                  record_dict['uuid'],
                  record_dict['ovsdb_identifier'])
        return
    return physical_switch


def get_physical_locator(context, record_dict):
    """Get physical locator that matches the supplied uuid."""
    try:
        query = context.session.query(models.PhysicalLocators)
        physical_locator = query.filter_by(
            uuid=record_dict['uuid'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no physical locator found for %s and %s',
                  record_dict['uuid'],
                  record_dict['ovsdb_identifier'])
        return
    return physical_locator


def get_physical_locator_by_dst_ip(context, record_dict):
    """Get physical locator that matches the supplied destination IP."""
    try:
        query = context.session.query(models.PhysicalLocators)
        physical_locator = query.filter_by(
            dst_ip=record_dict['dst_ip'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no physical locator found for %s and %s',
                  record_dict['dst_ip'],
                  record_dict['ovsdb_identifier'])
        return
    return physical_locator


def get_logical_switch_by_name(context, record_dict):
    """Get logical switch that matches the supplied name."""
    try:
        query = context.session.query(models.LogicalSwitches)
        logical_switch = query.filter_by(
            name=record_dict['logical_switch_name'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no logical switch found for %s and %s',
                  record_dict['logical_switch_name'],
                  record_dict['ovsdb_identifier'])
        return
    return logical_switch


def get_all_vlan_bindings_by_physical_port(context, record_dict):
    """Get vlan bindings that matches the supplied physical port."""
    query = context.session.query(models.VlanBindings)
    return query.filter_by(
        port_uuid=record_dict['uuid'],
        ovsdb_identifier=record_dict['ovsdb_identifier']).all()


def get_vlan_binding(context, record_dict):
    """Get vlan bindings that matches the supplied physical port."""
    try:
        query = context.session.query(models.VlanBindings)
        vlan_binding = query.filter_by(
            port_uuid=record_dict['port_uuid'],
            vlan=record_dict['vlan'],
            logical_switch_uuid=record_dict['logical_switch_uuid'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no vlan binding found for %s and %s',
                  record_dict['port_uuid'],
                  record_dict['ovsdb_identifier'])
        return
    return vlan_binding


def get_physical_switch_by_name(context, name):
    """Get logical switch that matches the supplied name."""
    query = context.session.query(models.PhysicalSwitches)
    return query.filter_by(name=name).first()


def get_physical_port_by_name_and_ps(context, record_dict):
    """Get vlan bindings that matches the supplied physical port."""
    try:
        query = context.session.query(models.PhysicalPorts)
        physical_port = query.filter_by(
            name=record_dict['interface_name'],
            physical_switch_id=record_dict['physical_switch_id'],
            ovsdb_identifier=record_dict['ovsdb_identifier']).one()
    except exc.NoResultFound:
        LOG.debug('no physical switch found for %s and %s',
                  record_dict['name'])
        return
    return physical_port


def get_all_physical_switches_by_ovsdb_id(context, ovsdb_identifier):
    """Get Physical Switches that match the supplied ovsdb identifier."""
    query = context.session.query(models.PhysicalSwitches)
    return query.filter_by(
        ovsdb_identifier=ovsdb_identifier).all()


def get_all_logical_switches_by_ovsdb_id(context, ovsdb_identifier):
    """Get logical Switches that match the supplied ovsdb identifier."""
    query = context.session.query(models.LogicalSwitches)
    return query.filter_by(
        ovsdb_identifier=ovsdb_identifier).all()


def get_all_vlan_bindings_by_logical_switch(context, record_dict):
    """Get Vlan bindings that match the supplied logical switch."""
    query = context.session.query(models.VlanBindings)
    return query.filter_by(
        logical_switch_uuid=record_dict['logical_switch_id'],
        ovsdb_identifier=record_dict['ovsdb_identifier']).all()
