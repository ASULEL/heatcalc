from math import isfinite

from langchain_core.tools import tool

from heatcalc import salt_storage
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
) -> dict[str, float]:
    """
    根据蒸汽需求和余热温度对应的供热 COP，计算热泵的购电成本。

    谷电充热时长和供汽时长需要分别提供，不能默认两者相同。

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
    :param waste_heat_temp: 余热温度 (°C)，当前 COP 表仅配置了 30°C 的数据
    :param steam_supply_hours: 供汽时长 (h)，必须大于零
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
) -> dict[str, float]:
    """根据指定购电成本和余热温度，计算热泵能够供给的蒸汽质量流量。

    谷电充热时长和供汽时长需要分别提供，不能默认两者相同。

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
    :param waste_heat_temp: 余热温度 (°C)，当前 COP 表仅配置了 30°C 的数据
    :param electricity_cost: 指定购电成本 (元)，允许为零
    :param steam_supply_hours: 供汽时长 (h)，必须大于零
    :return: 各阶段计算结果及 mass_flow (kg/s)，供热 COP 无量纲
    """
    heat_pump_strategy = HeatPumpStrategy(
        waste_heat_temp=waste_heat_temp,
        heat_exchange_efficiency=heat_exchange_efficiency,
        storage_efficiency=storage_efficiency,
        salt_specific_heat=salt_specific_heat,
        salt_temp_delta=salt_temp_high - salt_temp_low,
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
]
