"""直接调用风电或光伏功率计算蒸汽流量工具的示例。"""

from heatcalc.agent.formatting import format_result_for_display
from heatcalc.agent.tools import calculate_steam_flow_from_renewable_power


def test_calculate_steam_flow_from_renewable_power():
    # 功率使用 kW；0.97 是本用例明确给出的转换效率，与电热效率 0.985 分开。
    result = calculate_steam_flow_from_renewable_power.invoke({
        "renewable_power": 8000.0,
        "renewable_conversion_efficiency": 0.97,
        "rated_electrical_power": 10000.0,
        "electrical_efficiency": 0.985,
        "heat_exchange_efficiency": 0.99,
        "storage_efficiency": 0.99,
        "operating_hours": 8.0,
        "steam_supply_hours": 24.0,
        "steam_pressure": 1.5,
        "steam_temp": 200.0,
        "feedwater_pressure": 0.1,
        "feedwater_temp": 20.0,
    })
    print("原始结果：", result)
    print("展示结果：", format_result_for_display(result))
