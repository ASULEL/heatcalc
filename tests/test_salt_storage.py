import pytest

from heatcalc.electric_heater import ElectricHeaterStrategy
from heatcalc.salt_storage import calculate_salt_mass


def test_one_mwh_requires_ten_tonnes_of_salt():
    # 1 MWh = 3,600,000 kJ；每吨熔盐在 240 K 温差下储热 360,000 kJ。
    assert calculate_salt_mass(1000, 1, 1.5, 240) == pytest.approx(10)


@pytest.mark.parametrize("charging_power, storage_duration", [(0, 8), (1000, 0)])
def test_zero_storage_energy_requires_zero_salt(charging_power, storage_duration):
    assert calculate_salt_mass(charging_power, storage_duration, 1.5, 240) == 0


@pytest.mark.parametrize(
    "parameter, value",
    [
        ("charging_power", -1),
        ("charging_power", float("inf")),
        ("storage_duration", -1),
        ("storage_duration", float("nan")),
        ("salt_specific_heat", 0),
        ("salt_specific_heat", -1.5),
        ("salt_specific_heat", float("nan")),
        ("salt_temp_delta", 0),
        ("salt_temp_delta", -240),
        ("salt_temp_delta", float("inf")),
    ],
)
def test_invalid_storage_inputs_are_rejected(parameter, value):
    arguments = dict(
        charging_power=1000,
        storage_duration=8,
        salt_specific_heat=1.5,
        salt_temp_delta=240,
    )
    arguments[parameter] = value

    with pytest.raises(ValueError):
        calculate_salt_mass(**arguments)


def test_existing_strategy_storage_call_remains_compatible():
    heater = ElectricHeaterStrategy(0.985, 0.99, 0.99, 1.5, 240)

    assert heater.calculate_salt_mass(1000, 8) == pytest.approx(80)
