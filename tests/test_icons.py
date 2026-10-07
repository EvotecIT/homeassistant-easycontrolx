"""Custom icon metadata is available through Home Assistant's loader."""

from homeassistant.helpers.icon import async_get_icons
from homeassistant.setup import async_setup_component

from custom_components.easycontrolx.button import BUTTONS, EasyControlXManagedServiceRestartButton
from custom_components.easycontrolx.sensor import SENSORS
from tests.test_platform_setup import _make_entry, _service_status


async def test_custom_icons_load_for_frontend(hass):
    assert await async_setup_component(hass, "easycontrolx", {})
    icons = (await async_get_icons(hass, "entity", {"easycontrolx"}))["easycontrolx"]
    for platform, descriptions in (("button", BUTTONS), ("sensor", SENSORS)):
        for description in descriptions:
            assert icons[platform][description.key]["default"].startswith("mdi:")
            assert description.icon is None
    assert icons["button"]["lock"]["default"] == "mdi:lock"
    status = _service_status("windows.services.list", "windows.services.control")
    restart = EasyControlXManagedServiceRestartButton(
        _make_entry(status), status["serviceInventory"]["services"][0]
    )
    assert icons["button"][restart.translation_key]["default"] == "mdi:restart"
    assert icons["sensor"]["cpu_usage"]["default"] == "mdi:cpu-64-bit"
