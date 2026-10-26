"""参数表的页面显示说明。

工具调用仍然使用英文参数名；前端只显示这里定义的中文含义和单位。
"""

from typing import Any


PARAMETER_METADATA: dict[str, dict[str, str]] = {
    "steam_pressure": {"label": "蒸汽压力", "unit": "MPa"},
    "steam_temp": {"label": "蒸汽温度", "unit": "°C"},
    "feedwater_pressure": {"label": "给水压力", "unit": "MPa"},
    "feedwater_temp": {"label": "给水温度", "unit": "°C"},
    "mass_flow": {"label": "蒸汽质量流量", "unit": "kg/s"},
    "operating_hours": {"label": "充热时长", "unit": "h"},
    "electricity_price": {"label": "电价", "unit": "元/kWh"},
    "electrical_efficiency": {"label": "电加热器热效率", "unit": "小数"},
    "heat_exchange_efficiency": {"label": "换热效率", "unit": "小数"},
    "storage_efficiency": {"label": "储热效率", "unit": "小数"},
    "salt_specific_heat": {"label": "熔盐比热容", "unit": "kJ/(kg·K)"},
    "salt_temp_high": {"label": "熔盐最高温度", "unit": "°C"},
    "salt_temp_low": {"label": "熔盐最低温度", "unit": "°C"},
    "steam_supply_hours": {"label": "供汽时长", "unit": "h"},
    "renewable_power": {"label": "风电或光伏功率", "unit": "kW"},
    "renewable_conversion_efficiency": {"label": "风光到加热器输入效率", "unit": "小数"},
    "rated_electrical_power": {"label": "电加热器额定输入功率", "unit": "kW"},
    "waste_heat_temp": {"label": "余热温度", "unit": "°C"},
    "working_fluid": {"label": "循环介质", "unit": "名称"},
    "compressor_inlet_pressure": {"label": "压缩机进口压力", "unit": "kPa"},
    "compressor_outlet_pressure": {"label": "压缩机出口压力", "unit": "kPa"},
    "compressor_isentropic_efficiency": {"label": "压缩机等熵效率", "unit": "小数"},
    "compressor_mechanical_loss": {"label": "压缩机机械损失功率", "unit": "kW"},
    "compressor_to_heat_release_pressure_drop": {
        "label": "压缩机至放热器管道压损",
        "unit": "kPa",
    },
    "heat_release_temp_approach": {"label": "放热器端差", "unit": "°C"},
    "heat_release_pressure_drop": {"label": "放热器压损", "unit": "kPa"},
    "heat_release_to_regenerator_pressure_drop": {
        "label": "放热器至回热器管道压损",
        "unit": "kPa",
    },
    "regenerator_temp_approach": {"label": "回热器端差", "unit": "°C"},
    "regenerator_high_side_pressure_drop": {"label": "回热器高压侧压损", "unit": "kPa"},
    "regenerator_low_side_pressure_drop": {"label": "回热器低压侧压损", "unit": "kPa"},
    "regenerator_to_expander_pressure_drop": {
        "label": "回热器至膨胀机管道压损",
        "unit": "kPa",
    },
    "expander_outlet_pressure": {"label": "膨胀机出口压力", "unit": "kPa"},
    "expander_isentropic_efficiency": {"label": "膨胀机等熵效率", "unit": "小数"},
    "expander_mechanical_loss": {"label": "膨胀机机械损失功率", "unit": "kW"},
    "expander_to_heat_absorption_pressure_drop": {
        "label": "膨胀机至吸热器管道压损",
        "unit": "kPa",
    },
    "heat_absorption_temp_approach": {"label": "吸热器端差", "unit": "°C"},
    "heat_absorption_pressure_drop": {"label": "吸热器压损", "unit": "kPa"},
    "heat_absorption_to_regenerator_pressure_drop": {
        "label": "吸热器至回热器管道压损",
        "unit": "kPa",
    },
    "regenerator_to_compressor_pressure_drop": {
        "label": "回热器至压缩机管道压损",
        "unit": "kPa",
    },
    "motor_efficiency": {"label": "电动机效率", "unit": "小数"},
    "gearbox_efficiency": {"label": "齿轮箱效率", "unit": "小数"},
    "charging_power": {"label": "热泵输出热功率", "unit": "kW"},
    "electricity_cost": {"label": "指定购电成本", "unit": "元"},
    "storage_duration": {"label": "储热时长", "unit": "h"},
}

