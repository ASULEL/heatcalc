import pytest

from heatcalc.electric_heater import ElectricHeaterStrategy


@pytest.fixture
def heater():
    return ElectricHeaterStrategy(
        electrical_efficiency=0.985,
        heat_exchange_efficiency=0.99,
        storage_efficiency=0.99,
        salt_specific_heat=1.5,
        salt_temp_delta=240,
    )


@pytest.fixture
def operating_conditions():
    return {
        "steam_pressure": 1.5,
        "steam_temp": 200,
        "feedwater_pressure": 0.1,
        "feedwater_temp": 20,
        "operating_hours": 8,
        "electricity_price": 0.35,
    }


@pytest.mark.parametrize(
    "steam_pressure, steam_temp, feedwater_pressure, feedwater_temp, "
    "operating_hours, electricity_price, mass_flow",
    [
        (1.5, 200, 0.1, 20, 8, 0.35, 100 / 3.6),
        (3.0, 300, 0.5, 90, 6, 0.6, 10 / 3.6),
    ],
)
def test_reverse_recovers_forward_flow_and_intermediate_results(
    heater,
    steam_pressure,
    steam_temp,
    feedwater_pressure,
    feedwater_temp,
    operating_hours,
    electricity_price,
    mass_flow,
):
    conditions = {
        "steam_pressure": steam_pressure,
        "steam_temp": steam_temp,
        "feedwater_pressure": feedwater_pressure,
        "feedwater_temp": feedwater_temp,
        "operating_hours": operating_hours,
        "electricity_price": electricity_price,
    }
    forward = heater.calculate_cost_from_steam(**conditions, mass_flow=mass_flow)

    reverse = heater.calculate_mass_flow_from_cost(
        **conditions, electricity_cost=forward["electricity_cost"]
    )

    assert reverse["mass_flow"] == pytest.approx(mass_flow)
    for name, value in forward.items():
        assert reverse[name] == pytest.approx(value)


def test_existing_example_budget_produces_100_tonnes_per_hour(
    heater, operating_conditions
):
    result = heater.calculate_mass_flow_from_cost(
        **operating_conditions, electricity_cost=218491.75463413665
    )

    assert result["mass_flow"] * 3.6 == pytest.approx(100)


def test_zero_cost_produces_zero_flow_and_power(heater, operating_conditions):
    result = heater.calculate_mass_flow_from_cost(
        **operating_conditions, electricity_cost=0
    )

    assert all(value == 0 for value in result.values())


@pytest.mark.parametrize(
    "parameter, value",
    [
        ("electricity_cost", -1),
        ("electricity_cost", float("nan")),
        ("electricity_price", 0),
        ("electricity_price", -0.35),
        ("operating_hours", 0),
        ("operating_hours", -8),
        ("steam_pressure", 0),
        ("feedwater_pressure", -0.1),
        ("steam_temp", -273.15),
        ("feedwater_temp", float("inf")),
    ],
)
def test_invalid_inputs_are_rejected(
    heater, operating_conditions, parameter, value
):
    arguments = {**operating_conditions, "electricity_cost": 2800}
    arguments[parameter] = value

    with pytest.raises(ValueError):
        heater.calculate_mass_flow_from_cost(**arguments)


@pytest.mark.parametrize(
    "attribute, value",
    [
        ("electrical_efficiency", 0),
        ("electrical_efficiency", 1.1),
        ("storage_efficiency", -0.1),
        ("heat_exchange_efficiency", 1.1),
        ("heat_exchange_efficiency", float("nan")),
    ],
)
def test_invalid_efficiencies_are_rejected(
    heater, operating_conditions, attribute, value
):
    setattr(heater, attribute, value)

    with pytest.raises(ValueError):
        heater.calculate_mass_flow_from_cost(
            **operating_conditions, electricity_cost=2800
        )


@pytest.mark.parametrize("feedwater_temp", [200, 250])
def test_nonpositive_enthalpy_difference_is_rejected(
    heater, operating_conditions, feedwater_temp
):
    operating_conditions.update(
        feedwater_pressure=1.5, feedwater_temp=feedwater_temp
    )

    with pytest.raises(ValueError, match="蒸汽焓必须大于给水焓"):
        heater.calculate_mass_flow_from_cost(
            **operating_conditions, electricity_cost=2800
        )
