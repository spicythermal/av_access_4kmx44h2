"""Constants for the AV Access 4KMX44-H2 integration."""

DOMAIN = "av_access_4kmx44h2"

NUM_PORTS = 4  # 4 inputs, 4 outputs

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DEFAULT_SCAN_INTERVAL = 10  # seconds between coordinator polls

INPUT_NAMES = [f"HDMI In {i}" for i in range(1, NUM_PORTS + 1)]
