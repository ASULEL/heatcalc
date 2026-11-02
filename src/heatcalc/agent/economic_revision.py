"""明确的借款参数修改直接使用已保存输入计算。"""

import re
from typing import Any

from heatcalc.agent.loan_inputs import BankLoanInputs
from heatcalc.agent.parameter_specs import build_economic_form, build_next_economic_form
from heatcalc.finance.economic_calculation import revise_loan_scheme


LOAN_LABELS = {field.description: name for name, field in BankLoanInputs.model_fields.items()}
LOAN_CHANGE = re.compile(
    r"(?:请|麻烦)?\s*(?:帮我)?\s*(?:将|把)?\s*"
    r"(?:(?:经济测算|方案)\s*(?P<scheme>\d+)\s*的?\s*)?"
    rf"(?P<label>{'|'.join(re.escape(label) for label in LOAN_LABELS)})\s*"
    r"(?:修改为|修改成|改为|改成|调整为|调整成)\s*"
    r"(?P<value>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*"
    r"(?P<unit>万元|亿元|元|%|％|年)?\s*[。！!，,]?"
)
UNIT_FACTORS = {
    "万元": {"": 1, "万元": 1, "亿元": 10000, "元": 0.0001},
    "小数": {"": 1, "%": 0.01, "％": 0.01},
    "年": {"": 1, "年": 1},
    "项目第几年": {"": 1, "年": 1},
}


def revise_loan_from_message(
    message: str, saved_results: list[dict[str, Any]],
) -> tuple[str, list[dict], list[dict]] | None:
    """只识别完整的单参数修改指令；解释、假设和其他请求继续交给模型。"""
    match = LOAN_CHANGE.fullmatch(message.strip())
    if match is None:
        return None

    name = LOAN_LABELS[match["label"]]
    unit = match["unit"] or ""
    expected_unit = BankLoanInputs.model_fields[name].json_schema_extra["unit"]
    if unit not in UNIT_FACTORS[expected_unit]:
        raise ValueError(f"{match['label']}的单位应为{expected_unit}")
    value = float(match["value"].replace(",", "")) * UNIT_FACTORS[expected_unit][unit]

    if not saved_results:
        return "尚未生成借款表，已填入修改值，请确认其余借款参数。", build_economic_form("loan", {name: value}), []
    if match["scheme"]:
        requested_name = f"经济测算 {int(match['scheme'])}"
        saved = next((
            result for index, result in enumerate(saved_results, start=1)
            if result.get("scheme_name", f"经济测算 {index}") == requested_name
        ), None)
        if saved is None:
            raise ValueError("指定的经济测算方案不存在")
    elif len(saved_results) == 1:
        saved = saved_results[0]
    else:
        return "当前对话有多个方案，请指定编号，例如：将经济测算1的静态投资改成30458.8235。", [], []

    inputs = BankLoanInputs.model_validate({**saved["loan_result"]["inputs"], name: value}).model_dump()
    results = revise_loan_scheme(saved, inputs)
    tables = {
        "loan": "借款表", "cost": "成本表", "revenue_tax": "收入及税金表",
        "income_tax": "所得税表", "cash_flow": "现金流量表",
    }
    updated_tables = "、".join(tables[result["step"]] for result in results)
    display_unit = "万元" if expected_unit == "万元" else "年" if "年" in expected_unit else "（小数）"
    reply = f"已将{match['label']}改为{value:.4f}{display_unit}，重新生成{updated_tables}。"
    if len(results) == 1:
        reply += "请使用下方最新的成本参数表继续填写。"
    return reply, build_next_economic_form(results[-1]), [
        {"tool_name": "calculate_economic_scheme", **result} for result in results
    ]
