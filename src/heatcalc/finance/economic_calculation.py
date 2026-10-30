"""按方案步骤组织经济测算，保留输入和未舍入的表格数据。"""

from heatcalc.finance import calculate_cost_schedule, calculate_loan_schedule


def calculate_economic_step(
    scheme_id: str,
    step: str,
    inputs: dict,
    loan_result: dict | None = None,
) -> dict:
    """先生成借款表，再使用该方案已生成的借款结果计算成本表。"""
    result = {"scheme_id": scheme_id, "step": step}  # 本次测算所属方案与步骤

    if step == "loan":
        result["loan_result"] = {
            "table_type": "loan",
            "inputs": inputs,
            **calculate_loan_schedule(**inputs),
        }
    else:
        result["loan_result"] = loan_result
        result["cost_result"] = {
            "table_type": "cost",
            "inputs": inputs,
            **calculate_cost_schedule(loan_schedule=loan_result, **inputs),
        }

    return result
