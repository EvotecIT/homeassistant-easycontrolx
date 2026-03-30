from custom_components.easycontrolx.capabilities import (
    CORE_APPLICATIONS_LAUNCH,
    CORE_AUDIO_OUTPUT,
    CORE_BLUETOOTH_LIST,
    CORE_DESKTOP_PREVIEW,
    CORE_MEDIA,
    CORE_SYSTEM_CPU,
    CORE_SYSTEM_MEMORY,
    CORE_SYSTEM_NETWORK,
    CORE_SYSTEM_STORAGE,
    CORE_SYSTEM_UPTIME,
    LEGACY_FILES_BROWSE,
    LEGACY_FILES_COPY,
    LEGACY_MONITORS_LIST,
    LEGACY_MONITORS_PREVIEW,
    LEGACY_PROCESSES_CONTROL,
    LEGACY_PROCESSES_LIST,
    LEGACY_WINDOWS_LIST,
    LEGACY_WINDOWS_PREVIEW,
    WINDOWS_FILES_BROWSE,
    WINDOWS_FILES_COPY,
    WINDOWS_MONITORS_LIST,
    WINDOWS_PROCESSES_CONTROL,
    WINDOWS_PROCESSES_LIST,
    WINDOWS_SERVICES_CONTROL,
    WINDOWS_SERVICES_LIST,
    WINDOWS_WINDOWS_LIST,
    device_capabilities,
    has_any_capability,
    service_inventory_items,
    supports_active_window_preview,
    supports_app_launch,
    supports_audio,
    supports_bluetooth,
    supports_desktop_preview,
    supports_file_browse,
    supports_file_copy,
    supports_media,
    supports_monitor_inventory,
    supports_network_metrics,
    supports_process_control,
    supports_process_inventory,
    supports_service_control,
    supports_service_inventory,
    supports_storage_metrics,
    supports_system_metrics,
    supports_windows_inventory,
)


def test_device_capabilities_reads_status_payload() -> None:
    status = {"device": {"capabilities": [CORE_MEDIA, CORE_AUDIO_OUTPUT]}}
    assert device_capabilities(status) == {CORE_MEDIA, CORE_AUDIO_OUTPUT}


def test_has_any_capability_matches_when_present() -> None:
    status = {"device": {"capabilities": [CORE_MEDIA]}}
    assert has_any_capability(status, CORE_MEDIA, CORE_AUDIO_OUTPUT) is True


def test_supports_windows_inventory_handles_legacy_names() -> None:
    status = {"device": {"capabilities": [LEGACY_WINDOWS_LIST]}}
    assert supports_windows_inventory(status) is True


def test_supports_windows_inventory_handles_namespaced_names() -> None:
    status = {"device": {"capabilities": [WINDOWS_WINDOWS_LIST]}}
    assert supports_windows_inventory(status) is True


def test_supports_monitor_inventory_handles_legacy_names() -> None:
    status = {"device": {"capabilities": [LEGACY_MONITORS_LIST]}}
    assert supports_monitor_inventory(status) is True


def test_supports_monitor_inventory_handles_namespaced_names() -> None:
    status = {"device": {"capabilities": [WINDOWS_MONITORS_LIST]}}
    assert supports_monitor_inventory(status) is True


def test_supports_desktop_preview_accepts_core_or_legacy_preview() -> None:
    assert supports_desktop_preview({"device": {"capabilities": [CORE_DESKTOP_PREVIEW]}}) is True
    assert supports_desktop_preview({"device": {"capabilities": [LEGACY_MONITORS_PREVIEW]}}) is True


def test_supports_active_window_preview_requires_preview_and_windows() -> None:
    status = {
        "device": {
            "capabilities": [LEGACY_WINDOWS_LIST, LEGACY_WINDOWS_PREVIEW],
        }
    }
    assert supports_active_window_preview(status) is True


def test_supports_media_audio_and_bluetooth_are_capability_driven() -> None:
    status = {
        "device": {
            "capabilities": [CORE_MEDIA, CORE_AUDIO_OUTPUT, CORE_BLUETOOTH_LIST],
        }
    }
    assert supports_media(status) is True
    assert supports_audio(status) is True
    assert supports_bluetooth(status) is True


