"""COP 调用示例和压缩机进口管道压降回归测试。"""

import pytest

import heatcalc.cop as cop_module
from heatcalc.cop import calculate_cop


@pytest.fixture
def cop_parameters():
    # 压力和压降使用 kPa，温度和端差使用 ℃，功率使用 kW，效率为小数。
    return dict(
        working_fluid="Air",
        waste_heat_temp=400.0,
        salt_temp_low=310.0,
        charging_power=100000.0,
        compressor_inlet_pressure=2700.0,
        compressor_outlet_pressure=11500.0,
        compressor_isentropic_efficiency=0.85,
        compressor_mechanical_loss=0.0,
        compressor_to_heat_release_pressure_drop=0.0,
        heat_release_temp_approach=10.0,
        heat_release_pressure_drop=200.0,
        heat_release_to_regenerator_pressure_drop=0.0,
        regenerator_temp_approach=20.0,
        regenerator_high_side_pressure_drop=200.0,
        regenerator_low_side_pressure_drop=200.0,
        regenerator_to_expander_pressure_drop=0.0,
        expander_outlet_pressure=2950.0,
        expander_isentropic_efficiency=0.92,
        expander_mechanical_loss=0.0,
        expander_to_heat_absorption_pressure_drop=0.0,
        heat_absorption_temp_approach=130.0,
        heat_absorption_pressure_drop=50.0,
        heat_absorption_to_regenerator_pressure_drop=0.0,
        regenerator_to_compressor_pressure_drop=0.0,
        motor_efficiency=0.98,
        gearbox_efficiency=0.985,
    )


def test_calculate_cop(cop_parameters):
    result = calculate_cop(**cop_parameters)
    assert result["cop"] == pytest.approx(1.7403367160704801)
    assert result["electrical_power"] == pytest.approx(57460.14496883728)
    print(result)


def test_compressor_uses_upstream_pressure_minus_pipe_drop(cop_parameters, monkeypatch):
    baseline = calculate_cop(**cop_parameters)
    entropy_pressures = []
    original_props = cop_module.PropsSI

    def record_props(output, first_name, first_value, second_name, second_value, fluid):
        if output == "S":
            entropy_pressures.append(first_value)
        return original_props(output, first_name, first_value, second_name, second_value, fluid)

    monkeypatch.setattr(cop_module, "PropsSI", record_props)
    result = calculate_cop(**{
        **cop_parameters,
        "regenerator_to_compressor_pressure_drop": 100.0,
    })

    # 此工况回热器低压侧出口为 2700 kPa，管道压降为 100 kPa。
    assert entropy_pressures[0] == pytest.approx(2_600_000.0)
    assert result["cop"] != pytest.approx(baseline["cop"])
    assert result["electrical_power"] != pytest.approx(baseline["electrical_power"])


def test_legacy_inlet_pressure_does_not_override_upstream_state(cop_parameters):
    parameters = {**cop_parameters, "regenerator_to_compressor_pressure_drop": 100.0}
    expected = calculate_cop(**parameters)
    result = calculate_cop(**{**parameters, "compressor_inlet_pressure": 5000.0})
    assert result == pytest.approx(expected)


@pytest.mark.parametrize("pressure_drop", [2700.0, 2800.0, float("nan"), float("inf")])
def test_invalid_derived_compressor_pressure_is_rejected(cop_parameters, pressure_drop):
    with pytest.raises(ValueError, match="压缩机进口压力"):
        calculate_cop(**{
            **cop_parameters,
            "regenerator_to_compressor_pressure_drop": pressure_drop,
        })
