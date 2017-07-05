#!/bin/bash
# devstack/plugin.sh
# Functions to control the configuration and operation of the l2gw
# Dependencies:
#
# ``functions`` file
# ``DEST`` must be defined
# ``STACK_USER`` must be defined
# ``stack.sh`` calls the entry points in this order:
# Save trace setting

XTRACE=$(set +o | grep xtrace)
set +o xtrace

function install_l2gw {
   setup_develop $L2GW_DIR
}

function configure_agent_conf {
    sudo cp $L2GW_DIR/etc/l2gateway_agent.ini $L2GW_CONF_FILE
    iniset $L2GW_CONF_FILE ovsdb ovsdb_hosts $OVSDB_HOSTS
}

function start_l2gw_agent {
    run_process l2gw-agent "$L2GW_AGENT_BINARY --config-file $NEUTRON_CONF --config-file=$L2GW_CONF_FILE"
}

function run_l2gw_alembic_migration {
   $NEUTRON_BIN_DIR/neutron-db-manage --config-file $NEUTRON_CONF --config-file /$Q_PLUGIN_CONF_FILE upgrade head
}

function configure_l2gw_plugin {
    sudo cp $L2GW_DIR/etc/l2gw_plugin.ini $L2GW_PLUGIN_CONF_FILE
    neutron_server_config_add $L2GW_PLUGIN_CONF_FILE
}

function configure_tempest_for_l2gw {
    if is_service_enabled tempest; then
       iniset $TEMPEST_CONFIG l2gw l2gw_switch "cell08-5930-01::FortyGigE1/0/1|100"
       source /opt/stack/new/tempest/.tox/tempest/bin/activate
       pip install -r $L2GW_DIR/test-requirements.txt
       deactivate
    fi
}

# main loop
if is_service_enabled l2gw-plugin; then
    if [[ "$1" == "source" ]]; then
        # no-op
        :
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        install_l2gw
    elif [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        _neutron_service_plugin_class_add $L2GW_PLUGIN
    elif [[ "$1" == "stack" && "$2" == "test-config" ]]; then
        configure_tempest_for_l2gw
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        configure_l2gw_plugin
        run_l2gw_alembic_migration
        if is_service_enabled q-svc; then
            echo_summary "Configuring networking-l2gw"
            if [ "$NETWORKING_L2GW_SERVICE_DRIVER" ]; then
                inicomment $L2GW_PLUGIN_CONF_FILE service_providers service_provider
                iniadd $L2GW_PLUGIN_CONF_FILE service_providers service_provider $NETWORKING_L2GW_SERVICE_DRIVER
            fi
        fi
    elif [[ "$1" == "stack" && "$2" == "post-extra" ]]; then
        # no-op
        :
    fi

    if [[ "$1" == "unstack" ]]; then
        # no-op
        :
    fi

    if [[ "$1" == "clean" ]]; then
        # no-op
        :
    fi
fi

if is_service_enabled l2gw-agent; then
    if [[ "$1" == "source" ]]; then
        # no-op
        :
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        install_l2gw
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        configure_agent_conf
        start_l2gw_agent
    fi

    if [[ "$1" == "unstack" ]]; then
        #no-op
        :
    fi

    if [[ "$1" == "clean" ]]; then
        #no-op
        :
    fi
fi

# Restore xtrace
$XTRACE
