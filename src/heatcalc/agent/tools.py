from math import isfinite

from iapws import IAPWS95
from langchain_core.tools import tool

from heatcalc import salt_storage
from heatcalc.cop import calculate_cop
from heatcalc.electric_heater import ElectricHeaterStrategy
from heatcalc.pump_heater import HeatPumpStrategy


@tool
def calculate_electric_heater_cost(
        steam_pressure: float,
        steam_temp: float,
        feedwater_pressure: float,
        feedwater_temp: float,
        mass_flow: float,
        operating_hours: float,
        electricity_price: float,
        electrical_efficiency: float,
        heat_exchange_efficiency: float,
        storage_efficiency: float,
        salt_specific_heat: float,
        salt_temp_high: float,
        salt_temp_low: float,
        steam_supply_hours: float,
) -> dict:
    """
    计算电加热器满足指定蒸汽需求所需的购电成本。

    谷电充热时长和供汽时长需要分别提供，不能默认两者相同。

    :param steam_pressure: 蒸汽压力 (MPa)
    :param steam_temp: 蒸汽温度 (°C)
    :param feedwater_pressure: 给水压力 (MPa)
    :param feedwater_temp: 给水温度 (°C)
    :param mass_flow: 蒸汽质量流量 (kg/s)，若给定 t/h，需除以 3.6
    :param operating_hours: 谷电充热时长 (h)，必须大于零
    :param electricity_price: 电价 (元/kWh)
    :param electrical_efficiency: 电热效率 (0~1之间的小数)
    :param heat_exchange_efficiency: 换热效率 (0~1之间的小数)
    :param storage_efficiency: 储热效率 (0~1之间的小数)
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_high: 熔盐最高温度 (°C)
    :param salt_temp_low: 熔盐最低温度 (°C)
    :param steam_supply_hours: 供汽时长 (h)，必须大于零
    :return: 各阶段功率 (kW)、总供热量和耗电量 (kWh)、购电成本 (元)
    """
    salt_temp_delta = salt_temp_high - salt_temp_low
    # 1.创建计算蒸汽->电的实体
    electricHeaterStrategy = ElectricHeaterStrategy(
        electrical_efficiency,
        heat_exchange_efficiency,
        storage_efficiency,
        salt_specific_heat,
        salt_temp_delta
    )

    # 2.调用电加热器策略，返回原始单位的计算结果
    return electricHeaterStrategy.calculate_cost_from_steam(
        steam_pressure=steam_pressure,
        steam_temp=steam_temp,
        feedwater_pressure=feedwater_pressure,
        feedwater_temp=feedwater_temp,
        mass_flow=mass_flow,
        operating_hours=operating_hours,
        electricity_price=electricity_price,
        steam_supply_hours=steam_supply_hours,
    )


