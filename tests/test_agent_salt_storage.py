import pytest

from heatcalc.agent.formatting import format_result_for_display
from heatcalc.agent.tools import (
    ALL_TOOLS,
    calculate_electric_heater_cost,
    calculate_mass_flow,
    calculate_salt_mass,
)


def test_storage_tool_is_registered_with_only_storage_parameters():
    assert calculate_salt_mass in ALL_TOOLS
    assert set(calculate_salt_mass.args) == {
        "charging_power",
        "storage_duration",
        "salt_specific_heat",
        "salt_temp_high",
        "salt_temp_low",
    }


def test_standalone_storage_tool_displays_tonnes():
    result = calculate_salt_mass.invoke({
        "charging_power": 1000,
        "storage_duration": 8,
        "salt_specific_heat": 1.5,
        "salt_temp_high": 540,
        "salt_temp_low": 300,
    })

    assert result == {"salt_mass": pytest.approx(80)}
    assert format_result_for_display(result) == {
        "salt_mass": {"value": 80.0, "unit": "t"},
    }


@pytest.mark.parametrize(
    "salt_temp_high, salt_temp_low",
    [(300, 300), (300, 540), (float("inf"), 300), (540, float("nan"))],
)
def test_storage_tool_rejects_invalid_temperatures(salt_temp_high, salt_temp_low):
    with pytest.raises(ValueError):
        calculate_salt_mass.invoke({
            "charging_power": 1000,
            "storage_duration": 8,
            "salt_specific_heat": 1.5,
            "salt_temp_high": salt_temp_high,
            "salt_temp_low": salt_temp_low,
        })


@pytest.mark.parametrize(
    "tool, demand",
    [
        (calculate_electric_heater_cost, {"mass_flow": 100 / 3.6}),
        (calculate_mass_flow, {"electricity_cost": 218491.75463413665}),
    ],
)
def test_steam_tools_can_supply_charging_power_to_storage_tool(tool, demand):
    result = tool.invoke({
        "steam_pressure": 1.5,
        "steam_temp": 200,
        "feedwater_pressure": 0.1,
        "feedwater_temp": 20,
        "operating_hours": 8,
        "electricity_price": 0.35,
        "electrical_efficiency": 0.985,
        "heat_exchange_efficiency": 0.99,
        "storage_efficiency": 0.99,
        "salt_specific_heat": 1.5,
        "salt_temp_high": 540,
        "salt_temp_low": 300,
        **demand,
    })
    display = format_result_for_display(result)
    assert display["electrical_power"] == {"value": 78.03, "unit": "MWe"}
    assert display["electricity_cost"] == {
        "value": 218491.75,
        "unit": "元",
    }
    if tool is calculate_mass_flow:
        assert display["mass_flow"] == {"value": 100.0, "unit": "t/h"}
    else:
        assert "mass_flow" not in display

    # 后续计算使用原始 kW 数值，避免展示舍入影响储盐计算精度。
    storage_result = calculate_salt_mass.invoke({
        "charging_power": result["charging_power"],
        "storage_duration": 8,
        "salt_specific_heat": 1.5,
        "salt_temp_high": 540,
        "salt_temp_low": 300,
    })
    storage_display = format_result_for_display(storage_result)
    assert storage_result["salt_mass"] == pytest.approx(6148.982237560703)
    assert storage_display["salt_mass"]["value"] == 6148.98
    assert storage_display["salt_mass"]["unit"] == "t"
