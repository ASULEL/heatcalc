"""读取 Tool 的输入定义，生成前端参数表。"""

from inspect import signature
from typing import Any


def build_parameter_form(tool: Any, known_values: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """按函数参数顺序生成表单；已知值采用工具单位，示例值采用显示单位。"""
    if tool.name == "calculate_economic_scheme":
        return build_economic_form("loan", known_values)
    return build_input_form(tool.args_schema, known_values, list(signature(tool.func).parameters))


def build_economic_form(step: str, known_values: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """经济测算按步骤读取各自的输入模型，不把两组参数混在一起。"""
    from heatcalc.agent.cost_inputs import CostScheduleInputs
    from heatcalc.agent.loan_inputs import BankLoanInputs

    inputs = BankLoanInputs if step == "loan" else CostScheduleInputs  # 本步骤输入定义
    fields = build_input_form(inputs, known_values)  # 展示字段
    for field in fields:
        field["toolName"] = "calculate_economic_scheme"
        field["schemeStep"] = step
    return fields


def build_input_form(
    inputs: Any,
    known_values: dict[str, Any] | None = None,
    names: list[str] | None = None,
) -> list[dict[str, Any]]:
    """只读取输入模型的字段元数据，供普通工具和方案步骤共用。"""
    known_values = known_values or {}  # 用户已经提供的参数
    form_config = inputs.model_config.get("json_schema_extra") or {}  # 表单选项
    defaults = form_config.get("form_defaults", {})  # 仅供预填的示例值
    form = []  # 前端参数表

    for name in names if names is not None else inputs.model_fields:
        schema_field = inputs.model_fields[name]  # 输入字段定义
        metadata = schema_field.json_schema_extra  # 单位、分组和显示选项
        factor = metadata.get("toToolFactor", 1)  # 显示单位转工具单位的倍率
        has_known_value = name in known_values and known_values[name] is not None
        value = known_values[name] if has_known_value else defaults.get(name, metadata.get("default"))

        if has_known_value and isinstance(value, (int, float)) and factor != 1:
            value /= factor

        field = {
            "name": name,
            "label": schema_field.description,
            "unit": metadata.get("display_unit", metadata["unit"]),
            "group": metadata.get("group", "计算参数"),
            "advanced": metadata.get("advanced", False),
            "value": value,
            "required": schema_field.is_required(),
        }
        if factor != 1:
            field["toToolFactor"] = factor
        if "default" in metadata or (not has_known_value and name in defaults):
            field["isDefault"] = not has_known_value
        if "options" in metadata:
            field["inputType"] = "select"
            field["options"] = metadata["options"]
        if "annual_default" in metadata:
            field["annualDefault"] = metadata["annual_default"]
        if "period_defaults" in metadata:
            field["periodDefaults"] = metadata["period_defaults"]
        form.append(field)

    return form
