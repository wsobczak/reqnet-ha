"""Constants for the reQnet integration."""

DOMAIN = "reqnet"
DEFAULT_NAME = "Rekuperator reQnet"

CONF_HOST       = "host"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_NAME       = "name"

# ── CurrentWorkParameters → Values[] index mapping ────────────────
# Verified against live device (firmware 9.25, device type 9)
IDX_IS_ON               = 0    # 1=on, 0=standby
IDX_MAX_AIRFLOW         = 1    # system max airflow m³/h
IDX_AIRFLOW_SUPPLY      = 3    # current supply airflow m³/h
IDX_AIRFLOW_EXTRACT     = 4    # current extract airflow m³/h
IDX_MAX_AIRFLOW_SUPPLY  = 5    # configured max supply m³/h
IDX_MAX_AIRFLOW_EXTRACT = 6    # configured max extract m³/h
IDX_FAN_HUMIDITY_MIRROR = 7    # mirrors humidity % — NOT fan speed
IDX_BYPASS_STATUS       = 9    # bypass: 1=open, 0=closed
IDX_WORK_MODE           = 10   # operating mode integer (9=auto)
IDX_FAN_MANUAL_SUPPLY   = 16   # manual mode fan preset supply %
IDX_FAN_MANUAL_EXTRACT  = 17   # manual mode fan preset extract %
IDX_MAX_COMFORT_TEMP    = 18   # upper comfort temp limit °C (read-only)
IDX_MIN_COMFORT_TEMP    = 22   # lower comfort temp limit °C (read-only)
IDX_AIRING              = 26
IDX_CLEANING            = 27
IDX_HEATING             = 28
IDX_COOLING             = 29
IDX_FAST_HEATING        = 30
IDX_FAST_COOLING        = 31
IDX_FIREPLACE           = 32
IDX_HOLIDAY             = 33
IDX_SCHEDULE            = 34
IDX_GWC                 = 35
IDX_BYPASS_MODE         = 39   # 0=auto, 1=open, 2=closed
IDX_FILTER_DAYS         = 41
IDX_TEMP_INTAKE         = 55
IDX_TEMP_LAUNCHER       = 56
IDX_TEMP_SUPPLY         = 57
IDX_TEMP_EXTRACT        = 58
IDX_TEMP_HEATER         = 59
IDX_TEMP_GWC            = 60
IDX_TEMP_ROOM           = 61
IDX_TEMP_ADDITIONAL     = 62
IDX_FILTER_ALARM        = 63
IDX_COMFORT_TEMP        = 67   # user-set comfort temperature °C
IDX_FAN_SUPPLY_RPM      = 84   # supply fan RPM
IDX_FAN_EXTRACT_RPM     = 85   # extract fan RPM

# ── CurrentTemperatures MQTT payload field names ──────────────────
CT_INTAKE    = "IntakeTemp"
CT_LAUNCHER  = "LauncherTemp"
CT_SUPPLY    = "SupplyTemp"
CT_EXTRACT   = "ExtractTemp"
CT_HUMIDITY  = "Humidity"
CT_CO2       = "CO2Concentration"

# ── API MQTT payload field names ──────────────────────────────────
API_FW_VERSION  = "RecuperatorSoftwareVersion"
API_WIFI_SIGNAL = "WIFISignalStrength"
API_WIFI_DESC   = "WifiSignalStrengthDescription"
API_MQTT_STATUS = "MQTTStatus"
API_ERROR_CODE  = "ErrorCode"
API_DEVICE_TYPE = "DeviceType"
API_MAC         = "MAC"

# ── Work mode integer → string ────────────────────────────────────
# Mode 9 = auto confirmed; others based on API function names
MODE_STANDBY      = "standby"
MODE_AUTO         = "auto"
MODE_MANUAL       = "manual"
MODE_SCHEDULE     = "schedule"
MODE_AIRING       = "airing"
MODE_CLEANING     = "cleaning"
MODE_HEATING      = "heating"
MODE_COOLING      = "cooling"
MODE_FAST_HEATING = "fast_heating"
MODE_FAST_COOLING = "fast_cooling"
MODE_FIREPLACE    = "fireplace"
MODE_HOLIDAY      = "holiday"

WORK_MODE_MAP: dict[int, str] = {
    0:  MODE_STANDBY,
    1:  MODE_MANUAL,
    2:  MODE_SCHEDULE,
    3:  MODE_AIRING,
    4:  MODE_CLEANING,
    5:  MODE_HEATING,
    6:  MODE_COOLING,
    7:  MODE_FAST_HEATING,
    8:  MODE_FAST_COOLING,
    9:  MODE_AUTO,
    10: MODE_FIREPLACE,
    11: MODE_HOLIDAY,
}

# ── Bypass ────────────────────────────────────────────────────────
BYPASS_AUTO   = "auto"
BYPASS_OPEN   = "open"
BYPASS_CLOSED = "closed"
BYPASS_MODES  = [BYPASS_AUTO, BYPASS_OPEN, BYPASS_CLOSED]
BYPASS_INT_TO_STR = {0: BYPASS_AUTO, 1: BYPASS_OPEN, 2: BYPASS_CLOSED}
BYPASS_STR_TO_INT = {v: k for k, v in BYPASS_INT_TO_STR.items()}