TOOL_PARAMETER_OVERRIDES: dict[str, dict[str, dict[str, str]]] = {
    "calculate_salt_mass": {
        "charging_power": {
            "label": "充热端热功率",
            "unit": "kW",
            "group": "储热系统参数",
        },
    },
}

# 来自 outputs/cop-coolprop-20261022/系统COP计算_CoolProp.xlsx 的 COP 示例。
# 表格按 Excel 单位展示，提交参数时由前端转换为工具接口单位。
TOOL_DEFAULT_VALUES: dict[str, dict[str, Any]] = {
    "calculate_heat_pump_cop": {
        "working_fluid": "air",
        "waste_heat_temp": 400,
        "salt_temp_low": 310,
        "charging_power": 100,
        "compressor_inlet_pressure": 2.7,
        "compressor_outlet_pressure": 11.5,
        "compressor_isentropic_efficiency": 0.85,
        "heat_release_temp_approach": 10,
        "heat_release_pressure_drop": 200,
        "heat_release_to_regenerator_pressure_drop": 0,
        "regenerator_temp_approach": 20,
        "regenerator_high_side_pressure_drop": 200,
        "regenerator_low_side_pressure_drop": 200,
        "regenerator_to_expander_pressure_drop": 0,
        "expander_outlet_pressure": 2.95,
        "expander_isentropic_efficiency": 0.92,
        "expander_mechanical_loss": 0,
        "expander_to_heat_absorption_pressure_drop": 0,
        "heat_absorption_temp_approach": 130,
        "heat_absorption_pressure_drop": 50,
        "motor_efficiency": 0.98,
        "gearbox_efficiency": 0.985,
    },
}

COP_TOOL_NAMES = {
    "calculate_heat_pump_cop",
    "calculate_heat_pump_cost",
    "calculate_heat_pump_mass_flow",
}

DISPLAY_UNIT_OVERRIDES = {
    "charging_power": {"unit": "MWt", "toToolFactor": 1000},
    "compressor_inlet_pressure": {"unit": "MPa", "toToolFactor": 1000},
    "compressor_outlet_pressure": {"unit": "MPa", "toToolFactor": 1000},
    "expander_outlet_pressure": {"unit": "MPa", "toToolFactor": 1000},
}

TOOL_PARAMETER_OPTIONS: dict[str, dict[str, list[dict[str, str]]]] = {
    "calculate_heat_pump_cop": {
        "working_fluid": [{"value": "air", "label": "air（空气）"}],
    },
    "calculate_heat_pump_cost": {
        "working_fluid": [{"value": "air", "label": "air（空气）"}],
    },
    "calculate_heat_pump_mass_flow": {
        "working_fluid": [{"value": "air", "label": "air（空气）"}],
    },
}