def test_support_helpers_can_fall_back_to_status_sections() -> None:
    status = {
        "audio": {"isAvailable": True},
        "media": {"isAvailable": True},
        "bluetooth": {"isAvailable": True},
        "processes": {"itemCount": 42},
        "windows": {"itemCount": 3},
        "monitors": {"itemCount": 2},
    }
    assert supports_audio(status) is True
    assert supports_media(status) is True
    assert supports_bluetooth(status) is True
    assert supports_process_inventory(status) is True
    assert supports_windows_inventory(status) is True
    assert supports_monitor_inventory(status) is True


def test_supports_app_launch_is_capability_driven() -> None:
    status = {"device": {"capabilities": [CORE_APPLICATIONS_LAUNCH]}}
    assert supports_app_launch(status) is True


def test_supports_system_metrics_accept_capabilities() -> None:
    status = {
        "device": {
            "capabilities": [
                CORE_SYSTEM_CPU,
                CORE_SYSTEM_MEMORY,
                CORE_SYSTEM_UPTIME,
            ]
        }
    }
    assert supports_system_metrics(status) is True


def test_supports_system_metrics_can_fall_back_to_status_section() -> None:
    status = {"system": {"cpu": {"usagePercent": 7.5}}}
    assert supports_system_metrics(status) is True


def test_supports_storage_and_network_metrics_accept_capabilities() -> None:
    status = {"device": {"capabilities": [CORE_SYSTEM_STORAGE, CORE_SYSTEM_NETWORK]}}
    assert supports_storage_metrics(status) is True
    assert supports_network_metrics(status) is True


def test_supports_storage_and_network_metrics_can_fall_back_to_status_sections() -> None:
    status = {
        "storage": {"itemCount": 3},
        "network": {"itemCount": 2},
    }
    assert supports_storage_metrics(status) is True
    assert supports_network_metrics(status) is True


def test_supports_service_helpers_accept_namespaced_capabilities() -> None:
    status = {"device": {"capabilities": [WINDOWS_SERVICES_LIST, WINDOWS_SERVICES_CONTROL]}}
    assert supports_service_inventory(status) is True
    assert supports_service_control(status) is True


def test_supports_service_inventory_can_fall_back_to_status_section() -> None:
    status = {"services": {"itemCount": 5}}
    assert supports_service_inventory(status) is True


def test_service_inventory_items_reads_enriched_inventory_payload() -> None:
    status = {
        "serviceInventory": {
            "services": [
                {"serviceName": "EasyControlX Windows Agent"},
                {"serviceName": "Spooler"},
            ]
        }
    }
    assert service_inventory_items(status) == [
        {"serviceName": "EasyControlX Windows Agent"},
        {"serviceName": "Spooler"},
    ]


def test_supports_process_helpers_accept_legacy_and_namespaced_capabilities() -> None:
    legacy_status = {"device": {"capabilities": [LEGACY_PROCESSES_LIST, LEGACY_PROCESSES_CONTROL]}}
    namespaced_status = {
        "device": {"capabilities": [WINDOWS_PROCESSES_LIST, WINDOWS_PROCESSES_CONTROL]}
    }

    assert supports_process_inventory(legacy_status) is True
    assert supports_process_control(legacy_status) is True
    assert supports_process_inventory(namespaced_status) is True
    assert supports_process_control(namespaced_status) is True


def test_supports_file_helpers_accept_legacy_and_namespaced_capabilities() -> None:
    legacy_status = {"device": {"capabilities": [LEGACY_FILES_BROWSE, LEGACY_FILES_COPY]}}
    namespaced_status = {"device": {"capabilities": [WINDOWS_FILES_BROWSE, WINDOWS_FILES_COPY]}}

    assert supports_file_browse(legacy_status) is True
    assert supports_file_copy(legacy_status) is True
    assert supports_file_browse(namespaced_status) is True
    assert supports_file_copy(namespaced_status) is True
