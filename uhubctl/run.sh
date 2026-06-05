#!/usr/bin/with-contenv bashio
set -eu

# Check if the log level configuration option exists
declare LOG_LEVEL="INFO"
if bashio::config.has_value 'LOG_LEVEL'; then
    LOG_LEVEL="$(bashio::string.lower "$(bashio::config 'LOG_LEVEL')")"
fi
bashio::log.blue "Log level is set to ${LOG_LEVEL}"

while true; do
    bashio::log.blue "Starting MQTT - uhubctl bridge..."

    if ! bashio::services.available "mqtt"; then
        bashio::log.warning "No MQTT service running! Retry after 30 seconds..."
    else
        export MQTT_HOST=$(bashio::services "mqtt" "host")
        export MQTT_PORT=$(bashio::services "mqtt" "port")
        export MQTT_USERNAME=$(bashio::services "mqtt" "username")
        export MQTT_PASSWORD=$(bashio::services "mqtt" "password")

        if python3 main.py --log "${LOG_LEVEL}"; then
            bashio::log.info "Bridge stopped normally"
        else
            bashio::log.error "Bridge exited with error code $?"
        fi
    fi
    sleep 30
done