@tool
def calculate_steam_flow_from_renewable_power(
    renewable_power: float,
    renewable_conversion_efficiency: float,
    rated_electrical_power: float,
    electrical_efficiency: float,
    heat_exchange_efficiency: float,
    storage_efficiency: float,
    operating_hours: float,
    steam_supply_hours: float,
    steam_pressure: float,
    steam_temp: float,
    feedwater_pressure: float,
    feedwater_temp: float,
) -> dict[str, float]:
    """根据一个风电或光伏功率及转换效率，计算电加热器能够供给的蒸汽流量。

    renewable_power 表示本次输入的风电功率或光伏功率，按该功率在给定充热时段内运行。
    先乘以从该功率测点到加热器入口的转换效率，再限制电加热器实际输入电功率，
    然后计算充热功率、热量和供汽时段的热功率，
    乘以储热效率和换热效率得到制汽热功率，最后除以制汽比焓差得到蒸汽质量流量。
    转换效率只包含尚未扣除的转换和输送损失，与电热效率分别提供。
    若输入功率已经是加热器入口电功率，应明确提供转换效率 1.0，避免重复扣除损失。
    所有参数均须明确提供，缺少时先向用户询问，不能自行使用默认值。
    充热时长和供汽时长分别提供。功率使用 kW，用户提供 MW 时需乘以 1000。

    :param renewable_power: 本次风电或光伏功率 (kW)，按明确给出的功率测点取值，大于等于零
    :param renewable_conversion_efficiency: 从输入功率测点到加热器入口的总效率，
        大于 0 且不超过 1，使用小数，不包含电热效率
    :param rated_electrical_power: 电加热器额定电输入功率 (kW)，大于零
    :param electrical_efficiency: 电加热器热效率，大于 0 且不超过 1，使用小数
    :param heat_exchange_efficiency: SGS 换热效率，大于 0 且不超过 1，使用小数
    :param storage_efficiency: 储热效率，大于 0 且不超过 1，使用小数
    :param operating_hours: 风电或光伏供电的充热时长 (h)，必须大于零
    :param steam_supply_hours: 供汽时长 (h)，必须大于零
    :param steam_pressure: 蒸汽压力 (MPa)
    :param steam_temp: 蒸汽温度 (°C)
    :param feedwater_pressure: 给水压力 (MPa)
    :param feedwater_temp: 给水温度 (°C)
    :return: 各阶段功率 (kW)、充热量和用电量 (kWh)，
        以及供汽时段的平均蒸汽质量流量 mass_flow (kg/s)
    """
    # 1. 扣除输入功率测点至加热器入口尚未计入的转换和输送损失，单位 kW。
    available_electrical_power = renewable_power * renewable_conversion_efficiency
    # 2. 转换后的可用电功率受加热器额定电输入功率限制，单位 kW。
    electrical_power = min(available_electrical_power, rated_electrical_power)
    # 3. 输入电功率乘以电热效率得到充热功率；此处另计电加热器自身损失，单位 kW。
    charging_power = electrical_power * electrical_efficiency
    # 4. 充热功率 × 充热时长 → 总充热量，单位 kWh。
    heat_energy = charging_power * operating_hours
    # 5. 总充热量 ÷ 供汽时长 → 供汽时段热功率，单位 kW。
    supply_thermal_power = heat_energy / steam_supply_hours
    # 6. 扣除储热损失 → SGS 入口热功率，单位 kW。
    sgs_input_power = supply_thermal_power * storage_efficiency
    # 7. 扣除 SGS 换热损失 → 制汽热功率，单位 kW。
    water_to_steam_power = sgs_input_power * heat_exchange_efficiency
    # 8. 根据蒸汽、给水的压力和温度查比焓，计算比焓差，单位 kJ/kg。
    steam_state = IAPWS95(P=steam_pressure, T=steam_temp + 273.15)
    feedwater_state = IAPWS95(P=feedwater_pressure, T=feedwater_temp + 273.15)
    enthalpy_diff = steam_state.h - feedwater_state.h
    # 9. 制汽热功率 ÷ 制汽比焓差 → 平均蒸汽质量流量，单位 kg/s。
    mass_flow = water_to_steam_power / enthalpy_diff

    return {
        "electrical_power": electrical_power,
        "charging_power": charging_power,
        "heat_energy": heat_energy,
        "sgs_input_power": sgs_input_power,
        "water_to_steam_power": water_to_steam_power,
        # 记录加热器入口实际用电量，已扣除入口之前的损失并受额定功率限制。
        "electricity_consumption": electrical_power * operating_hours,
        "mass_flow": mass_flow,
    }


