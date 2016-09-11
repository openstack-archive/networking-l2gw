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

from neutron.api.v2 import base

from neutron_lib import exceptions
from webob import exc as web_exc

from networking_l2gw._i18n import _


class L2GatewayInUse(exceptions.InUse):
    message = _("L2 Gateway '%(gateway_id)s' still has active mappings "
                "with one or more neutron networks.")


class L2GatewayNotFound(exceptions.NotFound):
    message = _("L2 Gateway %(gateway_id)s could not be found")


class L2GatewayDeviceInUse(exceptions.InUse):
    message = _("L2 Gateway Device '%(device_id)s' is still used by "
                "one or more network gateways.")


class L2AgentNotFoundByHost(exceptions.NotFound):
    message = _("L2 Agent for host '%(host)s' could not be found.")


class L2GatewayDeviceNotFound(exceptions.NotFound):
    message = _("L2 Gateway Device %(device_id)s could not be found.")


class L2GatewayDeviceNameNotFound(exceptions.NotFound):
    message = _("L2 Gateway Device %(device_name)s could not be found.")


class L2GatewayPortInUse(exceptions.InUse):
    message = _("Port '%(port_id)s' is owned by '%(device_owner)s' and "
                "therefore cannot be deleted directly via the port API.")


class L2GatewayConnectionExists(exceptions.InUse):
    message = _("The specified mapping '%(mapping)s' exists on "
                "network gateway '%(gateway_id)s'.")


class L2MultipleGatewayConnections(exceptions.NeutronException):
    message = _("Multiple network connections found on '%(gateway_id)s' "
                "with provided criteria.")


class L2GatewayInterfaceNotFound(exceptions.NeutronException):
    message = _("L2 Gateway interface '%(interface_id)s' not found.")


class L2GatewayPhysicalPortFaultStatus(exceptions.NeutronException):
    message = _("Physical Port '%(int_name)s' in Physical switch "
                "'%(device_name)s' port_fault_status is '%(fault_status)s'")


class L2GatewayPhysicalSwitchFaultStatus(exceptions.NeutronException):
    message = _("Physical Switch '%(device_name)s' switch_fault_status is "
                "'%(fault_status)s'")


class L2GatewayConnectionNotFound(exceptions.NotFound):
    message = _("The connection %(id)s not found on the l2 gateway")


class L2gatewaySegmentationIDNotFound(exceptions.NotFound):
    message = _("The segmentation id not found on gateway "
                "'%(gateway_id)s'")


class MultipleVxlanSegmentsFound(exceptions.NeutronException):
    message = _("Multiple Vxlan segments found for the network "
                "'%(network_id)s'")


class VxlanSegmentationIDNotFound(exceptions.NotFound):
    message = _("vxlan segmentation id not found for the "
                "network '%(network_id)s'")


class L2GatewayInterfaceRequired(exceptions.NeutronException):
    message = _("L2 Gateway Interface required")


class L2GatewaySegmentationIDExists(exceptions.InUse):
    message = _("The segmentation id is already specified in "
                "gateway interface '%(interface_id)s'.")


class L2GatewaySegmentationRequired(exceptions.NeutronException):
    message = _("L2 gateway segmentation id must be consistent for all "
                "the interfaces")


class L2GatewayDuplicateSegmentationID(exceptions.Conflict):
    message = _("%(message)s")


class OVSDBError(exceptions.NeutronException):
    message = _("%(message)s")


class L2GatewayServiceDriverError(exceptions.NeutronException):
    """Service driver call failed."""
    message = _("%(method)s failed.")


class InvalidMethod(exceptions.NeutronException):
    message = _("invalid method '%(op_method)s'")


base.FAULT_MAP.update({L2GatewayInUse: web_exc.HTTPConflict,
                       L2GatewayPortInUse: web_exc.HTTPConflict,
                       L2GatewayConnectionExists: web_exc.HTTPConflict,
                       L2GatewayConnectionNotFound: web_exc.HTTPNotFound,
                       MultipleVxlanSegmentsFound: web_exc.HTTPConflict,
                       VxlanSegmentationIDNotFound: web_exc.HTTPNotFound,
                       L2GatewaySegmentationRequired: web_exc.HTTPConflict,
                       L2MultipleGatewayConnections: web_exc.HTTPConflict,
                       L2GatewayDuplicateSegmentationID: web_exc.HTTPConflict,
                       L2AgentNotFoundByHost: web_exc.HTTPNotFound,
                       OVSDBError: web_exc.HTTPConflict})


class L3DvrAgentNotFound(exceptions.NotFound):
    message = _("L3 agent could not be found")


class DvrAgentHostnameNotFound(exceptions.NeutronException):
    message = _("Hostname '%(host)' has 127.0.0.1 address")
