#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Grünbeck Spaliq Modbus Bridge..."

exec python3 /app/main.py
