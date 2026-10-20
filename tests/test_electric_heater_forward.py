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
        "steam_supply_hours": 8,
        "electricity_price": 0.35,
    }


def test_forward_preserves_existing_example_results(heater, steam_demand):
    result = heater.calculate_cost_from_steam(**steam_demand)

    assert result == pytest.approx({
        "water_to_steam_power": 75332.71863791556,
        "sgs_input_power": 76093.6551898137,
        "charging_power": 76862.27796950878,
        "electrical_power": 78032.76951219166,
        "heat_energy": 614898.2237560702,
        "electricity_consumption": 624262.1560975333,
        "electricity_cost": 218491.75463413665,
    })


def test_zero_flow_produces_zero_power_and_cost(heater, steam_demand):
    steam_demand["mass_flow"] = 0

    result = heater.calculate_cost_from_steam(**steam_demand)

    assert all(value == 0 for value in result.values())


def test_zero_price_produces_zero_cost(heater, steam_demand):
    steam_demand["electricity_price"] = 0

    result = heater.calculate_cost_from_steam(**steam_demand)

    assert result["electricity_cost"] == 0
    assert result["electrical_power"] > 0
    assert result["electricity_consumption"] > 0


def test_24_hour_supply_is_charged_within_8_valley_hours(heater, steam_demand):
    steam_demand["steam_supply_hours"] = 24

    result = heater.calculate_cost_from_steam(**steam_demand)

    assert result["water_to_steam_power"] == pytest.approx(75332.71863791556)
    assert result["heat_energy"] == pytest.approx(1844694.6712682107)
    assert result["charging_power"] == pytest.approx(230586.83390852634)
    assert result["electrical_power"] == pytest.approx(234098.30853657497)
    assert result["electricity_consumption"] == pytest.approx(1872786.4682925998)
    assert result["electricity_cost"] == pytest.approx(655475.2639024099)


@pytest.mark.parametrize("reverse", [False, True])
def test_shorter_charging_duration_increases_power_without_changing_energy(
    heater, steam_demand, reverse
):
    conditions = {key: value for key, value in steam_demand.items() if key != "mass_flow"}
    conditions["steam_supply_hours"] = 24
    if reverse:
        calculate = heater.calculate_mass_flow_from_cost
        demand = {"electricity_cost": 2800}
    else:
        calculate = heater.calculate_cost_from_steam
        demand = {"mass_flow": steam_demand["mass_flow"]}

    eight_hours = calculate(**conditions, **demand)
    four_hours = calculate(**{**conditions, "operating_hours": 4}, **demand)

    for field in ("charging_power", "electrical_power"):
        assert four_hours[field] == pytest.approx(eight_hours[field] * 2)
    for field in ("water_to_steam_power", "sgs_input_power", "heat_energy",
                  "electricity_consumption", "electricity_cost"):
        assert four_hours[field] == pytest.approx(eight_hours[field])
    if reverse:
        assert four_hours["mass_flow"] == pytest.approx(eight_hours["mass_flow"])


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("parameter", ["operating_hours", "steam_supply_hours"])
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_both_calculations_reject_invalid_durations(
    heater, steam_demand, reverse, parameter, value
):
    conditions = {key: value for key, value in steam_demand.items() if key != "mass_flow"}
    conditions[parameter] = value

    with pytest.raises(ValueError, match="时长"):
        if reverse:
            heater.calculate_mass_flow_from_cost(**conditions, electricity_cost=2800)
        else:
            heater.calculate_cost_from_steam(**conditions, mass_flow=1)


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
