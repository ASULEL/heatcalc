"""供工具入口和热泵类复用的热泵系统 COP 计算函数。"""

from CoolProp.CoolProp import PropsSI


def calculate_cop(
    *,
    working_fluid: str,  # E2
    waste_heat_temp: float,  # E4
    salt_temp_low: float,  # E5
    charging_power: float,  # E9，接口单位为 kW

    # 压缩机
    compressor_inlet_pressure: float,  # E11，接口单位为 kPa
    compressor_outlet_pressure: float,  # E14，接口单位为 kPa
    compressor_isentropic_efficiency: float,  # E17
    compressor_mechanical_loss: float,  # E20

    # 放热器及连接管道
    compressor_to_heat_release_pressure_drop: float,  # E21
    heat_release_temp_approach: float,  # E22
    heat_release_pressure_drop: float,  # E29
    heat_release_to_regenerator_pressure_drop: float,  # E31

    # 回热器
    regenerator_temp_approach: float,  # E32
    regenerator_high_side_pressure_drop: float,  # E39
    regenerator_low_side_pressure_drop: float,  # E46

    # 膨胀机及连接管道
    regenerator_to_expander_pressure_drop: float,  # E48
    expander_outlet_pressure: float,  # E52，接口单位为 kPa
    expander_isentropic_efficiency: float,  # E55
    expander_mechanical_loss: float,  # E58

    # 吸热器及连接管道
    expander_to_heat_absorption_pressure_drop: float,  # E59
    heat_absorption_temp_approach: float,  # E60
    heat_absorption_pressure_drop: float,  # E67
    heat_absorption_to_regenerator_pressure_drop: float,  # E69
    regenerator_to_compressor_pressure_drop: float,  # E70

    # 传动效率
    motor_efficiency: float,  # E71
    gearbox_efficiency: float,  # E72
) -> dict[str, float]:
    """
    根据循环介质、运行工况和设备参数，计算热泵系统供热 COP。

    依次计算各设备的进出口状态、循环介质质量流量、设备功率和系统 COP。
    压力和压降统一使用 kPa，温度和端差使用 ℃，功率使用 kW，比焓使用 kJ/kg。

    :param working_fluid: 循环介质的 CoolProp 名称，如 "Air"、"Nitrogen"
    :param waste_heat_temp: 余热温度 (℃)
    :param salt_temp_low: 熔盐下限温度 (℃)
    :param charging_power: 热泵输出热功率 (kW)

    :param compressor_inlet_pressure: 压缩机进口压力 (kPa)
    :param compressor_outlet_pressure: 压缩机出口压力 (kPa)
    :param compressor_isentropic_efficiency: 压缩机等熵效率，取值 (0, 1]
    :param compressor_mechanical_loss: 压缩机机械损失功率 (kW)

    :param compressor_to_heat_release_pressure_drop: 压缩机出口至放热器进口管道压降 (kPa)
    :param heat_release_temp_approach: 放热器端差 (℃)
    :param heat_release_pressure_drop: 放热器压降 (kPa)
    :param heat_release_to_regenerator_pressure_drop: 放热器出口至回热器高压侧进口管道压降 (kPa)

    :param regenerator_temp_approach: 回热器端差 (℃)
    :param regenerator_high_side_pressure_drop: 回热器高压侧压降 (kPa)
    :param regenerator_low_side_pressure_drop: 回热器低压侧压降 (kPa)

    :param regenerator_to_expander_pressure_drop: 回热器高压侧出口至膨胀机进口管道压降 (kPa)
    :param expander_outlet_pressure: 膨胀机出口压力 (kPa)
    :param expander_isentropic_efficiency: 膨胀机等熵效率，取值 (0, 1]
    :param expander_mechanical_loss: 膨胀机机械损失功率 (kW)

    :param expander_to_heat_absorption_pressure_drop: 膨胀机出口至吸热器进口管道压降 (kPa)
    :param heat_absorption_temp_approach: 吸热器端差 (℃)
    :param heat_absorption_pressure_drop: 吸热器压降 (kPa)
    :param heat_absorption_to_regenerator_pressure_drop: 吸热器出口至回热器低压侧进口管道压降 (kPa)
    :param regenerator_to_compressor_pressure_drop: 回热器低压侧出口至压缩机进口管道压降 (kPa)

    :param motor_efficiency: 电动机效率，取值 (0, 1]
    :param gearbox_efficiency: 齿轮箱效率，取值 (0, 1]

    :return: 包含 cop（无量纲）、charging_power (kW)、electrical_power (kW)
        和 cycle_mass_flow (kg/s) 的字典。
    """
    # 1. 从吸热器开始，先确定各位置的温度和压力，再查焓值。
    # 先算出口温度：余热温度减去吸热器端差。
    heat_absorption_outlet_temp = (  # E65，吸热器出口温度，℃
        waste_heat_temp - heat_absorption_temp_approach
    )

    # 再算压力：扣除连接管道压降，得到进口压力；再扣除吸热器自身压降，得到出口压力。
    heat_absorption_inlet_pressure = (  # E61，吸热器进口压力，kPa
        expander_outlet_pressure - expander_to_heat_absorption_pressure_drop
    )
    heat_absorption_outlet_pressure = (  # E64，吸热器出口压力，kPa
        heat_absorption_inlet_pressure - heat_absorption_pressure_drop
    )

    # 最后根据出口温度和压力查比焓；CoolProp 的输入需将 ℃ 转为 K、kPa 转为 Pa。
    heat_absorption_outlet_enthalpy = PropsSI(  # E66，吸热器出口比焓，kJ/kg
        "H",
        "P", heat_absorption_outlet_pressure * 1000,
        "T", heat_absorption_outlet_temp + 273.15,
        working_fluid,
    ) / 1000  # J/kg 转为 kJ/kg

    # 回热器：先确定两侧进出口温度。
    # 低压侧接吸热器出口；高压侧接放热器出口。
    regenerator_low_side_inlet_temp = heat_absorption_outlet_temp  # E41，℃
    regenerator_high_side_inlet_temp = (  # E34，℃
        salt_temp_low + heat_release_temp_approach
    )
    # 低压侧被加热，其出口温度比高压侧进口温度低一个回热器端差。
    regenerator_low_side_outlet_temp = (  # E44，℃
        regenerator_high_side_inlet_temp - regenerator_temp_approach
    )
    # 高压侧被冷却，其出口温度比低压侧进口温度高一个回热器端差。
    regenerator_high_side_outlet_temp = (  # E37，℃
        regenerator_low_side_inlet_temp + regenerator_temp_approach
    )

    # 再算压力：低压侧从吸热器出口扣除连接管道和回热器低压侧压降。
    regenerator_low_side_inlet_pressure = (  # E40，计入 E69 管道压降，kPa
        heat_absorption_outlet_pressure - heat_absorption_to_regenerator_pressure_drop
    )
    regenerator_low_side_outlet_pressure = (  # E43，kPa
        regenerator_low_side_inlet_pressure - regenerator_low_side_pressure_drop
    )
    # 高压侧从压缩机出口依次扣除上游管道、放热器和回热器高压侧压降。
    regenerator_high_side_inlet_pressure = (  # E33，kPa
        compressor_outlet_pressure
        - compressor_to_heat_release_pressure_drop
        - heat_release_pressure_drop
        - heat_release_to_regenerator_pressure_drop
    )
    regenerator_high_side_outlet_pressure = (  # E36，kPa
        regenerator_high_side_inlet_pressure - regenerator_high_side_pressure_drop
    )

    # 最后根据各位置的温度和压力查比焓，单位统一转换为 kJ/kg。
    regenerator_low_side_inlet_enthalpy = PropsSI(  # E42，kJ/kg
        "H",
        "P", regenerator_low_side_inlet_pressure * 1000,
        "T", regenerator_low_side_inlet_temp + 273.15,
        working_fluid,
    ) / 1000
    regenerator_low_side_outlet_enthalpy = PropsSI(  # E45，kJ/kg
        "H",
        "P", regenerator_low_side_outlet_pressure * 1000,
        "T", regenerator_low_side_outlet_temp + 273.15,
        working_fluid,
    ) / 1000
    regenerator_high_side_inlet_enthalpy = PropsSI(  # E35，kJ/kg
        "H",
        "P", regenerator_high_side_inlet_pressure * 1000,
        "T", regenerator_high_side_inlet_temp + 273.15,
        working_fluid,
    ) / 1000
    regenerator_high_side_outlet_enthalpy = PropsSI(  # E38，kJ/kg
        "H",
        "P", regenerator_high_side_outlet_pressure * 1000,
        "T", regenerator_high_side_outlet_temp + 273.15,
        working_fluid,
    ) / 1000

    # 压缩机：进口温度取回热器低压侧出口温度，进出口压力使用传入值。
    compressor_inlet_temp = regenerator_low_side_outlet_temp  # E12，℃

    # 根据进口温度和压力查询进口比焓、比熵。
    compressor_inlet_enthalpy = PropsSI(  # E13，kJ/kg
        "H",
        "P", compressor_inlet_pressure * 1000,
        "T", compressor_inlet_temp + 273.15,
        working_fluid,
    ) / 1000
    compressor_inlet_entropy = PropsSI(  # 进口比熵，kJ/(kg·K)
        "S",
        "P", compressor_inlet_pressure * 1000,
        "T", compressor_inlet_temp + 273.15,
        working_fluid,
    ) / 1000

    # 等熵压缩时出口比熵等于进口比熵，用出口压力和进口比熵查等熵出口比焓。
    compressor_isentropic_outlet_enthalpy = PropsSI(  # kJ/kg
        "H",
        "P", compressor_outlet_pressure * 1000,
        "S", compressor_inlet_entropy * 1000,
        working_fluid,
    ) / 1000
    # 实际压缩焓升为等熵焓升除以等熵效率。
    compressor_outlet_enthalpy = (  # E16，kJ/kg
        compressor_inlet_enthalpy
        + (compressor_isentropic_outlet_enthalpy - compressor_inlet_enthalpy)
        / compressor_isentropic_efficiency
    )

    # 出口温度需由实际出口比焓和出口压力反查，不能直接通过端差确定。
    compressor_outlet_temp = PropsSI(  # E15，℃
        "T",
        "P", compressor_outlet_pressure * 1000,
        "H", compressor_outlet_enthalpy * 1000,
        working_fluid,
    ) - 273.15

    # 放热器：先确定进出口温度，进口衔接压缩机出口，出口由熔盐下限温度加端差确定。
    heat_release_inlet_temp = compressor_outlet_temp  # E24 = E15，℃
    heat_release_outlet_temp = (  # E27，℃
        salt_temp_low + heat_release_temp_approach
    )

    # 再算压力：先扣除压缩机至放热器的管道压降，再扣除放热器自身压降。
    heat_release_inlet_pressure = (  # E23，kPa
        compressor_outlet_pressure - compressor_to_heat_release_pressure_drop
    )
    heat_release_outlet_pressure = (  # E26，kPa
        heat_release_inlet_pressure - heat_release_pressure_drop
    )

    # 最后根据进出口各自的温度和压力查比焓，单位统一转换为 kJ/kg。
    heat_release_inlet_enthalpy = PropsSI(  # E25，kJ/kg
        "H",
        "P", heat_release_inlet_pressure * 1000,
        "T", heat_release_inlet_temp + 273.15,
        working_fluid,
    ) / 1000
    heat_release_outlet_enthalpy = PropsSI(  # E28，kJ/kg
        "H",
        "P", heat_release_outlet_pressure * 1000,
        "T", heat_release_outlet_temp + 273.15,
        working_fluid,
    ) / 1000

    # 膨胀机：进口温度取回热器高压侧出口温度。
    expander_inlet_temp = regenerator_high_side_outlet_temp  # E50，℃

    # 进口压力扣除回热器至膨胀机的管道压降，出口压力使用传入值。
    expander_inlet_pressure = (  # E49，kPa
        regenerator_high_side_outlet_pressure - regenerator_to_expander_pressure_drop
    )

    # 根据进口温度和压力查询进口比焓、比熵。
    expander_inlet_enthalpy = PropsSI(  # E51，kJ/kg
        "H",
        "P", expander_inlet_pressure * 1000,
        "T", expander_inlet_temp + 273.15,
        working_fluid,
    ) / 1000
    expander_inlet_entropy = PropsSI(  # 进口比熵，kJ/(kg·K)
        "S",
        "P", expander_inlet_pressure * 1000,
        "T", expander_inlet_temp + 273.15,
        working_fluid,
    ) / 1000

    # 等熵膨胀时出口比熵等于进口比熵，用出口压力和进口比熵查等熵出口比焓。
    expander_isentropic_outlet_enthalpy = PropsSI(  # kJ/kg
        "H",
        "P", expander_outlet_pressure * 1000,
        "S", expander_inlet_entropy * 1000,
        working_fluid,
    ) / 1000
    # 实际膨胀焓降为等熵焓降乘以等熵效率。
    expander_outlet_enthalpy = (  # E54，kJ/kg
        expander_inlet_enthalpy
        - (expander_inlet_enthalpy - expander_isentropic_outlet_enthalpy)
        * expander_isentropic_efficiency
    )

    # 根据实际出口比焓和出口压力反查出口温度。
    expander_outlet_temp = PropsSI(  # E53，℃
        "T",
        "P", expander_outlet_pressure * 1000,
        "H", expander_outlet_enthalpy * 1000,
        working_fluid,
    ) - 273.15

    # 回到吸热器：进口温度衔接膨胀机出口温度。
    heat_absorption_inlet_temp = expander_outlet_temp  # E62，℃

    # 进口压力沿用前面扣除膨胀机至吸热器管道压降后的值，再根据温度和压力查比焓。
    heat_absorption_inlet_enthalpy = PropsSI(  # E63，kJ/kg
        "H",
        "P", heat_absorption_inlet_pressure * 1000,
        "T", heat_absorption_inlet_temp + 273.15,
        working_fluid,
    ) / 1000

    # 2. 计算循环介质质量流量：输出热功率除以放热器进出口比焓差。
    # 功率为 kW（kJ/s），比焓差为 kJ/kg，相除直接得到 kg/s。
    cycle_mass_flow = charging_power / (  # E3，kg/s
        heat_release_inlet_enthalpy - heat_release_outlet_enthalpy
    )

    # 3. 计算设备功率：质量流量（kg/s）乘以比焓差（kJ/kg），直接得到 kW。
    # 压缩机消耗轴功，使用出口比焓减去进口比焓。
    compressor_power = (  # E19，压缩机轴功率，kW
        compressor_outlet_enthalpy - compressor_inlet_enthalpy
    ) * cycle_mass_flow

    # 膨胀机输出轴功，使用进口比焓减去出口比焓。
    expander_power = (  # E57，膨胀机轴功率，kW
        expander_inlet_enthalpy - expander_outlet_enthalpy
    ) * cycle_mass_flow

    # 放热器向熔盐放热，使用进口比焓减去出口比焓。
    heat_release_power = (  # E30，放热器热功率，kW
        heat_release_inlet_enthalpy - heat_release_outlet_enthalpy
    ) * cycle_mass_flow

    # 回热器换热功率按低压侧吸收的热量计算。
    regenerator_power = (  # E47，回热器热功率，kW
        regenerator_low_side_outlet_enthalpy - regenerator_low_side_inlet_enthalpy
    ) * cycle_mass_flow

    # 吸热器从余热中吸热，使用出口比焓减去进口比焓。
    heat_absorption_power = (  # E68，吸热器热功率，kW
        heat_absorption_outlet_enthalpy - heat_absorption_inlet_enthalpy
    ) * cycle_mass_flow

    # 系统输入电功率：压缩机轴功加两台机械损失、减去膨胀机回收轴功，
    # 再除以电动机效率和齿轮箱效率；机械损失与轴功率均使用 kW。
    electrical_power = (  # E8，系统输入电功率，kW
        compressor_power
        + compressor_mechanical_loss
        + expander_mechanical_loss
        - expander_power
    ) / (motor_efficiency * gearbox_efficiency)

    # 4. 计算系统供热 COP：输出热功率除以系统输入电功率，无量纲。
    cop = charging_power / electrical_power  # E10

    return {
        "cop": cop,
        "charging_power": charging_power,
        "electrical_power": electrical_power,
        "cycle_mass_flow": cycle_mass_flow,
    }
