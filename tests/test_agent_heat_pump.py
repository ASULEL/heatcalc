import pytest
from pydantic import ValidationError

from heatcalc.agent.formatting import format_result_for_display
from heatcalc.agent.tools import ALL_TOOLS


@pytest.fixture
def tool_conditions():
    return {
        "steam_pressure": 1.5,
        "steam_temp": 200,
        "feedwater_pressure": 0.1,
        "feedwater_temp": 20,
        "operating_hours": 8,
        "steam_supply_hours": 24,
        "electricity_price": 0.35,
        "heat_exchange_efficiency": 0.99,
        "storage_efficiency": 0.99,
        "salt_specific_heat": 1.5,
        "salt_temp_high": 550,
        "salt_temp_low": 310,
        "waste_heat_temp": 400,
        "working_fluid": "Air",
        "compressor_inlet_pressure": 2700,
        "compressor_outlet_pressure": 11500,
        "compressor_isentropic_efficiency": 0.85,
        "compressor_mechanical_loss": 0,
        "compressor_to_heat_release_pressure_drop": 0,
        "heat_release_temp_approach": 10,
        "heat_release_pressure_drop": 200,
        "heat_release_to_regenerator_pressure_drop": 0,
        "regenerator_temp_approach": 20,
        "regenerator_high_side_pressure_drop": 200,
        "regenerator_low_side_pressure_drop": 200,
        "regenerator_to_expander_pressure_drop": 0,
        "expander_outlet_pressure": 2950,
        "expander_isentropic_efficiency": 0.92,
        "expander_mechanical_loss": 0,
        "expander_to_heat_absorption_pressure_drop": 0,
        "heat_absorption_temp_approach": 130,
        "heat_absorption_pressure_drop": 50,
        "heat_absorption_to_regenerator_pressure_drop": 0,
        "regenerator_to_compressor_pressure_drop": 0,
        "motor_efficiency": 0.98,
        "gearbox_efficiency": 0.985,
    }


def test_registered_heat_pump_tools_round_trip_and_display_units(tool_conditions):
    tools = {tool.name: tool for tool in ALL_TOOLS}
    forward = tools["calculate_heat_pump_cost"].invoke({
        **tool_conditions,
        "mass_flow": 100 / 3.6,
    })
    reverse = tools["calculate_heat_pump_mass_flow"].invoke({
        **tool_conditions,
        "electricity_cost": forward["electricity_cost"],
    })

    assert reverse["mass_flow"] == pytest.approx(100 / 3.6)
    for name, value in forward.items():
        assert reverse[name] == pytest.approx(value)

    display = format_result_for_display(reverse)
    assert display["mass_flow"] == {"value": 100.0, "unit": "t/h"}
    assert display["electrical_power"] == {"value": 132.5, "unit": "MWe"}
    assert display["heat_energy"] == {"value": 1844.69, "unit": "MWht"}
    assert display["electricity_consumption"] == {"value": 1059.96, "unit": "MWhe"}
    assert display["electricity_cost"] == {"value": 370987.48, "unit": "元"}
    assert display["cop"] == {"value": 1.74, "unit": "无量纲"}


@pytest.mark.parametrize(
    "tool_name, demand",
    [
        ("calculate_heat_pump_cost", {"mass_flow": 1}),
        ("calculate_heat_pump_mass_flow", {"electricity_cost": 2800}),
    ],
)
def test_heat_pump_tools_require_explicit_supply_duration(
    tool_conditions, tool_name, demand
):
    tools = {tool.name: tool for tool in ALL_TOOLS}
    tool_conditions.pop("steam_supply_hours")
    with pytest.raises(ValidationError, match="steam_supply_hours"):
        tools[tool_name].invoke({**tool_conditions, **demand})


def test_heat_pump_reverse_can_supply_original_power_to_storage_tool(tool_conditions):
    tools = {tool.name: tool for tool in ALL_TOOLS}
    reverse = tools["calculate_heat_pump_mass_flow"].invoke({
        **tool_conditions,
        "electricity_cost": 165549.52178048046,
    })
    storage = tools["calculate_salt_mass"].invoke({
        "charging_power": reverse["charging_power"],
        "storage_duration": 8,
        "salt_specific_heat": 1.5,
        "salt_temp_high": 540,
        "salt_temp_low": 300,
    })

    assert storage["salt_mass"] == pytest.approx(8231.768888070852)
    assert format_result_for_display(storage) == {
        "salt_mass": {"value": 8231.77, "unit": "t"},
    }