@tool
def calculate_heat_pump_cost(
        steam_pressure: float,
        steam_temp: float,
        feedwater_pressure: float,
        feedwater_temp: float,
        mass_flow: float,
        operating_hours: float,
        electricity_price: float,
        heat_exchange_efficiency: float,
        storage_efficiency: float,
        salt_specific_heat: float,
        salt_temp_high: float,
        salt_temp_low: float,
        waste_heat_temp: float,
        steam_supply_hours: float,
        working_fluid: str,
        compressor_inlet_pressure: float,
        compressor_outlet_pressure: float,
        compressor_isentropic_efficiency: float,
        compressor_mechanical_loss: float,
        compressor_to_heat_release_pressure_drop: float,
        heat_release_temp_approach: float,
        heat_release_pressure_drop: float,
        heat_release_to_regenerator_pressure_drop: float,
        regenerator_temp_approach: float,
        regenerator_high_side_pressure_drop: float,
        regenerator_low_side_pressure_drop: float,
        regenerator_to_expander_pressure_drop: float,
        expander_outlet_pressure: float,
        expander_isentropic_efficiency: float,
        expander_mechanical_loss: float,
        expander_to_heat_absorption_pressure_drop: float,
        heat_absorption_temp_approach: float,
        heat_absorption_pressure_drop: float,
        heat_absorption_to_regenerator_pressure_drop: float,
        regenerator_to_compressor_pressure_drop: float,
        motor_efficiency: float,
        gearbox_efficiency: float,
) -> dict[str, float]:
    """
    根据蒸汽需求和循环参数计算供热 COP，再计算热泵的购电成本。

    谷电充热时长和供汽时长需要分别提供，不能默认两者相同。
    循环参数均须由用户提供，缺少参数时先向用户询问，不能代入示例或默认值。

    :param steam_pressure: 蒸汽压力 (MPa)
    :param steam_temp: 蒸汽温度 (°C)
    :param feedwater_pressure: 给水压力 (MPa)
    :param feedwater_temp: 给水温度 (°C)
    :param mass_flow: 蒸汽质量流量 (kg/s)，若给定 t/h，需除以 3.6
    :param operating_hours: 谷电充热时长 (h)，必须大于零
    :param electricity_price: 电价 (元/kWh)
    :param heat_exchange_efficiency: 换热效率，大于 0 且不超过 1
    :param storage_efficiency: 储热效率，大于 0 且不超过 1
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_high: 熔盐最高温度 (°C)
    :param salt_temp_low: 熔盐最低温度 (°C)，必须低于最高温度
    :param waste_heat_temp: 余热温度 (°C)
    :param steam_supply_hours: 供汽时长 (h)，必须大于零
    :param working_fluid: 循环介质的 CoolProp 名称，如 Air、Nitrogen
    :param compressor_inlet_pressure: 兼容原字段 (kPa)，实际进口压力由回热器低压侧出口减去管道压降推导
    :param compressor_outlet_pressure: 压缩机出口压力 (kPa)
    :param compressor_isentropic_efficiency: 压缩机等熵效率，使用小数
    :param compressor_mechanical_loss: 压缩机机械损失功率 (kW)
    :param compressor_to_heat_release_pressure_drop: 压缩机出口至放热器进口管道压降 (kPa)
    :param heat_release_temp_approach: 放热器端差 (°C)
    :param heat_release_pressure_drop: 放热器压降 (kPa)
    :param heat_release_to_regenerator_pressure_drop: 放热器出口至回热器高压侧进口管道压降 (kPa)
    :param regenerator_temp_approach: 回热器端差 (°C)
    :param regenerator_high_side_pressure_drop: 回热器高压侧压降 (kPa)
    :param regenerator_low_side_pressure_drop: 回热器低压侧压降 (kPa)
    :param regenerator_to_expander_pressure_drop: 回热器高压侧出口至膨胀机进口管道压降 (kPa)
    :param expander_outlet_pressure: 膨胀机出口压力 (kPa)
    :param expander_isentropic_efficiency: 膨胀机等熵效率，使用小数
    :param expander_mechanical_loss: 膨胀机机械损失功率 (kW)
    :param expander_to_heat_absorption_pressure_drop: 膨胀机出口至吸热器进口管道压降 (kPa)
    :param heat_absorption_temp_approach: 吸热器端差 (°C)
    :param heat_absorption_pressure_drop: 吸热器压降 (kPa)
    :param heat_absorption_to_regenerator_pressure_drop: 吸热器出口至回热器低压侧进口管道压降 (kPa)
    :param regenerator_to_compressor_pressure_drop: 回热器低压侧出口至压缩机进口管道压降 (kPa)
    :param motor_efficiency: 电动机效率，使用小数
    :param gearbox_efficiency: 齿轮箱效率，使用小数
    :return: 包含各阶段功率 (kW)、耗电量 (kWh)、购电成本 (元)、
             供热量 (kWh) 和供热 COP（无量纲）的字典
    """
    # 1.先创建热泵实体
    salt_temp_delta = salt_temp_high - salt_temp_low
    heat_pump_strategy = HeatPumpStrategy(
        waste_heat_temp=waste_heat_temp,
        heat_exchange_efficiency=heat_exchange_efficiency,
        storage_efficiency=storage_efficiency,
        salt_specific_heat=salt_specific_heat,
        salt_temp_delta=salt_temp_delta,
        salt_temp_low=salt_temp_low,
        cop_parameters={
            "working_fluid": working_fluid,
            "compressor_inlet_pressure": compressor_inlet_pressure,
            "compressor_outlet_pressure": compressor_outlet_pressure,
            "compressor_isentropic_efficiency": compressor_isentropic_efficiency,
            "compressor_mechanical_loss": compressor_mechanical_loss,
            "compressor_to_heat_release_pressure_drop": compressor_to_heat_release_pressure_drop,
            "heat_release_temp_approach": heat_release_temp_approach,
            "heat_release_pressure_drop": heat_release_pressure_drop,
            "heat_release_to_regenerator_pressure_drop": heat_release_to_regenerator_pressure_drop,
            "regenerator_temp_approach": regenerator_temp_approach,
            "regenerator_high_side_pressure_drop": regenerator_high_side_pressure_drop,
            "regenerator_low_side_pressure_drop": regenerator_low_side_pressure_drop,
            "regenerator_to_expander_pressure_drop": regenerator_to_expander_pressure_drop,
            "expander_outlet_pressure": expander_outlet_pressure,
            "expander_isentropic_efficiency": expander_isentropic_efficiency,
            "expander_mechanical_loss": expander_mechanical_loss,
            "expander_to_heat_absorption_pressure_drop": expander_to_heat_absorption_pressure_drop,
            "heat_absorption_temp_approach": heat_absorption_temp_approach,
            "heat_absorption_pressure_drop": heat_absorption_pressure_drop,
            "heat_absorption_to_regenerator_pressure_drop": heat_absorption_to_regenerator_pressure_drop,
            "regenerator_to_compressor_pressure_drop": regenerator_to_compressor_pressure_drop,
            "motor_efficiency": motor_efficiency,
            "gearbox_efficiency": gearbox_efficiency,
        },
    )
    # 2.调用热泵策略计算购电成本
    return heat_pump_strategy.calculate_cost_from_steam(
        steam_pressure=steam_pressure,
        steam_temp=steam_temp,
        feedwater_pressure=feedwater_pressure,
        feedwater_temp=feedwater_temp,
        mass_flow=mass_flow,
        operating_hours=operating_hours,
        electricity_price=electricity_price,
        steam_supply_hours=steam_supply_hours,
    )


