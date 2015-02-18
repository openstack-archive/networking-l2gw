# Copyright 2015 OpenStack Foundation.
# All Rights Reserved
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
#

import logging

from neutronclient import client
from neutronclient.v2_0 import client as V2_Client

_logger = logging.getLogger(__name__)


class APIParamsCall(V2_Client.APIParamsCall):
    pass


class Client(V2_Client.Client):
    """Client for the  L2gateway v2.0 API.

    :param string username: Username for authentication. (optional)
    :param string user_id: User ID for authentication. (optional)
    :param string password: Password for authentication. (optional)
    :param string token: Token for authentication. (optional)
    :param string tenant_name: Tenant name. (optional)
    :param string tenant_id: Tenant id. (optional)
    :param string auth_url: Keystone service endpoint for authorization.
    :param string service_type: Network service type to pull from the
                                keystone catalog (e.g. 'network') (optional)
    :param string endpoint_type: Network service endpoint type to pull from the
                                 keystone catalog (e.g. 'publicURL',
                                 'internalURL', or 'adminURL') (optional)
    :param string region_name: Name of a region to select when choosing an
                               endpoint from the service catalog.
    :param string endpoint_url: A user-supplied endpoint URL for the neutron
                            service.  Lazy-authentication is possible for API
                            service calls if endpoint is set at
                            instantiation.(optional)
    :param integer timeout: Allows customization of the timeout for client
                            http requests. (optional)
    :param bool insecure: SSL certificate validation. (optional)
    :param string ca_cert: SSL CA bundle file to use. (optional)
    :param integer retries: How many times idempotent (GET, PUT, DELETE)
                            requests to Neutron server should be retried if
                            they fail (default: 0).
    :param bool raise_errors: If True then exceptions caused by connection
                              failure are propagated to the caller.
                              (default: True)
    :param session: Keystone client auth session to use. (optional)
    :param auth: Keystone auth plugin to use. (optional)
    """

    l2_gateways_path = "/l2-gateways"
    l2_gateway_path = "/l2-gateways/%s"
    l2_gateway_connections_path = "/l2-gateway-connections"
    l2_gateway_connection_path = "/l2-gateway-connections/%s"

    # API has no way to report plurals, so we have to hard code them
    EXTED_PLURALS = {'l2gateways': 'l2-gateways',
                     'l2gateway-connections': 'l2-gateway-connections',
                     }

    @APIParamsCall
    def create_l2_gateway(self, body=None):
        """Creates a new l2gateway."""

        return self.post(self.l2_gateways_path, body=body)

    @APIParamsCall
    def list_l2_gateways(self, retrieve_all=True, **_params):
        """Fetches a list of l2gateways."""

        return self.list('l2_gateways', self.l2_gateways_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_l2_gateway(self, l2gateway, **_params):
        """Fetches information of a certain l2gateway."""

        return self.get(self.l2_gateway_path % (l2gateway), params=_params)

    @APIParamsCall
    def delete_l2_gateway(self, l2gateway):
        """Deletes the specified l2gateway."""

        return self.delete(self.l2_gateway_path % (l2gateway))

    @APIParamsCall
    def update_l2_gateway(self, l2gateway, body):
        """Updates the specified l2gateway."""
        return self.put(self.l2_gateway_path % (l2gateway), body=body)

    @APIParamsCall
    def create_l2_gateway_connection(self, body=None):
        """Creates a new l2gateway-connection."""

        return self.post(self.l2_gateway_connections_path, body=body)

    @APIParamsCall
    def list_l2_gateway_connections(self, retrieve_all=True, **_params):
        """Fetches a list of l2gateway-connections."""

        return self.list('l2_gateway_connections',
                         self.l2_gateway_connections_path, retrieve_all,
                         **_params)

    @APIParamsCall
    def show_l2_gateway_connection(self, con_id, **_params):
        """Fetches information of a certain l2gateway-connection."""

        return self.get(self.l2_gateway_connection_path % (con_id),
                        params=_params)

    @APIParamsCall
    def delete_l2_gateway_connection(self, con_id):
        """Deletes the specified l2gateway-connection."""

        return self.delete(self.l2_gateway_connection_path % (con_id))

    def __init__(self, **kwargs):
        """Initialize a new client for the L2gateway v2.0 API."""

        super(Client, self).__init__()
        self.retries = kwargs.pop('retries', 0)
        self.raise_errors = kwargs.pop('raise_errors', True)
        self.httpclient = client.construct_http_client(**kwargs)
        self.version = '2.0'
        self.format = 'json'
        self.action_prefix = "/v%s" % (self.version)
        self.retry_interval = 1
