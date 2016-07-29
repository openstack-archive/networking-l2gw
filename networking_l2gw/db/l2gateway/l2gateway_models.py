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

import sqlalchemy as sa
from sqlalchemy.ext import declarative
from sqlalchemy import orm

from neutron.api.v2 import attributes as attr
from neutron.db import model_base
from neutron.db import models_v2


class HasProject(object):
    # NOTE(dasm): Temporary solution!
    # Remove when I87a8ef342ccea004731ba0192b23a8e79bc382dc is merged.

    project_id = sa.Column(sa.String(attr.TENANT_ID_MAX_LEN), index=True)

    def __init__(self, *args, **kwargs):
        # NOTE(dasm): debtcollector requires init in class
        super(HasProject, self).__init__(*args, **kwargs)

    def get_tenant_id(self):
        return self.project_id

    def set_tenant_id(self, value):
        self.project_id = value

    @declarative.declared_attr
    def tenant_id(cls):
        return orm.synonym(
            'project_id',
            descriptor=property(cls.get_tenant_id, cls.set_tenant_id))


class L2GatewayConnection(model_base.BASEV2, HasProject,
                          models_v2.HasId):
    """Define an l2 gateway connection between a l2 gateway and a network."""
    l2_gateway_id = sa.Column(sa.String(36),
                              sa.ForeignKey('l2gateways.id',
                                            ondelete='CASCADE'))
    network_id = sa.Column(sa.String(36),
                           sa.ForeignKey('networks.id', ondelete='CASCADE'),
                           nullable=False)
    segmentation_id = sa.Column(sa.Integer)
    __table_args__ = (sa.UniqueConstraint(l2_gateway_id,
                                          network_id),)


class L2GatewayInterface(model_base.BASEV2, models_v2.HasId):
    """Define an l2 gateway interface."""
    interface_name = sa.Column(sa.String(255))
    device_id = sa.Column(sa.String(36),
                          sa.ForeignKey('l2gatewaydevices.id',
                                        ondelete='CASCADE'),
                          nullable=False)
    segmentation_id = sa.Column(sa.Integer)


class L2GatewayDevice(model_base.BASEV2, models_v2.HasId):
    """Define an l2 gateway device."""
    device_name = sa.Column(sa.String(255), nullable=False)
    interfaces = orm.relationship(L2GatewayInterface,
                                  backref='l2gatewaydevices',
                                  cascade='all,delete')
    l2_gateway_id = sa.Column(sa.String(36),
                              sa.ForeignKey('l2gateways.id',
                                            ondelete='CASCADE'),
                              nullable=False)


class L2Gateway(model_base.BASEV2, models_v2.HasId, HasProject):
    """Define an l2 gateway."""
    name = sa.Column(sa.String(255))
    devices = orm.relationship(L2GatewayDevice,
                               backref='l2gateways',
                               cascade='all,delete')
    network_connections = orm.relationship(L2GatewayConnection,
                                           lazy='joined')
