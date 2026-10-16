from langchain_core.tools import tool

from heatcalc.electric_heater import ElectricHeaterStrategy


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
) -> dict:
    """
    计算电加热器满足指定蒸汽需求所需的购电成本。

    :param steam_pressure: 蒸汽压力 (MPa)
    :param steam_temp: 蒸汽温度 (°C)
    :param feedwater_pressure: 给水压力 (MPa)
    :param feedwater_temp: 给水温度 (°C)
    :param mass_flow: 质量流量 (kg/s)
    :param operating_hours: 用电时长 (h)
    :param electricity_price: 电价 (元/kWh)
    :param electrical_efficiency: 电热效率 (0~1之间的小数)
    :param heat_exchange_efficiency: 换热效率 (0~1之间的小数)
    :param storage_efficiency: 储热效率 (0~1之间的小数)
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_high: 熔盐最高温度 (°C)
    :param salt_temp_low: 熔盐最低温度 (°C)
    :return: 包含中间计算结果和最终购电成本的字典
    """
    salt_temp_delta = salt_temp_high - salt_temp_low
    # 1.创建计算蒸汽->电的实体
    electricHeaterStrategy = ElectricHeaterStrategy(
        electrical_efficiency,
        heat_exchange_efficiency,
        storage_efficiency,
        salt_specific_heat,
        salt_temp_delta)

    # 2.计算电价，这里要转换成工业单位，当前是标准单位，一个字典
    data = electricHeaterStrategy.calculate_cost_from_steam(steam_pressure,
                                                     steam_temp,
                                                     feedwater_pressure,
                                                     feedwater_temp,
                                                     mass_flow,
                                                     operating_hours,
                                                     electricity_price)

    return data


# 所有可用的工具
ALL_TOOLS = [
    calculate_electric_heater_cost,
    # 以后在这里加新工具：
    # calculate_salt_mass,
    # calculate_heat_pump_cost,
]
