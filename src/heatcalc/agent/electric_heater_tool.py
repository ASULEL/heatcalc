"""电加热器计算工具。"""

from langchain_core.tools import tool
from pydantic import Field

from heatcalc.agent.common_inputs import HeatSourceInputs, HeatTransferInputs, SteamInputs
from heatcalc.heat_source.electric_heater import ElectricHeaterStrategy
from heatcalc.heat_source.renewable import (
    calculate_steam_flow_from_renewable_power as calculate_steam_flow_from_renewable_power_model,
)


class ElectricHeaterInputs(HeatSourceInputs):
    """电加热器共用工况。"""

    # 风光与电加热参数
    electrical_efficiency: float = Field(
        description="电加热器热效率",
        json_schema_extra={"unit": "小数", "group": "风光与电加热参数"},
    )


class ElectricHeaterCostInputs(ElectricHeaterInputs):
    """根据蒸汽需求计算购电成本。"""

    # 蒸汽与供热参数
    mass_flow: float = Field(
        description="蒸汽质量流量",
        json_schema_extra={"unit": "kg/s", "group": "蒸汽与供热参数"},
    )


class ElectricHeaterFlowInputs(ElectricHeaterInputs):
    """根据购电预算计算蒸汽流量。"""

    # 电价与预算参数
    electricity_cost: float = Field(
        description="指定购电成本",
        json_schema_extra={"unit": "元", "group": "电价与预算参数"},
    )


class RenewableSteamInputs(SteamInputs, HeatTransferInputs):
    """风电或光伏供电的电加热制汽输入。"""

    # 风光与电加热参数
    renewable_power: float = Field(
        description="风电或光伏功率",
        json_schema_extra={"unit": "kW", "group": "风光与电加热参数"},
    )
    renewable_conversion_efficiency: float = Field(
        description="风光到加热器输入效率",
        json_schema_extra={"unit": "小数", "group": "风光与电加热参数"},
    )
    rated_electrical_power: float = Field(
        description="电加热器额定输入功率",
        json_schema_extra={"unit": "kW", "group": "风光与电加热参数"},
    )
    electrical_efficiency: float = Field(
        description="电加热器热效率",
        json_schema_extra={"unit": "小数", "group": "风光与电加热参数"},
    )


@tool(args_schema=ElectricHeaterCostInputs)
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


@tool(args_schema=ElectricHeaterFlowInputs)
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


@tool(args_schema=RenewableSteamInputs)
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
    return calculate_steam_flow_from_renewable_power_model(
        renewable_power=renewable_power,
        renewable_conversion_efficiency=renewable_conversion_efficiency,
        rated_electrical_power=rated_electrical_power,
        electrical_efficiency=electrical_efficiency,
        heat_exchange_efficiency=heat_exchange_efficiency,
        storage_efficiency=storage_efficiency,
        operating_hours=operating_hours,
        steam_supply_hours=steam_supply_hours,
        steam_pressure=steam_pressure,
        steam_temp=steam_temp,
        feedwater_pressure=feedwater_pressure,
        feedwater_temp=feedwater_temp,
    )
