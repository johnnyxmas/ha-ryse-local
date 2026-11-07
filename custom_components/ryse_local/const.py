"""Constants for the RYSE SmartBridge (local) integration."""

DOMAIN = "ryse_local"

CONF_HOST = "host"
CONF_SERIAL = "serial"  # optional; sent as Authorization when local security is on

# Poll interval (seconds). The bridge is a small embedded device; keep this gentle.
SCAN_INTERVAL_SECONDS = 20

# Request timeout (seconds).
REQUEST_TIMEOUT = 10
