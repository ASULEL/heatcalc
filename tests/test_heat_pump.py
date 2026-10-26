import pytest

from heatcalc.pump_heater import HeatPumpStrategy


@pytest.fixture
def pump():
    return HeatPumpStrategy(
        400.0, 0.99, 0.99, 1.5, 240,
        salt_temp_low=310.0,
        cop_parameters={
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
        },
    )


@pytest.fixture
def conditions():
    return {
        "steam_pressure": 1.5,
        "steam_temp": 200,
        "feedwater_pressure": 0.1,
        "feedwater_temp": 20,
        "operating_hours": 8,
        "steam_supply_hours": 8,
        "electricity_price": 0.35,
    }


def test_forward_preserves_energy_calculation_and_returns_electrical_power(
    pump, conditions
):
    result = pump.calculate_cost_from_steam(**conditions, mass_flow=100 / 3.6)

    assert result == pytest.approx({
        "water_to_steam_power": 75332.71863791556,
        "sgs_input_power": 76093.6551898137,
        "charging_power": 76862.27796950878,
        "electrical_power": 44165.17634763042,
        "heat_energy": 614898.2237560702,
        "cop": 1.7403367160704801,
        "electricity_consumption": 353321.41078104335,
        "electricity_cost": 123662.49377336516,
    })


def test_electrical_power_converts_thermal_kw_using_calculated_cop(pump):
    cop = pump.calculate_cop(charging_power=100000)
    assert pump.electrical_power(100000, cop) == pytest.approx(57460.14496883728)
    assert pump.electrical_power(0, cop) == 0


def test_electrical_power_uses_supplied_cop_without_temperature_lookup(pump):
    pump.waste_heat_temp = 999

    assert pump.electrical_power(1300, cop=2) == pytest.approx(650)


@pytest.mark.parametrize("cop", [0, -1, float("inf"), float("nan")])
def test_electrical_power_rejects_invalid_supplied_cop(pump, cop):
    with pytest.raises(ValueError, match="COP"):
        pump.electrical_power(1300, cop)


def test_reverse_follows_known_budget_and_heat_balance(pump, conditions):
    result = pump.calculate_mass_flow_from_cost(**conditions, electricity_cost=2800)

    assert result == pytest.approx({
        "electricity_cost": 2800,
        "electricity_consumption": 8000,
        "electrical_power": 1000,
        "charging_power": 1740.3367160704804,
        "sgs_input_power": 1722.9333489097755,
        "water_to_steam_power": 1705.7040154206777,
        "heat_energy": 13922.693728563843,
        "cop": 1.7403367160704801,
        "mass_flow": 0.6289520403843724,
    })


@pytest.mark.parametrize("steam_supply_hours, operating_hours", [(8, 8), (24, 8), (16, 6)])
@pytest.mark.parametrize("mass_flow", [0, 1, 100 / 3.6])
def test_reverse_recovers_forward_flow_and_intermediate_results(
    pump, conditions, mass_flow, steam_supply_hours, operating_hours
):
    conditions.update(
        steam_supply_hours=steam_supply_hours,
        operating_hours=operating_hours,
    )
    forward = pump.calculate_cost_from_steam(**conditions, mass_flow=mass_flow)
    reverse = pump.calculate_mass_flow_from_cost(
        **conditions, electricity_cost=forward["electricity_cost"]
    )

    assert reverse["mass_flow"] == pytest.approx(mass_flow)
    for name, value in forward.items():
        assert reverse[name] == pytest.approx(value)


def test_forward_allows_zero_price(pump, conditions):
    conditions["electricity_price"] = 0
    result = pump.calculate_cost_from_steam(**conditions, mass_flow=1)

    assert result["electricity_cost"] == 0
    assert result["electrical_power"] > 0


def test_forward_supplies_24_hours_of_steam_from_8_hours_of_charging(pump, conditions):
    conditions["steam_supply_hours"] = 24
    result = pump.calculate_cost_from_steam(**conditions, mass_flow=100 / 3.6)

    assert result["water_to_steam_power"] == pytest.approx(75332.71863791556)
    assert result["sgs_input_power"] == pytest.approx(76093.6551898137)
    assert result["heat_energy"] == pytest.approx(1844694.6712682107)
    assert result["charging_power"] == pytest.approx(230586.83390852634)
    assert result["electrical_power"] == pytest.approx(132495.52904289126)
    assert result["electricity_consumption"] == pytest.approx(1059964.23234313)
    assert result["electricity_cost"] == pytest.approx(370987.4813200955)