PARAMETER_GROUPS: dict[str, str] = {
    "steam_pressure": "蒸汽与供热参数",
    "steam_temp": "蒸汽与供热参数",
    "feedwater_pressure": "蒸汽与供热参数",
    "feedwater_temp": "蒸汽与供热参数",
    "mass_flow": "蒸汽与供热参数",
    "steam_supply_hours": "蒸汽与供热参数",
    "electricity_price": "电价与预算参数",
    "electricity_cost": "电价与预算参数",
    "operating_hours": "储热系统参数",
    "heat_exchange_efficiency": "储热系统参数",
    "storage_efficiency": "储热系统参数",
    "salt_specific_heat": "储热系统参数",
    "salt_temp_high": "储热系统参数",
    "salt_temp_low": "储热系统参数",
    "storage_duration": "储热系统参数",
    "renewable_power": "风光与电加热参数",
    "renewable_conversion_efficiency": "风光与电加热参数",
    "rated_electrical_power": "风光与电加热参数",
    "electrical_efficiency": "风光与电加热参数",
    "waste_heat_temp": "热泵基础参数",
    "working_fluid": "热泵基础参数",
    "charging_power": "热泵基础参数",
    "compressor_inlet_pressure": "压缩机参数",
    "compressor_outlet_pressure": "压缩机参数",
    "compressor_isentropic_efficiency": "压缩机参数",
    "compressor_mechanical_loss": "压缩机参数",
    "compressor_to_heat_release_pressure_drop": "放热器参数",
    "heat_release_temp_approach": "放热器参数",
    "heat_release_pressure_drop": "放热器参数",
    "heat_release_to_regenerator_pressure_drop": "放热器参数",
    "regenerator_temp_approach": "回热器参数",
    "regenerator_high_side_pressure_drop": "回热器参数",
    "regenerator_low_side_pressure_drop": "回热器参数",
    "regenerator_to_expander_pressure_drop": "膨胀机参数",
    "expander_outlet_pressure": "膨胀机参数",
    "expander_isentropic_efficiency": "膨胀机参数",
    "expander_mechanical_loss": "膨胀机参数",
    "expander_to_heat_absorption_pressure_drop": "吸热器参数",
    "heat_absorption_temp_approach": "吸热器参数",
    "heat_absorption_pressure_drop": "吸热器参数",
    "heat_absorption_to_regenerator_pressure_drop": "吸热器参数",
    "regenerator_to_compressor_pressure_drop": "传动与连接参数",
    "motor_efficiency": "传动与连接参数",
    "gearbox_efficiency": "传动与连接参数",
}

ADVANCED_GROUPS = {
    "压缩机参数",
    "放热器参数",
    "回热器参数",
    "膨胀机参数",
    "吸热器参数",
    "传动与连接参数",
}


def build_parameter_form(tool: Any, known_values: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """根据工具签名生成前端使用的参数表。"""
    known_values = known_values or {}
    fields = getattr(tool.args_schema, "model_fields", {})
    overrides = TOOL_PARAMETER_OVERRIDES.get(tool.name, {})
    defaults = TOOL_DEFAULT_VALUES.get(tool.name, {})
    options = TOOL_PARAMETER_OPTIONS.get(tool.name, {})

    form = []
    for name in fields:
        has_known_value = name in known_values and known_values[name] is not None
        display_override = DISPLAY_UNIT_OVERRIDES.get(name, {}) if tool.name in COP_TOOL_NAMES else {}
        to_tool_factor = display_override.get("toToolFactor", 1)
        display_value = (
            known_values[name] / to_tool_factor
            if has_known_value and isinstance(known_values[name], (int, float)) and to_tool_factor != 1
            else known_values[name] if has_known_value else defaults.get(name)
        )
        field = {
            "name": name,
            "label": overrides.get(name, PARAMETER_METADATA[name])["label"],
            "unit": display_override.get(
                "unit",
                overrides.get(name, PARAMETER_METADATA[name])["unit"],
            ),
            "group": overrides.get(name, {}).get("group", PARAMETER_GROUPS[name]),
            "advanced": overrides.get(name, {}).get(
                "group",
                PARAMETER_GROUPS[name],
            ) in ADVANCED_GROUPS,
            "value": display_value,
            "required": True,
        }
        if to_tool_factor != 1:
            field["toToolFactor"] = to_tool_factor
        if not has_known_value and name in defaults:
            field["isDefault"] = True
        if name in options:
            field["inputType"] = "select"
            field["options"] = options[name]
        form.append(field)

    return form
