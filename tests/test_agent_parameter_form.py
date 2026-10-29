import pytest

from heatcalc.agent.parameter_specs import build_parameter_form
from heatcalc.agent.tool import (
    ALL_TOOLS,
    calculate_heat_pump_cop,
    calculate_heat_pump_cost,
    calculate_heat_pump_mass_flow,
    calculate_salt_mass,
    calculate_steam_flow_from_renewable_power,
)


def test_renewable_parameter_form_uses_chinese_labels_and_units():
    form = build_parameter_form(
        calculate_steam_flow_from_renewable_power,
        {"renewable_power": 8000},
    )

    assert form[0] == {
        "name": "renewable_power",
        "label": "风电或光伏功率",
        "unit": "kW",
        "group": "风光与电加热参数",
        "advanced": False,
        "value": 8000,
        "required": True,
    }


def test_salt_mass_form_uses_context_specific_power_label():
    form = build_parameter_form(calculate_salt_mass)

    assert form[0]["label"] == "充热端热功率"
    assert form[0]["unit"] == "kW"
    assert form[0]["group"] == "储热系统参数"


def test_heat_pump_cop_form_uses_excel_example_defaults():
    form = build_parameter_form(calculate_heat_pump_cop)
    fields = {field["name"]: field for field in form}

    assert fields["working_fluid"]["value"] == "air"
    assert fields["working_fluid"]["options"] == [
        {"value": "air", "label": "air（空气）"},
    ]
    assert fields["charging_power"]["value"] == 100
    assert fields["charging_power"]["unit"] == "MWt"
    assert fields["charging_power"]["toToolFactor"] == 1000
    assert fields["compressor_inlet_pressure"]["value"] == 2.7
    assert fields["compressor_inlet_pressure"]["unit"] == "MPa"
    assert fields["compressor_inlet_pressure"]["toToolFactor"] == 1000
    assert fields["expander_outlet_pressure"]["value"] == 2.95
    assert "compressor_mechanical_loss" not in fields or fields["compressor_mechanical_loss"]["value"] is None


@pytest.mark.parametrize(
    "tool",
    [calculate_heat_pump_cop, calculate_heat_pump_cost, calculate_heat_pump_mass_flow],
    ids=lambda tool: tool.name,
)
def test_heat_pump_inputs_keep_display_units_and_known_values(tool):
    form = build_parameter_form(tool, {
        "compressor_inlet_pressure": 2700,
        "compressor_outlet_pressure": 11500,
        "expander_outlet_pressure": 2950,
        "compressor_mechanical_loss": 0,
    })
    fields = {field["name"]: field for field in form}

    assert fields["compressor_inlet_pressure"]["value"] == 2.7
    assert fields["compressor_outlet_pressure"]["value"] == 11.5
    assert fields["expander_outlet_pressure"]["value"] == 2.95
    assert fields["expander_outlet_pressure"]["unit"] == "MPa"
    assert fields["expander_outlet_pressure"]["toToolFactor"] == 1000
    assert fields["compressor_mechanical_loss"]["value"] == 0
    assert fields["compressor_inlet_pressure"]["advanced"] is True


def test_cop_example_values_do_not_fill_other_heat_pump_forms():
    for tool in [calculate_heat_pump_cost, calculate_heat_pump_mass_flow]:
        fields = build_parameter_form(tool)
        assert all(field["value"] is None for field in fields)
        assert all("isDefault" not in field for field in fields)


def test_cop_known_power_converts_from_tool_units_and_overrides_example():
    fields = {field["name"]: field for field in build_parameter_form(
        calculate_heat_pump_cop, {"charging_power": 123456},
    )}

    assert fields["charging_power"]["value"] == 123.456
    assert fields["charging_power"]["unit"] == "MWt"
    assert not fields["charging_power"].get("isDefault", False)


def test_schema_examples_keep_inputs_required_and_table_tools_direct_call():
    for tool in ALL_TOOLS:
        fields = build_parameter_form(tool)
        assert all(field["required"] for field in fields)
        if tool.name == "calculate_economic_scheme":
            assert all(field["toolName"] == tool.name for field in fields)
        else:
            assert all("toolName" not in field for field in fields)