def test_reverse_distributes_known_budget_over_steam_supply_hours(pump, conditions):
    conditions["steam_supply_hours"] = 24
    result = pump.calculate_mass_flow_from_cost(**conditions, electricity_cost=2800)

    assert result["electricity_consumption"] == pytest.approx(8000)
    assert result["electrical_power"] == pytest.approx(1000)
    assert result["heat_energy"] == pytest.approx(13922.693728563843)
    assert result["sgs_input_power"] == pytest.approx(574.3111163032585)
    assert result["water_to_steam_power"] == pytest.approx(568.5680051402259)
    assert result["mass_flow"] == pytest.approx(0.2096506801281241)


@pytest.mark.parametrize("reverse", [False, True])
def test_shorter_valley_hours_increase_power_without_changing_energy_or_flow(
    pump, conditions, reverse
):
    conditions["steam_supply_hours"] = 24
    if reverse:
        calculate = pump.calculate_mass_flow_from_cost
        demand = {"electricity_cost": 2800}
    else:
        calculate = pump.calculate_cost_from_steam
        demand = {"mass_flow": 100 / 3.6}
    eight_hours = calculate(**conditions, **demand)
    conditions["operating_hours"] = 4
    four_hours = calculate(**conditions, **demand)

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
def test_both_directions_require_positive_finite_durations(
    pump, conditions, reverse, parameter, value
):
    conditions[parameter] = value
    with pytest.raises(ValueError, match="时长"):
        if reverse:
            pump.calculate_mass_flow_from_cost(**conditions, electricity_cost=2800)
        else:
            pump.calculate_cost_from_steam(**conditions, mass_flow=1)


@pytest.mark.parametrize(
    "parameter, value",
    [
        ("electricity_price", 0),
        ("electricity_price", -0.35),
        ("electricity_price", float("inf")),
        ("electricity_cost", -1),
        ("electricity_cost", float("nan")),
        ("electricity_cost", float("inf")),
    ],
)
def test_reverse_rejects_invalid_budget_conditions(
    pump, conditions, parameter, value
):
    arguments = {**conditions, "electricity_cost": 2800, parameter: value}
    with pytest.raises(ValueError):
        pump.calculate_mass_flow_from_cost(**arguments)


@pytest.mark.parametrize("mass_flow", [-1, float("inf"), float("nan")])
def test_forward_rejects_invalid_flow(pump, conditions, mass_flow):
    with pytest.raises(ValueError):
        pump.calculate_cost_from_steam(**conditions, mass_flow=mass_flow)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "parameter, value",
    [
        ("heat_exchange_efficiency", 0),
        ("heat_exchange_efficiency", 1.1),
        ("storage_efficiency", -0.1),
        ("storage_efficiency", float("nan")),
    ],
)
def test_both_directions_reject_invalid_efficiency(
    pump, conditions, reverse, parameter, value
):
    setattr(pump, parameter, value)
    with pytest.raises(ValueError):
        if reverse:
            pump.calculate_mass_flow_from_cost(**conditions, electricity_cost=2800)
        else:
            pump.calculate_cost_from_steam(**conditions, mass_flow=1)


@pytest.mark.parametrize("temperature", [float("inf"), float("nan")])
def test_cop_rejects_invalid_temperature(pump, temperature):
    pump.waste_heat_temp = temperature
    with pytest.raises(ValueError):
        pump.calculate_cop(charging_power=100000)


def test_reverse_rejects_nonpositive_enthalpy_difference(pump, conditions):
    conditions["feedwater_pressure"] = conditions["steam_pressure"]
    conditions["feedwater_temp"] = conditions["steam_temp"]
    with pytest.raises(ValueError, match="蒸汽焓必须大于给水焓"):
        pump.calculate_mass_flow_from_cost(**conditions, electricity_cost=2800)
