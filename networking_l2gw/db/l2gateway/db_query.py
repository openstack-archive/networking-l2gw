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

from neutron.db import models_v2

from neutron_lib import exceptions
from neutron_lib.plugins.ml2 import api
import sqlalchemy as sa
from sqlalchemy.orm import exc


class L2GatewayCommonDbMixin(object):

    def _apply_filters_to_query(self, query, model, filters):
        """Apply filters to query for the models."""
        if filters:
            for key, value in filters.items():
                column = getattr(model, key, None)
                if column:
                    query = query.filter(column.in_(value))
        return query

    def _model_query(self, context, model):
        """Query model based on filter."""
        query = context.session.query(model)
        query_filter = None
        if not context.is_admin and hasattr(model, 'tenant_id'):
            if hasattr(model, 'shared'):
                query_filter = ((model.tenant_id == context.tenant_id) |
                                (model.shared == sa.true()))
            else:
                query_filter = (model.tenant_id == context.tenant_id)
        if query_filter is not None:
            query = query.filter(query_filter)
        return query

    def _get_collection_query(self, context, model, filters=None,
                              sorts=None, limit=None, marker_obj=None,
                              page_reverse=False):
        """Get collection query for the models."""
        collection = self._model_query(context, model)
        collection = self._apply_filters_to_query(collection, model, filters)
        return collection

    def _get_marker_obj(self, context, resource, limit, marker):
        """Get marker object for the resource."""
        if limit and marker:
            return getattr(self, '_get_%s' % resource)(context, marker)
        return None

    def _fields(self, resource, fields):
        """Get fields for the resource for get query."""
        if fields:
            return dict(((key, item) for key, item in resource.items()
                         if key in fields))
        return resource

    def _get_tenant_id_for_create(self, context, resource):
        """Get tenant id for creation of resources."""
        if context.is_admin and 'tenant_id' in resource:
            tenant_id = resource['tenant_id']
        elif ('tenant_id' in resource and
              resource['tenant_id'] != context.tenant_id):
            reason = _('Cannot create resource for another tenant')
            raise exceptions.AdminRequired(reason=reason)
        else:
            tenant_id = context.tenant_id
        return tenant_id

    def _get_collection(self, context, model, dict_func, filters=None,
                        fields=None, sorts=None, limit=None, marker_obj=None,
                        page_reverse=False):
        """Get collection object based on query for resources."""
        query = self._get_collection_query(context, model, filters=filters,
                                           sorts=sorts,
                                           limit=limit,
                                           marker_obj=marker_obj,
                                           page_reverse=page_reverse)
        items = [dict_func(c, fields) for c in query]
        if limit and page_reverse:
            items.reverse()
        return items

    def _make_segment_dict(self, record):
        """Make a segment dictionary out of a DB record."""
        return {api.ID: record.id,
                api.NETWORK_TYPE: record.network_type,
                api.PHYSICAL_NETWORK: record.physical_network,
                api.SEGMENTATION_ID: record.segmentation_id}

    def _get_network(self, context, id):
        try:
            network = self._get_by_id(context, models_v2.Network, id)
        except exc.NoResultFound:
            raise exceptions.NetworkNotFound(net_id=id)
        return network

    def _get_by_id(self, context, model, id):
        query = self._model_query(context, model)
        return query.filter(model.id == id).one()
