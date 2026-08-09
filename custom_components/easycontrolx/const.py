from __future__ import annotations

from datetime import timedelta

DOMAIN = "easycontrolx"
DATA_LOADED_ENTRY_IDS = "loaded_entry_ids"

PLATFORMS: tuple[str, ...] = (
    "binary_sensor",
    "button",
    "camera",
    "sensor",
    "switch",
)

CONF_BASE_URL = "base_url"
CONF_CONTROLLER_NAME = "controller_name"
CONF_DEVICE_ID = "device_id"
CONF_TLS_FINGERPRINT = "tls_fingerprint"
CONF_CONFIG_ENTRY_ID = "config_entry_id"
CONF_PREFERRED_MONITOR_ID = "preferred_monitor_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_CONTROLLER_NAME = "Home Assistant"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT_SECONDS = 10

OPTIONAL_OPTIONS = {
    CONF_PREFERRED_MONITOR_ID: "",
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}

SCAN_INTERVAL_MIN = 10
SCAN_INTERVAL_MAX = 300

UPDATE_INTERVAL_FALLBACK = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

TOKEN_HEADER = "X-EasyControlX-Token"

SERVICE_POWER_ACTION = "power_action"
SERVICE_MEDIA_ACTION = "media_action"
SERVICE_AUDIO_ACTION = "audio_action"
SERVICE_REFRESH = "refresh"
SERVICE_SERVICE_ACTION = "service_action"
SERVICE_LIST_SERVICES = "list_services"

ATTR_ACTION = "action"
ATTR_ALLOW_MULTIPLE_MATCHES = "allow_multiple_matches"
ATTR_ARGUMENTS = "arguments"
ATTR_DESTINATION_PATH = "destination_path"
ATTR_OVERWRITE = "overwrite"
ATTR_PATH = "path"
ATTR_PROCESS_ID = "process_id"
ATTR_PROCESS_NAME = "process_name"
ATTR_SERVICE_NAME = "service_name"
ATTR_SOURCE_PATH = "source_path"
ATTR_TARGET = "target"
ATTR_VALUE = "value"
ATTR_WORKING_DIRECTORY = "working_directory"

POWER_ACTIONS: tuple[str, ...] = ("Lock", "Sleep")
MEDIA_ACTIONS: tuple[str, ...] = ("PlayPause", "NextTrack", "PreviousTrack", "Pause")
AUDIO_ACTIONS: tuple[str, ...] = (
    "SetOutputVolume",
    "MuteOutput",
    "UnmuteOutput",
    "ToggleMute",
)
PROCESS_ACTIONS: tuple[str, ...] = ("CloseMainWindow", "Terminate")
MANAGED_SERVICE_ACTIONS: tuple[str, ...] = ("Start", "Stop", "Restart")

SERVICE_APP_LAUNCH = "app_launch"
SERVICE_BROWSE_FILES = "browse_files"
SERVICE_COPY_FILE = "copy_file"
SERVICE_LIST_PROCESSES = "list_processes"
SERVICE_PROCESS_ACTION = "process_action"

DIAGNOSTICS_REDACT = {
    "access_token",
    "verificationCode",
    "sessionId",
}