@tool
def calculate_heat_pump_mass_flow(
    steam_pressure: float,
    steam_temp: float,
    feedwater_pressure: float,
    feedwater_temp: float,
    operating_hours: float,
    electricity_price: float,
    heat_exchange_efficiency: float,
    storage_efficiency: float,
    salt_specific_heat: float,
    salt_temp_high: float,
    salt_temp_low: float,
    waste_heat_temp: float,
    electricity_cost: float,
    steam_supply_hours: float,
    working_fluid: str,
    compressor_inlet_pressure: float,
    compressor_outlet_pressure: float,
    compressor_isentropic_efficiency: float,
    compressor_mechanical_loss: float,
    compressor_to_heat_release_pressure_drop: float,
    heat_release_temp_approach: float,
    heat_release_pressure_drop: float,
    heat_release_to_regenerator_pressure_drop: float,
    regenerator_temp_approach: float,
    regenerator_high_side_pressure_drop: float,
    regenerator_low_side_pressure_drop: float,
    regenerator_to_expander_pressure_drop: float,
    expander_outlet_pressure: float,
    expander_isentropic_efficiency: float,
    expander_mechanical_loss: float,
    expander_to_heat_absorption_pressure_drop: float,
    heat_absorption_temp_approach: float,
    heat_absorption_pressure_drop: float,
    heat_absorption_to_regenerator_pressure_drop: float,
    regenerator_to_compressor_pressure_drop: float,
    motor_efficiency: float,
    gearbox_efficiency: float,
) -> dict[str, float]:
    """根据指定购电成本和循环参数，计算热泵能够供给的蒸汽质量流量。

    谷电充热时长和供汽时长需要分别提供，不能默认两者相同。
    循环参数均须由用户提供，缺少参数时先向用户询问，不能代入示例或默认值。

    :param steam_pressure: 蒸汽压力 (MPa)
    :param steam_temp: 蒸汽温度 (°C)
    :param feedwater_pressure: 给水压力 (MPa)
    :param feedwater_temp: 给水温度 (°C)
    :param operating_hours: 谷电充热时长 (h)，必须大于零
    :param electricity_price: 电价 (元/kWh)，必须大于零
    :param heat_exchange_efficiency: 换热效率，大于 0 且不超过 1
    :param storage_efficiency: 储热效率，大于 0 且不超过 1
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_high: 熔盐最高温度 (°C)
    :param salt_temp_low: 熔盐最低温度 (°C)，必须低于最高温度
    :param waste_heat_temp: 余热温度 (°C)
    :param electricity_cost: 指定购电成本 (元)，允许为零
    :param steam_supply_hours: 供汽时长 (h)，必须大于零
    :param working_fluid: 循环介质的 CoolProp 名称，如 Air、Nitrogen
    :param compressor_inlet_pressure: 兼容原字段 (kPa)，实际进口压力由回热器低压侧出口减去管道压降推导
    :param compressor_outlet_pressure: 压缩机出口压力 (kPa)
    :param compressor_isentropic_efficiency: 压缩机等熵效率，使用小数
    :param compressor_mechanical_loss: 压缩机机械损失功率 (kW)
    :param compressor_to_heat_release_pressure_drop: 压缩机出口至放热器进口管道压降 (kPa)
    :param heat_release_temp_approach: 放热器端差 (°C)
    :param heat_release_pressure_drop: 放热器压降 (kPa)
    :param heat_release_to_regenerator_pressure_drop: 放热器出口至回热器高压侧进口管道压降 (kPa)
    :param regenerator_temp_approach: 回热器端差 (°C)
    :param regenerator_high_side_pressure_drop: 回热器高压侧压降 (kPa)
    :param regenerator_low_side_pressure_drop: 回热器低压侧压降 (kPa)
    :param regenerator_to_expander_pressure_drop: 回热器高压侧出口至膨胀机进口管道压降 (kPa)
    :param expander_outlet_pressure: 膨胀机出口压力 (kPa)
    :param expander_isentropic_efficiency: 膨胀机等熵效率，使用小数
    :param expander_mechanical_loss: 膨胀机机械损失功率 (kW)
    :param expander_to_heat_absorption_pressure_drop: 膨胀机出口至吸热器进口管道压降 (kPa)
    :param heat_absorption_temp_approach: 吸热器端差 (°C)
    :param heat_absorption_pressure_drop: 吸热器压降 (kPa)
    :param heat_absorption_to_regenerator_pressure_drop: 吸热器出口至回热器低压侧进口管道压降 (kPa)
    :param regenerator_to_compressor_pressure_drop: 回热器低压侧出口至压缩机进口管道压降 (kPa)
    :param motor_efficiency: 电动机效率，使用小数
    :param gearbox_efficiency: 齿轮箱效率，使用小数
    :return: 各阶段计算结果及 mass_flow (kg/s)，供热 COP 无量纲
    """
    heat_pump_strategy = HeatPumpStrategy(
        waste_heat_temp=waste_heat_temp,
        heat_exchange_efficiency=heat_exchange_efficiency,
        storage_efficiency=storage_efficiency,
        salt_specific_heat=salt_specific_heat,
        salt_temp_delta=salt_temp_high - salt_temp_low,
        salt_temp_low=salt_temp_low,
        cop_parameters={
            "working_fluid": working_fluid,
            "compressor_inlet_pressure": compressor_inlet_pressure,
            "compressor_outlet_pressure": compressor_outlet_pressure,
            "compressor_isentropic_efficiency": compressor_isentropic_efficiency,
            "compressor_mechanical_loss": compressor_mechanical_loss,
            "compressor_to_heat_release_pressure_drop": compressor_to_heat_release_pressure_drop,
            "heat_release_temp_approach": heat_release_temp_approach,
            "heat_release_pressure_drop": heat_release_pressure_drop,
            "heat_release_to_regenerator_pressure_drop": heat_release_to_regenerator_pressure_drop,
            "regenerator_temp_approach": regenerator_temp_approach,
            "regenerator_high_side_pressure_drop": regenerator_high_side_pressure_drop,
            "regenerator_low_side_pressure_drop": regenerator_low_side_pressure_drop,
            "regenerator_to_expander_pressure_drop": regenerator_to_expander_pressure_drop,
            "expander_outlet_pressure": expander_outlet_pressure,
            "expander_isentropic_efficiency": expander_isentropic_efficiency,
            "expander_mechanical_loss": expander_mechanical_loss,
            "expander_to_heat_absorption_pressure_drop": expander_to_heat_absorption_pressure_drop,
            "heat_absorption_temp_approach": heat_absorption_temp_approach,
            "heat_absorption_pressure_drop": heat_absorption_pressure_drop,
            "heat_absorption_to_regenerator_pressure_drop": heat_absorption_to_regenerator_pressure_drop,
            "regenerator_to_compressor_pressure_drop": regenerator_to_compressor_pressure_drop,
            "motor_efficiency": motor_efficiency,
            "gearbox_efficiency": gearbox_efficiency,
        },
    )
    return heat_pump_strategy.calculate_mass_flow_from_cost(
        steam_pressure=steam_pressure,
        steam_temp=steam_temp,
        feedwater_pressure=feedwater_pressure,
        feedwater_temp=feedwater_temp,
        operating_hours=operating_hours,
        electricity_price=electricity_price,
        electricity_cost=electricity_cost,
        steam_supply_hours=steam_supply_hours,
    )


