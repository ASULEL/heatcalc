import pytest
from pydantic import ValidationError

from heatcalc.agent.formatting import format_result_for_display
from heatcalc.agent.tools import ALL_TOOLS, calculate_salt_mass


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
        "electrical_efficiency": 0.985,
        "heat_exchange_efficiency": 0.99,
        "storage_efficiency": 0.99,
        "salt_specific_heat": 1.5,
        "salt_temp_high": 540,
        "salt_temp_low": 300,
    }


def test_registered_tools_recover_flow_for_different_durations(tool_conditions):
    tools = {tool.name: tool for tool in ALL_TOOLS}
    cost = tools["calculate_electric_heater_cost"].invoke({
        **tool_conditions,
        "mass_flow": 100 / 3.6,
    })
    flow = tools["calculate_mass_flow"].invoke({
        **tool_conditions,
        "electricity_cost": cost["electricity_cost"],
    })

    assert cost["electricity_cost"] == pytest.approx(655475.2639024099)
    assert flow["mass_flow"] * 3.6 == pytest.approx(100)
    for field, value in cost.items():
        assert flow[field] == pytest.approx(value)

    display = format_result_for_display(flow)
    assert display["mass_flow"] == {"value": 100.0, "unit": "t/h"}
    assert display["electrical_power"] == {"value": 234.1, "unit": "MWe"}
    assert display["heat_energy"] == {"value": 1844.69, "unit": "MWht"}
    assert display["electricity_consumption"] == {"value": 1872.79, "unit": "MWhe"}
    assert display["electricity_cost"] == {"value": 655475.26, "unit": "元"}


@pytest.mark.parametrize(
    "tool_name, demand",
    [
        ("calculate_electric_heater_cost", {"mass_flow": 1}),
        ("calculate_mass_flow", {"electricity_cost": 2800}),
    ],
)
def test_electric_heater_tools_require_supply_duration(
    tool_conditions, tool_name, demand
):
    tools = {tool.name: tool for tool in ALL_TOOLS}
    tool_conditions.pop("steam_supply_hours")

    with pytest.raises(ValidationError, match="steam_supply_hours"):
        tools[tool_name].invoke({**tool_conditions, **demand})


@pytest.mark.parametrize("charging_hours", [4, 8])
def test_storage_capacity_covers_supply_energy_regardless_of_charging_duration(
    tool_conditions, charging_hours
):
    tools = {tool.name: tool for tool in ALL_TOOLS}
    result = tools["calculate_electric_heater_cost"].invoke({
        **tool_conditions,
        "operating_hours": charging_hours,
        "mass_flow": 100 / 3.6,
    })
    storage = calculate_salt_mass.invoke({
        "charging_power": result["charging_power"],
        "storage_duration": charging_hours,
        "salt_specific_heat": 1.5,
        "salt_temp_high": 540,
        "salt_temp_low": 300,
    })

    assert storage["salt_mass"] == pytest.approx(18446.946712682107)
