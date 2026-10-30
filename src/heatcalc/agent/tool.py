"""统一汇总并注册所有计算工具。"""

from heatcalc.agent.economic_tool import calculate_economic_scheme
from heatcalc.agent.electric_heater_tool import (
    calculate_electric_heater_cost,
    calculate_mass_flow,
    calculate_steam_flow_from_renewable_power,
)
from heatcalc.agent.heat_pump_tool import (
    calculate_heat_pump_cop,
    calculate_heat_pump_cost,
    calculate_heat_pump_mass_flow,
)
from heatcalc.agent.salt_storage_tool import calculate_salt_mass


ALL_TOOLS = [  # Agent 可调用的计算工具
    # 电加热器
    calculate_electric_heater_cost,
    calculate_mass_flow,
    calculate_steam_flow_from_renewable_power,
    # 热泵
    calculate_heat_pump_cost,
    calculate_heat_pump_mass_flow,
    calculate_heat_pump_cop,
    # 熔盐储量
    calculate_salt_mass,
    # 经济测算方案：先借款还本付息，后成本计算
    calculate_economic_scheme,
]
