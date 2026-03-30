from __future__ import annotations

from .helpers import nested_get

CORE_DESKTOP_PREVIEW = "desktop.preview"
CORE_AUDIO_OUTPUT = "audio.output"
CORE_APPLICATIONS_LAUNCH = "applications.launch"
CORE_MEDIA = "media"
CORE_BLUETOOTH_LIST = "bluetooth.list"
CORE_SYSTEM_CPU = "system.cpu"
CORE_SYSTEM_MEMORY = "system.memory"
CORE_SYSTEM_UPTIME = "system.uptime"
CORE_SYSTEM_STORAGE = "system.storage"
CORE_SYSTEM_NETWORK = "system.network"
CORE_POWER_LOCK = "power.lock"
CORE_POWER_SLEEP = "power.sleep"
CORE_POWER_RESTART = "power.restart"
CORE_POWER_SHUTDOWN = "power.shutdown"

WINDOWS_MONITORS_LIST = "windows.monitors.list"
WINDOWS_MONITORS_PREVIEW = "windows.monitors.preview"
WINDOWS_PROCESSES_CONTROL = "windows.processes.control"
WINDOWS_PROCESSES_LIST = "windows.processes.list"
WINDOWS_FILES_BROWSE = "windows.files.browse"
WINDOWS_FILES_COPY = "windows.files.copy"
WINDOWS_WINDOWS_LIST = "windows.windows.list"
WINDOWS_WINDOWS_PREVIEW = "windows.windows.preview"
WINDOWS_SERVICES_LIST = "windows.services.list"
WINDOWS_SERVICES_CONTROL = "windows.services.control"

LEGACY_FILES_BROWSE = "files.browse"
LEGACY_FILES_COPY = "files.copy"
LEGACY_MONITORS_LIST = "monitors.list"
LEGACY_MONITORS_PREVIEW = "monitors.preview"
LEGACY_PROCESSES_CONTROL = "processes.control"
LEGACY_PROCESSES_LIST = "processes.list"
LEGACY_WINDOWS_LIST = "windows.list"
LEGACY_WINDOWS_PREVIEW = "windows.preview"


def device_capabilities(status: dict) -> set[str]:
    """Return the normalized capability set from status data."""
    capabilities = nested_get(status, "device", "capabilities", default=[]) or []
    return {str(capability) for capability in capabilities}


def has_any_capability(status: dict, *capabilities: str) -> bool:
    """Check whether any capability is present."""
    available = device_capabilities(status)
    return any(capability in available for capability in capabilities)


def status_has_section(status: dict, section: str) -> bool:
    """Check if a status section exists and is populated."""
    value = nested_get(status, section)
    return value is not None


def is_platform(status: dict, platform_name: str) -> bool:
    """Check the platform name from status."""
    platform = str(nested_get(status, "device", "platform", default="")).lower()
    return platform == platform_name.lower()


def supports_audio(status: dict) -> bool:
    """Return whether audio entities should exist."""
    return has_any_capability(status, CORE_AUDIO_OUTPUT) or status_has_section(status, "audio")


def supports_media(status: dict) -> bool:
    """Return whether media entities should exist."""
    return has_any_capability(status, CORE_MEDIA) or status_has_section(status, "media")


def supports_bluetooth(status: dict) -> bool:
    """Return whether Bluetooth entities should exist."""
    return has_any_capability(status, CORE_BLUETOOTH_LIST) or status_has_section(
        status, "bluetooth"
    )


def supports_app_launch(status: dict) -> bool:
    """Return whether application launch services should exist."""
    return has_any_capability(status, CORE_APPLICATIONS_LAUNCH)


def supports_system_metrics(status: dict) -> bool:
    """Return whether system telemetry entities should exist."""
    return has_any_capability(
        status,
        CORE_SYSTEM_CPU,
        CORE_SYSTEM_MEMORY,
        CORE_SYSTEM_UPTIME,
    ) or status_has_section(status, "system")


def supports_storage_metrics(status: dict) -> bool:
    """Return whether storage telemetry entities should exist."""
    return has_any_capability(status, CORE_SYSTEM_STORAGE) or status_has_section(status, "storage")


def supports_network_metrics(status: dict) -> bool:
    """Return whether network telemetry entities should exist."""
    return has_any_capability(status, CORE_SYSTEM_NETWORK) or status_has_section(status, "network")


def supports_service_inventory(status: dict) -> bool:
    """Return whether curated service inventory entities should exist."""
    return has_any_capability(status, WINDOWS_SERVICES_LIST) or status_has_section(
        status, "services"
    )


def supports_service_control(status: dict) -> bool:
    """Return whether curated service control services should exist."""
    return has_any_capability(status, WINDOWS_SERVICES_CONTROL)


def service_inventory_items(status: dict) -> list[dict]:
    """Return curated service inventory entries when available."""
    services = nested_get(status, "serviceInventory", "services", default=[]) or []
    return [service for service in services if isinstance(service, dict)]


def supports_windows_inventory(status: dict) -> bool:
    """Return whether window inventory entities should exist."""
    return has_any_capability(
        status,
        WINDOWS_WINDOWS_LIST,
        LEGACY_WINDOWS_LIST,
    ) or status_has_section(status, "windows")


def supports_monitor_inventory(status: dict) -> bool:
    """Return whether monitor inventory entities should exist."""
    return has_any_capability(
        status,
        WINDOWS_MONITORS_LIST,
        LEGACY_MONITORS_LIST,
    ) or status_has_section(status, "monitors")


def supports_process_inventory(status: dict) -> bool:
    """Return whether process inventory entities should exist."""
    return has_any_capability(
        status,
        WINDOWS_PROCESSES_LIST,
        LEGACY_PROCESSES_LIST,
    ) or status_has_section(status, "processes")


def supports_process_control(status: dict) -> bool:
    """Return whether process control services should exist."""
    return has_any_capability(
        status,
        WINDOWS_PROCESSES_CONTROL,
        LEGACY_PROCESSES_CONTROL,
    )


def supports_file_browse(status: dict) -> bool:
    """Return whether file browse services should exist."""
    return has_any_capability(
        status,
        WINDOWS_FILES_BROWSE,
        LEGACY_FILES_BROWSE,
    )


def supports_file_copy(status: dict) -> bool:
    """Return whether file copy services should exist."""
    return has_any_capability(
        status,
        WINDOWS_FILES_COPY,
        LEGACY_FILES_COPY,
    )


def supports_desktop_preview(status: dict) -> bool:
    """Return whether desktop preview entities should exist."""
    return has_any_capability(
        status,
        CORE_DESKTOP_PREVIEW,
        WINDOWS_MONITORS_PREVIEW,
        LEGACY_MONITORS_PREVIEW,
    )


def supports_active_window_preview(status: dict) -> bool:
    """Return whether active-window preview entities should exist."""
    return has_any_capability(
        status,
        WINDOWS_WINDOWS_PREVIEW,
        LEGACY_WINDOWS_PREVIEW,
    ) and supports_windows_inventory(status)


def supported_power_actions(status: dict) -> set[str]:
    """Return the supported power action names from status."""
    actions = nested_get(status, "power", "supportedActions", default=[]) or []
    return {str(action) for action in actions}
