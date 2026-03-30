from custom_components.easycontrolx.helpers import nested_get, normalize_optional_string


def test_nested_get_returns_nested_value() -> None:
    data = {"outer": {"inner": {"value": 42}}}
    assert nested_get(data, "outer", "inner", "value") == 42


def test_nested_get_returns_default_for_missing_path() -> None:
    assert nested_get({"outer": {}}, "outer", "missing", default="fallback") == "fallback"


def test_normalize_optional_string_trims_values() -> None:
    assert normalize_optional_string("  test  ") == "test"


def test_normalize_optional_string_maps_blank_to_none() -> None:
    assert normalize_optional_string("   ") is None
