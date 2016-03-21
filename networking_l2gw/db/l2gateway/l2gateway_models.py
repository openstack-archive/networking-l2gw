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

from neutron.db import model_base
from neutron.db import models_v2

import sqlalchemy as sa
from sqlalchemy import orm


class L2GatewayConnection(model_base.BASEV2, models_v2.HasTenant,
                          models_v2.HasId):
    """Define an l2 gateway connection between a l2 gateway and a network."""
    l2_gateway_id = sa.Column(sa.String(36),
                              sa.ForeignKey('l2gateways.id',
                                            ondelete='CASCADE'))
    network_id = sa.Column(sa.String(36),
                           sa.ForeignKey('networks.id', ondelete='CASCADE'))
    segmentation_id = sa.Column(sa.Integer)
    __table_args__ = (sa.UniqueConstraint(l2_gateway_id,
                                          network_id),)


class L2GatewayInterface(model_base.BASEV2, models_v2.HasId):
    """Define an l2 gateway interface."""
    interface_name = sa.Column(sa.String(255))
    device_id = sa.Column(sa.String(36),
                          sa.ForeignKey('l2gatewaydevices.id',
                                        ondelete='CASCADE'))
    segmentation_id = sa.Column(sa.Integer)


class L2GatewayDevice(model_base.BASEV2, models_v2.HasId):
    """Define an l2 gateway device."""
    device_name = sa.Column(sa.String(255))
    interfaces = orm.relationship(L2GatewayInterface,
                                  backref='l2gatewaydevices',
                                  cascade='all,delete')
    l2_gateway_id = sa.Column(sa.String(36),
                              sa.ForeignKey('l2gateways.id',
                                            ondelete='CASCADE'))


class L2Gateway(model_base.BASEV2, models_v2.HasId,
                models_v2.HasTenant):
    """Define an l2 gateway."""
    name = sa.Column(sa.String(255))
    devices = orm.relationship(L2GatewayDevice,
                               backref='l2gateways',
                               cascade='all,delete')
    network_connections = orm.relationship(L2GatewayConnection,
                                           lazy='joined')


class L2RemoteGateway(model_base.BASEV2, models_v2.HasId):
    name = sa.Column(sa.String(255))
    # should have hostname instead of IP address
    ipaddr = sa.Column(sa.String(255))


class L2RemoteGatewayConnection(model_base.BASEV2, models_v2.HasId):
    gateway = sa.Column(sa.String(36),
                        sa.ForeignKey('l2gateways.id',
                        ondelete='CASCADE'))
    network = sa.Column(sa.String(36),
                        sa.ForeignKey('networks.id', ondelete='CASCADE'))
    remote_gateway = sa.Column(sa.String(36),
                               sa.ForeignKey('l2remotegateways.id',
                                             ondelete='CASCADE')
                               )
    seg_id = sa.Column(sa.String(255))
    flood = sa.Column(sa.String(5))
