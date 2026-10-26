"""直接调用 COP 计算函数的示例。"""

from heatcalc.cop import calculate_cop


def test_calculate_cop():
    # 压力和压降使用 kPa，温度和端差使用 ℃，功率使用 kW，效率为小数。
    result = calculate_cop(
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
    print(result)
