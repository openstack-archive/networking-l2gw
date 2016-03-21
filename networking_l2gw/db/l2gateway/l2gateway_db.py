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

from oslo_utils import uuidutils

from neutron.callbacks import events
from neutron.callbacks import registry
from neutron.callbacks import resources
from neutron.common import exceptions
from neutron import manager

from networking_l2gw.db.l2gateway import db_query
from networking_l2gw.db.l2gateway import l2gateway_models as models
from networking_l2gw.db.l2gateway.ovsdb import models as models2
from networking_l2gw.extensions import l2gateway
from networking_l2gw.extensions import l2gatewayconnection
from networking_l2gw.extensions import l2remotegateway
from networking_l2gw.extensions import l2remotegatewayconnection
from networking_l2gw.extensions import l2remotemac
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import constants
from networking_l2gw.services.l2gateway.common import l2gw_validators
from networking_l2gw.services.l2gateway import exceptions as l2gw_exc

from oslo_log import log as logging
from sqlalchemy.orm import exc as sa_orm_exc

LOG = logging.getLogger(__name__)


class L2GatewayMixin(l2gateway.L2GatewayPluginBase,
                     db_query.L2GatewayCommonDbMixin,
                     l2gatewayconnection.L2GatewayConnectionPluginBase,
                     l2remotegateway.L2RemoteGatewayPluginBase,
                     l2remotegatewayconnection.
                     L2RemoteGatewayConnectionPluginBase,
                     l2remotemac.L2RemoteMacPluginBase):
    """Class L2GatewayMixin for handling l2_gateway resource."""
    gateway_resource = constants.GATEWAY_RESOURCE_NAME
    connection_resource = constants.CONNECTION_RESOURCE_NAME
    config.register_l2gw_opts_helper()

    def _get_l2_gateway(self, context, gw_id):
        try:
            gw = context.session.query(models.L2Gateway).get(gw_id)
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2GatewayNotFound(gateway_id=gw_id)
        return gw

    def _get_l2_gateways(self, context):
        return context.session.query(models.L2Gateway).all()

    def _get_l2_gw_interfaces(self, context, id):
        return context.session.query(models.L2GatewayInterface).filter_by(
            device_id=id).all()

    def _is_vlan_configured_on_any_interface_for_l2gw(self,
                                                      context,
                                                      l2gw_id):
        devices_db = self._get_l2_gateway_devices(context, l2gw_id)
        for device_model in devices_db:
            interfaces_db = self._get_l2_gw_interfaces(context,
                                                       device_model.id)
            for int_model in interfaces_db:
                query = context.session.query(models.L2GatewayInterface)
                int_db = query.filter_by(id=int_model.id).first()
                seg_id = int_db[constants.SEG_ID]
                if seg_id > 0:
                    return True
        return False

    def _get_l2_gateway_devices(self, context, l2gw_id):
        return context.session.query(models.L2GatewayDevice).filter_by(
            l2_gateway_id=l2gw_id).all()

    def _get_l2gw_devices_by_name_andl2gwid(self, context, device_name,
                                            l2gw_id):
        return context.session.query(models.L2GatewayDevice).filter_by(
            device_name=device_name, l2_gateway_id=l2gw_id).all()

    def _get_l2_gateway_connection(self, context, cn_id):
        try:
            con = context.session.query(models.L2GatewayConnection).get(cn_id)
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2GatewayConnectionNotFound(id=cn_id)
        return con

    def _make_l2_remote_gateway_dict(self, rgw, fields=None):
        res = {'id': rgw['id'],
               'name': rgw['name'],
               'ipaddr': rgw['ipaddr']}

        return self._fields(res, fields)

    def _make_l2_remote_gateway_conn_dict(self, rgw, fields=None):
        res = {'id': rgw['id'],
               'gateway': rgw['gateway'],
               'network': rgw['network'],
               'remote_gateway': rgw['remote_gateway'],
               'seg_id': rgw['seg_id'],
               'flood': rgw['flood']}

        return self._fields(res, fields)

    def _make_l2gw_connections_dict(self, gw_conn, fields=None):
        if gw_conn is None:
            raise l2gw_exc.L2GatewayConnectionNotFound(id="")
        segmentation_id = gw_conn['segmentation_id']
        if segmentation_id == 0:
            segmentation_id = ""
        res = {'id': gw_conn['id'],
               'network_id': gw_conn['network_id'],
               'l2_gateway_id': gw_conn['l2_gateway_id'],
               'tenant_id': gw_conn['tenant_id'],
               'segmentation_id': segmentation_id
               }
        return self._fields(res, fields)

    def _make_l2_gateway_dict(self, l2_gateway, fields=None):
        device_list = []
        for d in l2_gateway.devices:
            interface_list = []
            for interfaces_db in d.interfaces:
                seg_id = interfaces_db[constants.SEG_ID]
                if seg_id == 0:
                    seg_id = ""
                interface_list.append({'name':
                                       interfaces_db['interface_name'],
                                       constants.SEG_ID:
                                       seg_id})
            aligned_int__list = self._align_interfaces_list(interface_list)
            device_list.append({'device_name': d['device_name'],
                                'id': d['id'],
                                'interfaces': aligned_int__list})
        res = {'id': l2_gateway['id'],
               'name': l2_gateway['name'],
               'devices': device_list,
               'tenant_id': l2_gateway['tenant_id']}
        return self._fields(res, fields)

    def _set_mapping_info_defaults(self, mapping_info):
        if not mapping_info.get(constants.SEG_ID):
            mapping_info[constants.SEG_ID] = 0

    def _retrieve_gateway_connections(self, context, gateway_id,
                                      mapping_info={}, only_one=False):
        filters = {'l2_gateway_id': [gateway_id]}
        for k, v in mapping_info.iteritems():
            if v and k != constants.SEG_ID:
                filters[k] = [v]
        query = self._get_collection_query(context,
                                           models.L2GatewayConnection,
                                           filters)
        return query.one() if only_one else query.all()

    def create_l2_gateway(self, context, l2_gateway):
        """Create a logical gateway."""
        self._admin_check(context, 'CREATE')
        gw = l2_gateway[self.gateway_resource]
        tenant_id = self._get_tenant_id_for_create(context, gw)
        devices = gw['devices']
        self._validate_any_seg_id_empty_in_interface_dict(devices)
        with context.session.begin(subtransactions=True):
                gw_db = models.L2Gateway(
                    id=gw.get('id', uuidutils.generate_uuid()),
                    tenant_id=tenant_id,
                    name=gw.get('name'))
                context.session.add(gw_db)
                l2gw_device_dict = {}
                for device in devices:
                    l2gw_device_dict['l2_gateway_id'] = id
                    device_name = device['device_name']
                    l2gw_device_dict['device_name'] = device_name
                    l2gw_device_dict['id'] = uuidutils.generate_uuid()
                    uuid = self._generate_uuid()
                    dev_db = models.L2GatewayDevice(id=uuid,
                                                    l2_gateway_id=gw_db.id,
                                                    device_name=device_name)
                    context.session.add(dev_db)
                    for interface_list in device['interfaces']:
                        int_name = interface_list.get('name')
                        if constants.SEG_ID in interface_list:
                            seg_id_list = interface_list.get(constants.SEG_ID)
                            for seg_ids in seg_id_list:
                                uuid = self._generate_uuid()
                                interface_db = self._get_int_model(uuid,
                                                                   int_name,
                                                                   dev_db.id,
                                                                   seg_ids)
                                context.session.add(interface_db)
                        else:
                            uuid = self._generate_uuid()
                            interface_db = self._get_int_model(uuid,
                                                               int_name,
                                                               dev_db.id,
                                                               0)
                            context.session.add(interface_db)
                        context.session.query(models.L2GatewayDevice).all()
        return self._make_l2_gateway_dict(gw_db)

    def update_l2_gateway(self, context, id, l2_gateway):
        """Update l2 gateway."""
        self._admin_check(context, 'UPDATE')
        gw = l2_gateway[self.gateway_resource]
        if 'devices' in gw:
            devices = gw['devices']
        with context.session.begin(subtransactions=True):
                l2gw_db = self._get_l2_gateway(context, id)
                if l2gw_db.network_connections:
                    raise l2gw_exc.L2GatewayInUse(gateway_id=id)
                dev_db = self._get_l2_gateway_devices(context, id)
                if not gw.get('devices'):
                    l2gw_db.name = gw.get('name')
                    return self._make_l2_gateway_dict(l2gw_db)
                for device in devices:
                    dev_name = device['device_name']
                    dev_db = self._get_l2gw_devices_by_name_andl2gwid(context,
                                                                      dev_name,
                                                                      id)
                    if not dev_db:
                        raise l2gw_exc.L2GatewayDeviceNotFound(device_id="")
                    interface_db = self._get_l2_gw_interfaces(context,
                                                              dev_db[0].id)
                    self._delete_l2_gateway_interfaces(context, interface_db)
                    interface_dict_list = []
                    self.validate_device_name(context, dev_name, id)
                    for interfaces in device['interfaces']:
                        interface_dict_list.append(interfaces)
                    self._update_interfaces_db(context, interface_dict_list,
                                               dev_db)
        if gw.get('name'):
            l2gw_db.name = gw.get('name')
        return self._make_l2_gateway_dict(l2gw_db)

    def _update_interfaces_db(self, context, interface_dict_list, device_db):
        for interfaces in interface_dict_list:
            int_name = interfaces.get('name')
            if constants.SEG_ID in interfaces:
                seg_id_list = interfaces.get(constants.SEG_ID)
                for seg_ids in seg_id_list:
                    uuid = self._generate_uuid()
                    int_db = self._get_int_model(uuid,
                                                 int_name,
                                                 device_db[0].id,
                                                 seg_ids)
                    context.session.add(int_db)
            else:
                uuid = self._generate_uuid()
                interface_db = self._get_int_model(uuid,
                                                   int_name,
                                                   device_db[0].id,
                                                   0)
                context.session.add(interface_db)

    def get_l2_gateway(self, context, id, fields=None):
        """get the l2 gateway by id."""
        self._admin_check(context, 'GET')
        gw_db = self._get_l2_gateway(context, id)
        if gw_db:
            return self._make_l2_gateway_dict(gw_db, fields)
        else:
            return []

    def delete_l2_gateway(self, context, id):
        """delete the l2 gateway  by id."""
        self._admin_check(context, 'DELETE')
        with context.session.begin(subtransactions=True):
            gw_db = self._get_l2_gateway(context, id)
            if gw_db is None:
                raise l2gw_exc.L2GatewayNotFound(gateway_id=id)
            if gw_db.network_connections:
                raise l2gw_exc.L2GatewayInUse(gateway_id=id)
            context.session.delete(gw_db)
        LOG.debug("l2 gateway '%s' was deleted.", id)

    def get_l2_gateways(self, context, filters=None, fields=None,
                        sorts=None,
                        limit=None,
                        marker=None,
                        page_reverse=False):
        """list the l2 gateways available in the neutron DB."""
        self._admin_check(context, 'GET')
        marker_obj = self._get_marker_obj(
            context, 'l2_gateway', limit, marker)
        return self._get_collection(context, models.L2Gateway,
                                    self._make_l2_gateway_dict,
                                    filters=filters, fields=fields,
                                    sorts=sorts, limit=limit,
                                    marker_obj=marker_obj,
                                    page_reverse=page_reverse)

    def _update_segmentation_id(self, context, l2gw_id, segmentation_id):
        """Update segmentation id for interfaces."""
        device_db = self._get_l2_gateway_devices(context, l2gw_id)
        for device_model in device_db:
            interface_db = self._get_l2_gw_interfaces(context,
                                                      device_model.id)
            for interface_model in interface_db:
                interface_model.segmentation_id = segmentation_id

    def _delete_l2_gateway_interfaces(self, context, int_db_list):
        """delete the l2 interfaces  by id."""
        with context.session.begin(subtransactions=True):
            for interfaces in int_db_list:
                context.session.delete(interfaces)
        LOG.debug("l2 gateway interfaces was deleted.")

    def create_l2_gateway_connection(self, context, l2_gateway_connection):
        """Create l2 gateway connection."""
        self._admin_check(context, 'CREATE')
        gw_connection = l2_gateway_connection[self.connection_resource]
        l2_gw_id = gw_connection.get('l2_gateway_id')
        network_id = gw_connection.get('network_id')
        nw_map = {}
        nw_map['network_id'] = network_id
        nw_map['l2_gateway_id'] = l2_gw_id
        segmentation_id = ""
        if constants.SEG_ID in gw_connection:
            segmentation_id = gw_connection.get(constants.SEG_ID)
            nw_map[constants.SEG_ID] = segmentation_id
        is_vlan = self._is_vlan_configured_on_any_interface_for_l2gw(context,
                                                                     l2_gw_id)
        network_id = l2gw_validators.validate_network_mapping_list(nw_map,
                                                                   is_vlan)
        with context.session.begin(subtransactions=True):
            gw_db = self._get_l2_gateway(context, l2_gw_id)
            tenant_id = self._get_tenant_id_for_create(context, gw_db)
            if self._retrieve_gateway_connections(context,
                                                  l2_gw_id,
                                                  nw_map):
                raise l2gw_exc.L2GatewayConnectionExists(mapping=nw_map,
                                                         gateway_id=l2_gw_id)
            nw_map['tenant_id'] = tenant_id
            connection_id = uuidutils.generate_uuid()
            nw_map['id'] = connection_id
            if not segmentation_id:
                nw_map['segmentation_id'] = "0"
            gw_db.network_connections.append(
                models.L2GatewayConnection(**nw_map))
            gw_db = models.L2GatewayConnection(id=connection_id,
                                               tenant_id=tenant_id,
                                               network_id=network_id,
                                               l2_gateway_id=l2_gw_id,
                                               segmentation_id=segmentation_id)
        return self._make_l2gw_connections_dict(gw_db)

    def get_l2_gateway_connections(self, context, filters=None,
                                   fields=None,
                                   sorts=None, limit=None, marker=None,
                                   page_reverse=False):
        """List l2 gateway connections."""
        self._admin_check(context, 'GET')
        marker_obj = self._get_marker_obj(
            context, 'l2_gateway_connection', limit, marker)
        return self._get_collection(context, models.L2GatewayConnection,
                                    self._make_l2gw_connections_dict,
                                    filters=filters, fields=fields,
                                    sorts=sorts, limit=limit,
                                    marker_obj=marker_obj,
                                    page_reverse=page_reverse)

    def get_l2_gateway_connection(self, context, id, fields=None):
        """Get l2 gateway connection."""
        self._admin_check(context, 'GET')
        """Get the l2 gateway  connection  by id."""
        gw_db = self._get_l2_gateway_connection(context, id)
        return self._make_l2gw_connections_dict(gw_db, fields)

    def delete_l2_gateway_connection(self, context, id):
        """Delete the l2 gateway connection by id."""
        self._admin_check(context, 'DELETE')
        with context.session.begin(subtransactions=True):
            gw_db = self._get_l2_gateway_connection(context, id)
            context.session.delete(gw_db)
        LOG.debug("l2 gateway '%s' was destroyed.", id)

    @staticmethod
    def _get_l2_remote_gateways(context):
        return context.session.query(models.L2RemoteGateway).all()

    def get_l2_remote_gateways(self, context, filters=None,
                               fields=None,
                               sorts=None, limit=None, marker=None,
                               page_reverse=False):
        self._admin_check(context, 'GET')
        marker_obj = self._get_marker_obj(
            context, 'l2_remote_gateway', limit, marker)
        return self._get_collection(context, models.L2RemoteGateway,
                                    self._make_l2_remote_gateway_dict,
                                    filters=filters, fields=fields,
                                    sorts=sorts, limit=limit,
                                    marker_obj=marker_obj,
                                    page_reverse=page_reverse)

    def create_l2_remote_gateway(self, context, l2_remote_gateway):
        self._admin_check(context, 'POST')
        rgw = l2_remote_gateway['l2_remote_gateway']
        with context.session.begin(subtransactions=True):
            rgw_db = models.L2RemoteGateway(id=uuidutils.generate_uuid(),
                                            name=rgw['name'],
                                            ipaddr=rgw['ipaddr'])
            context.session.add(rgw_db)

        return self._make_l2_remote_gateway_dict(rgw_db)

    def get_l2_remote_gateway(self, context, id, fields=None):
        self._admin_check(context, 'GET')
        return self._make_l2_remote_gateway_dict(
            self._get_l2_remote_gateway(context, id, fields))

    @staticmethod
    def _get_l2_remote_gateway(context, id, fields=None):
        try:
            rgw = context.session.query(models.L2RemoteGateway).get(id)
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2RemoteGatewayNotFound(id=id)
        return rgw

    @staticmethod
    def _get_remote_gateway_by_ip(context, ipaddr):
        return context.session.query(models.L2RemoteGateway).filter_by(
            ipaddr=ipaddr).one()

    def delete_l2_remote_gateway(self, context, id):
        self._admin_check(context, 'DELETE')
        with context.session.begin(subtransactions=True):
            rgw_db = self._get_l2_remote_gateway(context, id)
            context.session.delete(rgw_db)
        LOG.debug("l2 remote gateway '%s' was destroyed.", id)

    def update_l2_remote_gateway(self, context, id, l2_remote_gateway):
        self._admin_check(context, 'UPDATE')
        with context.session.begin(subtransactions=True):
            rgw_db = self._get_l2_remote_gateway(context, id)
            rgw = l2_remote_gateway['l2_remote_gateway']
            if 'name' in rgw:
                rgw_db.name = rgw['name']
            if 'ipaddr' in rgw:
                rgw_db.ipaddr = rgw['ipaddr']
        return self._make_l2_remote_gateway_dict(rgw_db)

    def get_l2_remote_gateway_connections(self, context, filters=None,
                                          fields=None,
                                          sorts=None, limit=None, marker=None,
                                          page_reverse=False):
        self._admin_check(context, 'GET')
        marker_obj = self._get_marker_obj(
            context, 'l2_remote_gateway_connection', limit, marker)
        return self._get_collection(context, models.L2RemoteGatewayConnection,
                                    self._make_l2_remote_gateway_conn_dict,
                                    filters=filters, fields=fields,
                                    sorts=sorts, limit=limit,
                                    marker_obj=marker_obj,
                                    page_reverse=page_reverse)

    def get_l2_remote_gateway_connection(self, context, id, fields=None):
        self._admin_check(context, 'GET')
        return self._make_l2_remote_gateway_conn_dict(
            self._get_l2_remote_gateway_connection(
                context, id, fields)
        )

    @staticmethod
    def _get_all_remote_gateway_connections(context):
        return context.session.query(models.L2RemoteGatewayConnection).all()

    @staticmethod
    def _get_l2_remote_gateway_connection(context, id, fields=None):
        try:
            rgw_con = context.session.query(
                models.L2RemoteGatewayConnection).get(id)
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2RemoteGatewayConnectionNotFound(id=id)
        return rgw_con

    @staticmethod
    def _get_remote_connection_by_rgw_and_segid(context, rgw, seg_id):
        return context.session.query(
            models.L2RemoteGatewayConnection).filter_by(
                remote_gateway=rgw, seg_id=seg_id).one()

    def create_l2_remote_gateway_connection(self, context,
                                            l2_remote_gateway_connection):
        self._admin_check(context, 'POST')
        rgw_conn = l2_remote_gateway_connection['l2_remote_gateway_connection']

        with context.session.begin(subtransactions=True):
            rgw_conn_db = models.L2RemoteGatewayConnection(
                id=uuidutils.generate_uuid(),
                gateway=rgw_conn['gateway'],
                network=rgw_conn['network'],
                remote_gateway=rgw_conn['remote_gateway']
            )

            if 'flood' in rgw_conn:
                rgw_conn_db.flood = rgw_conn['flood']
            else:
                rgw_conn_db.flood = 'True'

            if 'seg_id' in rgw_conn:
                rgw_conn_db.seg_id = rgw_conn['seg_id']

            context.session.add(rgw_conn_db)

        return self._make_l2_remote_gateway_conn_dict(rgw_conn_db)

    def delete_l2_remote_gateway_connection(self, context, id):
        self._admin_check(context, 'DELETE')
        with context.session.begin(subtransactions=True):
            rgw_conn_db = self._get_l2_remote_gateway_connection(context, id)
            context.session.delete(rgw_conn_db)
        LOG.debug("l2 remote gateway connection '%s' was destroyed.", id)

    def _admin_check(self, context, action):
        """Admin role check helper."""
        # TODO(selva): his check should be required if the tenant_id is
        # specified in the request, otherwise the policy.json do a trick
        # this need further revision.
        if not context.is_admin:
            reason = _('Cannot %s resource for non admin tenant') % action
            raise exceptions.AdminRequired(reason=reason)

    def _generate_uuid(self):
        """Generate uuid helper."""
        uuid = uuidutils.generate_uuid()
        return uuid

    def _get_int_model(self, uuid, interface_name, dev_id, seg_id):
        return models.L2GatewayInterface(id=uuid,
                                         interface_name=interface_name,
                                         device_id=dev_id,
                                         segmentation_id=seg_id)

    def get_l2gateway_devices_by_gateway_id(self, context, l2_gateway_id):
        """Get l2gateway_devices_by id."""
        session = context.session
        with session.begin():
            return session.query(models.L2GatewayDevice).filter_by(
                l2_gateway_id=l2_gateway_id).all()

    def get_ovsdb_identifiers(self, context, l2_gateway_id):
        session = context.session
        with session.begin():
            l2gw_list = session.query(models.L2GatewayDevice).filter_by(
                l2_gateway_id=l2_gateway_id).all()
            for l2gw in l2gw_list:
                session.query(models.L2GatewayDevice).filter_by(
                    l2_gateway_id=l2_gateway_id).all()

    def get_l2gateway_interfaces_by_device_id(self, context, device_id):
        """Get all l2gateway_interfaces_by device_id."""
        session = context.session
        with session.begin():
            return session.query(models.L2GatewayInterface).filter_by(
                device_id=device_id).all()

    def validate_device_name(self, context, device_name, l2gw_id):
        if device_name:
            devices_db = self._get_l2gw_devices_by_name_andl2gwid(context,
                                                                  device_name,
                                                                  l2gw_id)
        if not devices_db:
            raise l2gw_exc.L2GatewayDeviceNameNotFound(device_name=device_name)

    def _validate_any_seg_id_empty_in_interface_dict(self, devices):
        """Validate segmentation_id for consistency."""
        for device in devices:
            interface_list = device['interfaces']
            if not interface_list:
                raise l2gw_exc.L2GatewayInterfaceRequired()
            if constants.SEG_ID in interface_list[0]:
                for interfaces in interface_list[1:len(interface_list)]:
                    if constants.SEG_ID not in interfaces:
                        raise l2gw_exc.L2GatewaySegmentationRequired()
            if constants.SEG_ID not in interface_list[0]:
                for interfaces in interface_list[1:len(interface_list)]:
                    if constants.SEG_ID in interfaces:
                        raise l2gw_exc.L2GatewaySegmentationRequired()

    def _align_interfaces_list(self, interface_list):
        """Align interfaces list based on input dict for multiple seg ids."""
        interface_dict = {}
        aligned_interface_list = []
        for interfaces in interface_list:
            actual__name = interfaces.get('name')
            if actual__name in interface_dict:
                interface_name = interface_dict.get(actual__name)
                seg_id_list = interfaces.get(constants.SEG_ID)
                interface_name.append(str(seg_id_list))
                interface_dict.update({actual__name: interface_name})
            else:
                seg_id = str(interfaces.get(constants.SEG_ID)).split()
                interface_dict.update({actual__name: seg_id})
        for name in interface_dict:
            aligned_interface_list.append({'segmentation_id':
                                           interface_dict[name],
                                           'name': name})
        return aligned_interface_list

    def _get_l2_gateway_connections(self, context):
        """Get l2 gateway connections."""
        try:
            con = context.session.query(models.L2GatewayConnection).all()
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2GatewayConnectionNotFound(
                id="")
        return con

    def _get_l2gw_ids_by_interface_switch(self, context, interface_name,
                                          switch_name):
        """Get l2 gateway ids by interface and switch."""
        connections = self._get_l2_gateway_connections(context)
        l2gw_id_list = []
        if connections:
            for connection in connections:
                l2gw_id = connection.l2_gateway_id
                devices = self._get_l2_gateway_device_by_name_id(context,
                                                                 switch_name,
                                                                 l2gw_id)
                if devices:
                    for device in devices:
                        interfaces = self._get_l2_gw_interfaces(context,
                                                                device.id)
                        for interface in interfaces:
                            if interface_name == interface.interface_name:
                                l2gw_id_list.append(l2gw_id)
                else:
                    LOG.debug("l2 gateway devices are empty")
        else:
            LOG.debug("l2 gateway connections are empty")
        return l2gw_id_list

    def _delete_connection_by_l2gw_id(self, context, l2gw_id):
        """Delete the l2 gateway connection by l2gw id."""
        with context.session.begin(subtransactions=True):
            con_db = self._get_l2_gateway_connection_by_l2gw_id(context,
                                                                l2gw_id)
            if con_db:
                context.session.delete(con_db[0])
                LOG.debug("l2 gateway connection was destroyed.")

    def _get_l2_gateway_connection_by_l2gw_id(self, context, l2gw_id):
        """Get the l2 gateway connection by l2gw id."""
        try:
            con = context.session.query(models.L2GatewayConnection).filter_by(
                l2_gateway_id=l2gw_id).all()
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2GatewayConnectionNotFound(
                id=l2gw_id)
        return con

    def _get_l2_gateway_device_by_name_id(self, context, device_name, l2gw_id):
        """Get the l2 gateway device by name and id."""
        try:
            gw = context.session.query(models.L2GatewayDevice).filter_by(
                device_name=device_name, l2_gateway_id=l2gw_id).all()
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2GatewayDeviceNotFound(
                device_id=device_name)
        return gw

    @staticmethod
    def _get_physical_locator(context, ipaddr):
        return context.session.query(
            models2.PhysicalLocators).filter_by(dst_ip=ipaddr).all()

    @staticmethod
    def _get_physical_locator_by_id(context, uuid):
        return context.session.query(
            models2.PhysicalLocators).filter_by(uuid=uuid).one()

    @staticmethod
    def _get_physical_locator_by_ip_and_key(context, ipaddr, tunnel_key):
        return context.session.query(
            models2.PhysicalLocators).filter_by(
                dst_ip=ipaddr, tunnel_key=tunnel_key).one()

    @staticmethod
    def _get_ucat_macs_remote(context, phy_locator_uuid):
        return context.session.query(
            models2.UcastMacsRemotes).filter_by(
                physical_locator_id=phy_locator_uuid).all()

    @staticmethod
    def _get_ucast_mac_remote_by_id(context, uuid):
        return context.session.query(
            models2.UcastMacsRemotes).filter_by(uuid=uuid).one()

    def get_l2_remote_macs(self, context, filters=None,
                           fields=None, sorts=None,
                           limit=None, marker=None,
                           page_reverse=False):
        self._admin_check(context, 'GET')
        rmacs = []
        rgw_conn_list = self._get_all_remote_gateway_connections(context)
        ip_dict = {}
        for rgw_conn_db in rgw_conn_list:
            rgw_uuid = rgw_conn_db['remote_gateway']
            if rgw_uuid not in ip_dict:
                rgw_db = self._get_l2_remote_gateway(context, rgw_uuid)
                ip_dict[rgw_uuid] = rgw_db['ipaddr']
            locator_db = self._get_physical_locator_by_ip_and_key(
                context,
                ip_dict[rgw_uuid],
                rgw_conn_db['seg_id']
            )
            macs_db = self._get_ucat_macs_remote(
                context, locator_db['uuid'])
            if macs_db:
                for mac_db in macs_db:
                    rmac = {'uuid': mac_db['uuid'],
                            'mac': mac_db['mac'],
                            'rgw_connection': rgw_conn_db['id']}
                    rmacs.append(rmac)
        return rmacs

    def get_l2_remote_mac(self, context, id, fields=None):
        self._admin_check(context, 'GET')
        LOG.debug("Get remote MAC id: '%s'", id)
        rmac_db = context.session.query(
            models2.UcastMacsRemotes).filter_by(uuid=id).one()

        locator_db = self._get_physical_locator_by_id(
            context,
            rmac_db['physical_locator_id'])
        rgw_db = self._get_remote_gateway_by_ip(context, locator_db['dst_ip'])

        rgw_conn_db = self._get_remote_connection_by_rgw_and_segid(
            context, rgw_db['id'], locator_db['tunnel_key'])

        res = {'uuid': rmac_db['uuid'],
               'mac': rmac_db['mac'],
               'ipaddr': rmac_db['ip_address'],
               'rgw_connection': rgw_conn_db['id']
               }

        return res

    def create_l2_remote_mac(self, context, remote_gateway_conn):
        pass

    def delete_l2_remote_mac(self, context, id):
        pass

    def _get_logical_sw_by_name(self, context, name):
        return context.session.query(models2.LogicalSwitches).filter_by(
            name=name).one()


def l2gw_callback(resource, event, trigger, **kwargs):
    l2gwservice = manager.NeutronManager.get_service_plugins().get(
        constants.L2GW)
    context = kwargs.get('context')
    port_dict = kwargs.get('port')
    if l2gwservice:
        if event == events.AFTER_UPDATE:
            l2gwservice.add_port_mac(context, port_dict)
        elif event == events.AFTER_DELETE:
            l2gwservice.delete_port_mac(context, port_dict)


def subscribe():
    interested_events = (events.AFTER_UPDATE,
                         events.AFTER_DELETE)
    for x in interested_events:
        registry.subscribe(
            l2gw_callback, resources.PORT, x)
