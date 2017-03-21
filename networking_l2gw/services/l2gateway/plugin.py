# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
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

from neutron_lib.plugins import directory
from oslo_utils import excutils

from neutron.db import servicetype_db as st_db
from neutron.services import provider_configuration as pconf
from neutron.services import service_base

from networking_l2gw.db.l2gateway import l2gateway_db
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import constants
from networking_l2gw.services.l2gateway import exceptions as exc

from neutron_lib import exceptions as n_exc
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class L2GatewayPlugin(l2gateway_db.L2GatewayMixin):

    """Implementation of the Neutron l2 gateway Service Plugin.

    This class manages the workflow of L2 gateway request/response.
    """

    supported_extension_aliases = ["l2-gateway",
                                   "l2-gateway-connection"]

    def __init__(self):
        """Do the initialization for the l2 gateway service plugin here."""
        config.register_l2gw_opts_helper()
        self.service_type_manager = st_db.ServiceTypeManager.get_instance()
        self.service_type_manager.add_provider_configuration(
            constants.L2GW, pconf.ProviderConfiguration('networking_l2gw'))
        self._load_drivers()
        LOG.info("L2Gateway Service Plugin using Service Driver: %s",
                 self.default_provider)
        self.driver = self.drivers[self.default_provider]
        if len(self.drivers) > 1:
            LOG.warning("Multiple drivers configured for L2Gateway, "
                        "although running multiple drivers in parallel"
                        " is not yet supported")
        super(L2GatewayPlugin, self).__init__()
        l2gateway_db.subscribe()

    def _load_drivers(self):
        """Loads plugin-drivers specified in configuration."""
        self.drivers, self.default_provider = service_base.load_drivers(
            'L2GW', self)

    def _get_driver_for_provider(self, provider):
        if provider in self.drivers:
            return self.drivers[provider]
        # raise if not associated (should never be reached)
        raise n_exc.Invalid("Error retrieving driver for provider %s" %
                            provider)

    @property
    def _core_plugin(self):
        return directory.get_plugin()

    def get_plugin_type(self):
        """Get type of the plugin."""
        return constants.L2GW

    def get_plugin_description(self):
        """Get description of the plugin."""
        return constants.L2_GATEWAY_SERVICE_PLUGIN

    def add_port_mac(self, context, port_dict):
        """Process a created Neutron port."""
        self.driver.add_port_mac(context, port_dict)

    def delete_port_mac(self, context, port):
        """Process a deleted Neutron port."""
        self.driver.delete_port_mac(context, port)

    def create_l2_gateway(self, context, l2_gateway):
        """Create the L2Gateway."""
        self.validate_l2_gateway_for_create(context, l2_gateway)
        self.driver.create_l2_gateway(context, l2_gateway)
        with context.session.begin(subtransactions=True):
            l2_gateway_instance = super(L2GatewayPlugin,
                                        self).create_l2_gateway(context,
                                                                l2_gateway)
            self.driver.create_l2_gateway_precommit(context,
                                                    l2_gateway_instance)
        try:
            self.driver.create_l2_gateway_postcommit(
                context, l2_gateway_instance)
        except exc.L2GatewayServiceDriverError:
            with excutils.save_and_reraise_exception():
                LOG.error("L2GatewayPlugin.create_l2_gateway_postcommit "
                          "failed, deleting l2gateway '%s'",
                          l2_gateway_instance['id'])
                self.delete_l2_gateway(context, l2_gateway_instance['id'])
        return l2_gateway_instance

    def update_l2_gateway(self, context, l2_gateway_id, l2_gateway):
        """Update the L2Gateway."""
        self.validate_l2_gateway_for_update(context, l2_gateway_id, l2_gateway)
        self.driver.update_l2_gateway(context, l2_gateway_id, l2_gateway)
        with context.session.begin(subtransactions=True):
            l2_gateway_instance = super(L2GatewayPlugin,
                                        self).update_l2_gateway(context,
                                                                l2_gateway_id,
                                                                l2_gateway)
            self.driver.update_l2_gateway_precommit(context,
                                                    l2_gateway_instance)
        try:
            self.driver.update_l2_gateway_postcommit(
                context, l2_gateway_instance)
        except exc.L2GatewayServiceDriverError:
            with excutils.save_and_reraise_exception():
                LOG.error("L2GatewayPlugin.update_l2_gateway_postcommit"
                          " failed for l2gateway %s", l2_gateway_id)
        return l2_gateway_instance

    def delete_l2_gateway(self, context, l2_gateway_id):
        """Delete the L2Gateway."""
        self.validate_l2_gateway_for_delete(context, l2_gateway_id)
        self.driver.delete_l2_gateway(context, l2_gateway_id)
        with context.session.begin(subtransactions=True):
            super(L2GatewayPlugin, self).delete_l2_gateway(context,
                                                           l2_gateway_id)
            self.driver.delete_l2_gateway_precommit(context, l2_gateway_id)
        try:
            self.driver.delete_l2_gateway_postcommit(context, l2_gateway_id)
        except exc.L2GatewayServiceDriverError:
            with excutils.save_and_reraise_exception():
                LOG.error("L2GatewayPlugin.delete_l2_gateway_postcommit"
                          " failed for l2gateway %s", l2_gateway_id)

    def create_l2_gateway_connection(self, context, l2_gateway_connection):
        """Create an L2Gateway Connection

        Bind a Neutron VXLAN Network to Physical Network Segment.
        """
        self.validate_l2_gateway_connection_for_create(
            context, l2_gateway_connection)
        self.driver.create_l2_gateway_connection(context,
                                                 l2_gateway_connection)
        with context.session.begin(subtransactions=True):
            l2_gateway_conn_instance = super(
                L2GatewayPlugin, self).create_l2_gateway_connection(
                    context, l2_gateway_connection)
            self.driver.create_l2_gateway_connection_precommit(
                context, l2_gateway_conn_instance)
        try:
            self.driver.create_l2_gateway_connection_postcommit(
                context, l2_gateway_conn_instance)
        except exc.L2GatewayServiceDriverError:
            with excutils.save_and_reraise_exception():
                LOG.error("L2GatewayPlugin."
                          "create_l2_gateway_connection_postcommit "
                          "failed, deleting connection '%s'",
                          l2_gateway_conn_instance['id'])
                self.delete_l2_gateway_connection(
                    context, l2_gateway_conn_instance['id'])

        return l2_gateway_conn_instance

    def delete_l2_gateway_connection(self, context, l2_gateway_connection_id):
        """Delete an L2Gateway Connection

        Unbind a Neutron VXLAN Network from Physical Network Segment.
        """
        self.validate_l2_gateway_connection_for_delete(
            context, l2_gateway_connection_id)
        self.driver.delete_l2_gateway_connection(
            context, l2_gateway_connection_id)
        with context.session.begin(subtransactions=True):
            super(L2GatewayPlugin, self).delete_l2_gateway_connection(
                context, l2_gateway_connection_id)
            self.driver.delete_l2_gateway_connection_precommit(
                context, l2_gateway_connection_id)
        try:
            self.driver.delete_l2_gateway_connection_postcommit(
                context, l2_gateway_connection_id)
        except exc.L2GatewayServiceDriverError:
            with excutils.save_and_reraise_exception():
                LOG.error(
                    "L2GatewayPlugin.delete_l2_gateway_connection_postcommit"
                    " failed for connection %s", l2_gateway_connection_id)
