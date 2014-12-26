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

from neutron.common import exceptions
from neutron.openstack.common import log as logging
from neutron.openstack.common import uuidutils

from networking_l2gw.db.l2gateway import db_query
from networking_l2gw.db.l2gateway import l2gateway_models as models
from networking_l2gw.extensions import l2gateway
from networking_l2gw.extensions import l2gatewayconnection
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import constants
from networking_l2gw.services.l2gateway.common import l2gw_validators
from networking_l2gw.services.l2gateway import exceptions as l2gw_exc

from sqlalchemy.orm import exc as sa_orm_exc

LOG = logging.getLogger(__name__)


class L2GatewayMixin(l2gateway.L2GatewayPluginBase,
                     db_query.L2GatewayCommonDbMixin,
                     l2gatewayconnection.L2GatewayConnectionPluginBase):
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
        try:
            gw = context.session.query(models.L2Gateway).all()
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2GatewayNotFound(gateway_id="")
        return gw

    def _get_l2_gateway_interface(self, context, id):
        try:
            gw = context.session.query(models.L2GatewayInterface).filter_by(
                device_id=id).all()
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2GatewayInterfaceNotFound(interface_id=id)
        return gw

    def _check_vlan_on_interface(self, context, l2gw_id):
        device_db = self._get_l2_gateway_device(context, l2gw_id)
        for device_model in device_db:
            interface_db = self._get_l2_gateway_interface(context,
                                                          device_model.id)
            for int_model in interface_db:
                query = context.session.query(models.L2GatewayInterface)
                int_db = query.filter_by(id=int_model.id).first()
                seg_id = int_db[constants.SEG_ID]
                if seg_id > 0:
                    return True
        return False

    def _get_l2_gateway_device(self, context, l2gw_id):
        try:
            gw = context.session.query(models.L2GatewayDevice).filter_by(
                l2_gateway_id=l2gw_id).all()
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2GatewayDeviceNotFound(device_id=l2gw_id)
        return gw

    def _get_l2_gateway_connection(self, context, cn_id):
        try:
            con = context.session.query(models.L2GatewayConnection).get(cn_id)
        except sa_orm_exc.NoResultFound:
            raise l2gw_exc.L2GatewayConnectionNotFound(id=cn_id)
        return con

    def _make_l2gw_connections_dict(self, gw_conn, fields=None):
        if gw_conn is None:
            raise l2gw_exc.L2GatewayConnectionNotFound(id="")
        res = {'id': gw_conn['id'],
               'network_id': gw_conn['network_id'],
               'l2_gateway_id': gw_conn['l2_gateway_id']
               }
        return self._fields(res, fields)

    def _make_l2_gateway_dict(self, l2_gateway, interface_db, fields=None):
        device_list = []
        interface_list = []
        for d in l2_gateway['devices']:
            if not interface_list:
                for interfaces_db in d['interfaces']:
                    interface_list.append({'name':
                                           interfaces_db['interface_name'],
                                           constants.SEG_ID:
                                           interfaces_db[constants.SEG_ID]})
            device_list.append({'device_name': d['device_name'],
                                'id': d['id'],
                                'interfaces': interface_list})
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
            if v:
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
        with context.session.begin(subtransactions=True):
                gw_db = models.L2Gateway(
                    id=gw.get('id', uuidutils.generate_uuid()),
                    tenant_id=tenant_id,
                    name=gw.get('name'))
                context.session.add(gw_db)
                l2gw_device_dict = {}
                interface_db_list = []
                for device in devices:
                    l2gw_device_dict['l2_gateway_id'] = id
                    device_name = device['device_name']
                    l2gw_device_dict['device_name'] = device_name
                    l2gw_device_dict['id'] = uuidutils.generate_uuid()
                    uuid = self._generate_uuid()
                    d_db = models.L2GatewayDevice(id=uuid,
                                                  l2_gateway_id=gw_db.id,
                                                  device_name=device_name)
                    context.session.add(d_db)
                    for interface_list in device['interfaces']:
                        name = interface_list.get('name')
                        seg_list = interface_list.get(constants.SEG_ID, None)
                        if seg_list:
                            for segs in seg_list:
                                uuid = self._generate_uuid()
                                interface_db = self._get_int_model(uuid,
                                                                   name,
                                                                   d_db.id,
                                                                   segs)
                                context.session.add(interface_db)
                                interface_db_list.append(interface_db)
                        else:
                            uuid = self._generate_uuid()
                            default_seg_id = constants.SEG_ID
                            interface_db = self._get_int_model(uuid,
                                                               name,
                                                               d_db.id,
                                                               default_seg_id)
                            context.session.add(interface_db)
                            interface_db_list.append(interface_db)
                        context.session.query(models.L2GatewayDevice).all()
        return self._make_l2_gateway_dict(gw_db, interface_db_list)

    def update_l2_gateway(self, context, id, l2_gateway):
        """Update l2 gateway."""
        self._admin_check(context, 'UPDATE')
        gw = l2_gateway[self.gateway_resource]
        devices = gw['devices']
        with context.session.begin(subtransactions=True):
                l2gw_db = self._get_l2_gateway(context, id)
                if l2gw_db.network_connections:
                    raise l2gw_exc.L2GatewayInUse(gateway_id=id)
                l2gw_db.name = gw.get('name')
                interface_db_list = []
                device_db = self._get_l2_gateway_device(context, id)
                interface_dict_list = []
                for device in devices:
                        for interfaces in device['interfaces']:
                            interface_dict_list.append(interfaces)
                for d_val in device_db:
                    interface_db = self._get_l2_gateway_interface(context,
                                                                  d_val.id)
                    self._delete_l2_gateway_interfaces(context, interface_db)
                    for interfaces in interface_dict_list:
                        int_name = interfaces.get('name')
                        seg_id_list = interfaces.get(constants.SEG_ID, None)
                        uuid = self._generate_uuid()
                        for seg_ids in seg_id_list:
                            interface_db = self._get_int_model(uuid,
                                                               int_name,
                                                               d_val.id,
                                                               seg_ids)
                            context.session.add(interface_db)
                            interface_db_list.append(interface_db)
        return self._make_l2_gateway_dict(l2gw_db, interface_db_list)

    def get_l2_gateway(self, context, id, fields=None):
        """get the l2 gateway by id."""
        self._admin_check(context, 'GET')
        gw_db = self._get_l2_gateway(context, id)
        if gw_db:
            device_db = self._get_l2_gateway_device(context, gw_db.id)
            for devices in device_db:
                interface_db = self._get_l2_gateway_interface(context,
                                                              devices.id)
                return self._make_l2_gateway_dict(gw_db, interface_db, fields)
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
        device_db = self._get_l2_gateway_device(context, l2gw_id)
        for device_model in device_db:
            interface_db = self._get_l2_gateway_interface(context,
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
        segmentation_id = gw_connection.get(constants.SEG_ID)
        nw_map = {}
        nw_map['network_id'] = network_id
        nw_map['l2_gateway_id'] = l2_gw_id
        if segmentation_id in gw_connection:
            nw_map[constants.SEG_ID] = segmentation_id
        check_vlan = self._check_vlan_on_interface(context, l2_gw_id)
        network_id = l2gw_validators.validate_network_mapping_list(nw_map,
                                                                   check_vlan)
        if segmentation_id:
            self._update_segmentation_id(context, l2_gw_id, segmentation_id)
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
            nw_map.pop(constants.SEG_ID, None)
            gw_db.network_connections.append(
                models.L2GatewayConnection(**nw_map))
            gw_db = models.L2GatewayConnection(id=connection_id,
                                               tenant_id=tenant_id,
                                               network_id=network_id,
                                               l2_gateway_id=l2_gw_id)
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

    def _admin_check(self, context, action):
        """Admin role check helper."""
        # TODO(selva): his check should be required if the tenant_id is
        # specified inthe request, otherwise the policy.json do a trick
        # this need further revision.
        if not context.is_admin:
            reason = _('Cannot %(action)s resource for non admin tenant')
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