@tool
def calculate_heat_pump_cop(
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
        expander_outlet_pressure: float,  # E52，当前为公式；接口单位为 kPa
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

    单独计算 COP，只需热泵输出热功率和循环参数。
    缺少参数时先向用户询问，不能代入示例或默认值。
    压力和压降统一使用 kPa，温度和端差使用 ℃，功率使用 kW。
    若用户给出的热泵输出热功率为 MW，需乘以 1000 后传入 charging_power。

    :param working_fluid: 循环介质的 CoolProp 名称，如 "Air"、"Nitrogen"
    :param waste_heat_temp: 余热温度 (℃)
    :param salt_temp_low: 熔盐下限温度 (℃)
    :param charging_power: 热泵输出热功率 (kW)

    :param compressor_inlet_pressure: 兼容原字段 (kPa)，实际进口压力由回热器低压侧出口减去管道压降推导
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

    :return: 包含以下结果的字典：
        cop：系统供热 COP，无量纲；
        charging_power：热泵输出热功率 (kW)；
        electrical_power：系统输入电功率 (kW)；
        cycle_mass_flow：循环介质质量流量 (kg/s)。
    """
    return calculate_cop(
        working_fluid=working_fluid,
        waste_heat_temp=waste_heat_temp,
        salt_temp_low=salt_temp_low,
        charging_power=charging_power,
        compressor_inlet_pressure=compressor_inlet_pressure,
        compressor_outlet_pressure=compressor_outlet_pressure,
        compressor_isentropic_efficiency=compressor_isentropic_efficiency,
        compressor_mechanical_loss=compressor_mechanical_loss,
        compressor_to_heat_release_pressure_drop=compressor_to_heat_release_pressure_drop,
        heat_release_temp_approach=heat_release_temp_approach,
        heat_release_pressure_drop=heat_release_pressure_drop,
        heat_release_to_regenerator_pressure_drop=heat_release_to_regenerator_pressure_drop,
        regenerator_temp_approach=regenerator_temp_approach,
        regenerator_high_side_pressure_drop=regenerator_high_side_pressure_drop,
        regenerator_low_side_pressure_drop=regenerator_low_side_pressure_drop,
        regenerator_to_expander_pressure_drop=regenerator_to_expander_pressure_drop,
        expander_outlet_pressure=expander_outlet_pressure,
        expander_isentropic_efficiency=expander_isentropic_efficiency,
        expander_mechanical_loss=expander_mechanical_loss,
        expander_to_heat_absorption_pressure_drop=expander_to_heat_absorption_pressure_drop,
        heat_absorption_temp_approach=heat_absorption_temp_approach,
        heat_absorption_pressure_drop=heat_absorption_pressure_drop,
        heat_absorption_to_regenerator_pressure_drop=heat_absorption_to_regenerator_pressure_drop,
        regenerator_to_compressor_pressure_drop=regenerator_to_compressor_pressure_drop,
        motor_efficiency=motor_efficiency,
        gearbox_efficiency=gearbox_efficiency,
    )

@tool
def calculate_mass_flow(
        steam_pressure: float,
        steam_temp: float,
        feedwater_pressure: float,
        feedwater_temp: float,
        operating_hours: float,
        electricity_price: float,
        electrical_efficiency: float,
        heat_exchange_efficiency: float,
        storage_efficiency: float,
        salt_specific_heat: float,
        salt_temp_high: float,
        salt_temp_low: float,
        electricity_cost: float,
        steam_supply_hours: float,
    ) -> dict:
    """
    根据指定购电成本，计算电加热器能够供给的蒸汽质量流量。

    谷电充热时长和供汽时长需要分别提供，不能默认两者相同。

    :param steam_pressure: 蒸汽压力 (MPa)
    :param steam_temp: 蒸汽温度 (°C)
    :param feedwater_pressure: 给水压力 (MPa)
    :param feedwater_temp: 给水温度 (°C)
    :param operating_hours: 谷电充热时长 (h)，必须大于零
    :param electricity_price: 电价 (元/kWh)，必须大于零
    :param electrical_efficiency: 电热效率 (0~1之间的小数)
    :param heat_exchange_efficiency: 换热效率 (0~1之间的小数)
    :param storage_efficiency: 储热效率 (0~1之间的小数)
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_high: 熔盐最高温度 (°C)
    :param salt_temp_low: 熔盐最低温度 (°C)
    :param electricity_cost: 指定购电成本 (元)，允许为零
    :param steam_supply_hours: 供汽时长 (h)，必须大于零
    :return: 各阶段功率 (kW)、总供热量和耗电量 (kWh)、购电成本 (元)
             和蒸汽质量流量 mass_flow (kg/s)
    """
    salt_temp_delta = salt_temp_high - salt_temp_low
    electricHeaterStrategy = ElectricHeaterStrategy(
        electrical_efficiency,
        heat_exchange_efficiency,
        storage_efficiency,
        salt_specific_heat,
        salt_temp_delta
    )

    return electricHeaterStrategy.calculate_mass_flow_from_cost(
        steam_pressure=steam_pressure,
        steam_temp=steam_temp,
        feedwater_pressure=feedwater_pressure,
        feedwater_temp=feedwater_temp,
        operating_hours=operating_hours,
        electricity_price=electricity_price,
        electricity_cost=electricity_cost,
        steam_supply_hours=steam_supply_hours,
    )


@tool
def calculate_salt_mass(
    charging_power: float,
    storage_duration: float,
    salt_specific_heat: float,
    salt_temp_high: float,
    salt_temp_low: float,
) -> dict[str, float]:
    """根据充热端热功率、储热时长和熔盐物性，计算所需熔盐质量。

    可以使用电加热器或热泵计算结果中的 charging_power，输入单位为 kW。

    :param charging_power: 充热端热功率 (kW)，若给定 MW，需乘以 1000
    :param storage_duration: 按充热功率配置的储热容量时长 (h)
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_high: 熔盐最高温度 (°C)，必须高于最低温度
    :param salt_temp_low: 熔盐最低温度 (°C)
    :return: 包含 salt_mass 的字典，熔盐质量单位为吨
    """
    if not isfinite(salt_temp_high) or not isfinite(salt_temp_low):
        raise ValueError("熔盐最高温度和最低温度必须是有限数值")

    salt_mass = salt_storage.calculate_salt_mass(
        charging_power=charging_power,
        storage_duration=storage_duration,
        salt_specific_heat=salt_specific_heat,
        salt_temp_delta=salt_temp_high - salt_temp_low,
    )
    return {"salt_mass": salt_mass}


# 所有可用的工具
ALL_TOOLS = [
    calculate_electric_heater_cost,
    calculate_mass_flow,
    calculate_salt_mass,
    # 以后在这里加新工具：
    calculate_heat_pump_cost,
    calculate_heat_pump_mass_flow,
    calculate_heat_pump_cop,
    calculate_steam_flow_from_renewable_power,
]
