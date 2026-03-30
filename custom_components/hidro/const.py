"""Constante pentru integrarea Hidroelectrica."""

from datetime import timedelta

DOMAIN = "hidro"
DEFAULT_SCAN_INTERVAL = 3600  # 1 oră
MIN_SCAN_INTERVAL = 300  # 5 minute
MAX_SCAN_INTERVAL = 86400  # 24 ore

CONF_UAN = "uan"
CONF_ACCOUNTS = "accounts"

# API endpoints
API_BASE_URL = "https://portal.hidroelectrica.ro/SEW/rest/"

# Sensor types
SENSOR_CONTRACT_DATA = "contract_data"
SENSOR_CURRENT_BALANCE = "current_balance"
SENSOR_OUTSTANDING_BILL = "outstanding_bill"
SENSOR_CURRENT_INDEX = "current_index"
SENSOR_ALLOWED_READING = "allowed_reading"
SENSOR_CONSUMPTION_ARCHIVE = "consumption_archive"
SENSOR_INDEX_ARCHIVE = "index_archive"
SENSOR_PAYMENTS_ARCHIVE = "payments_archive"

# Prosumator specific
SENSOR_PRODUCTION_INDEX = "production_index"
SENSOR_PRODUCTION_INDEX_ARCHIVE = "production_index_archive"
SENSOR_PROSUMER_PAYMENTS_ARCHIVE = "prosumer_payments_archive"

# Attributes
ATTR_UAN = "uan"
ATTR_NAME = "name"
ATTR_ADDRESS = "address"
ATTR_CITY = "city"
ATTR_PHONE = "phone"
ATTR_METER_SERIAL = "meter_serial"
ATTR_CONTRACT_NUMBER = "contract_number"
ATTR_CLIENT_TYPE = "client_type"