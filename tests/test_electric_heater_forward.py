import pytest

from heatcalc.electric_heater import ElectricHeaterStrategy


@pytest.fixture
def heater():
    return ElectricHeaterStrategy(0.985, 0.99, 0.99, 1.5, 240)


@pytest.fixture
def steam_demand():
    return {
        "steam_pressure": 1.5,
        "steam_temp": 200,
        "feedwater_pressure": 0.1,
        "feedwater_temp": 20,
        "mass_flow": 100 / 3.6,
        "operating_hours": 8,
        "electricity_price": 0.35,
    }


def test_forward_preserves_existing_example_results(heater, steam_demand):
    result = heater.calculate_cost_from_steam(**steam_demand)

    assert result == pytest.approx({
        "water_to_steam_power": 75332.71863791556,
        "sgs_input_power": 76093.6551898137,
        "charging_power": 76862.27796950878,
        "electrical_power": 78032.76951219166,
        "electricity_consumption": 624262.1560975333,
        "electricity_cost": 218491.75463413665,
    })


def test_zero_flow_produces_zero_power_and_cost(heater, steam_demand):
    steam_demand["mass_flow"] = 0

    result = heater.calculate_cost_from_steam(**steam_demand)

    assert all(value == 0 for value in result.values())


@pytest.mark.parametrize("parameter", ["operating_hours", "electricity_price"])
def test_zero_hours_or_price_produces_zero_cost(heater, steam_demand, parameter):
    steam_demand[parameter] = 0

    result = heater.calculate_cost_from_steam(**steam_demand)

    assert result["electricity_cost"] == 0
    assert result["electrical_power"] > 0
    if parameter == "operating_hours":
        assert result["electricity_consumption"] == 0


@pytest.mark.parametrize(
    "parameter, value",
    [
        ("mass_flow", -1),
        ("mass_flow", float("inf")),
        ("operating_hours", -1),
        ("operating_hours", float("nan")),
        ("electricity_price", -0.35),
        ("electricity_price", float("inf")),
    ],
)
def test_invalid_forward_inputs_are_rejected(
    heater, steam_demand, parameter, value
):
    steam_demand[parameter] = value

    with pytest.raises(ValueError):
        heater.calculate_cost_from_steam(**steam_demand)


def test_forward_rejects_invalid_efficiency(heater, steam_demand):
    heater.electrical_efficiency = 0

    with pytest.raises(ValueError, match="电热效率"):
        heater.calculate_cost_from_steam(**steam_demand)


def test_forward_rejects_nonpositive_enthalpy_difference(heater, steam_demand):
    steam_demand.update(feedwater_pressure=1.5, feedwater_temp=200)

    with pytest.raises(ValueError, match="蒸汽焓必须大于给水焓"):
        heater.calculate_cost_from_steam(**steam_demand)
