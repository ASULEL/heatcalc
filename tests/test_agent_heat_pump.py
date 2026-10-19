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
        "salt_temp_high": 540,
        "salt_temp_low": 300,
        "waste_heat_temp": 30,
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
    assert display["electrical_power"] == {"value": 177.37, "unit": "MWe"}
    assert display["heat_energy"] == {"value": 1844.69, "unit": "MWht"}
    assert display["electricity_consumption"] == {"value": 1419.0, "unit": "MWhe"}
    assert display["electricity_cost"] == {"value": 496648.57, "unit": "元"}
    assert display["cop"] == {"value": 1.3, "unit": "无量纲"}


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

    assert storage["salt_mass"] == pytest.approx(6148.982237560703)
    assert format_result_for_display(storage) == {
        "salt_mass": {"value": 6148.98, "unit": "t"},
    }
