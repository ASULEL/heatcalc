"""按方案步骤组织经济测算，保留输入和未舍入的表格数据。"""

from heatcalc.finance import (
    calculate_cash_flow_schedule, calculate_cost_schedule, calculate_income_tax_schedule,
    calculate_loan_schedule, calculate_revenue_tax_schedule,
)


def calculate_economic_step(
    scheme_id: str,
    step: str,
    inputs: dict,
    loan_result: dict | None = None,
    cost_result: dict | None = None,
    revenue_tax_result: dict | None = None,
    income_tax_result: dict | None = None,
) -> dict:
    """按借款、成本、收入及税金、所得税、现金流量的顺序计算，引用来源保留原始精度。"""
    result = {"scheme_id": scheme_id, "step": step}  # 本次测算所属方案与步骤

    if step == "loan":
        result["loan_result"] = {
            "table_type": "loan",
            "inputs": inputs,
            **calculate_loan_schedule(**inputs),
        }
    elif step == "cost":
        result["loan_result"] = loan_result
        result["cost_result"] = {
            "table_type": "cost",
            "inputs": inputs,
            **calculate_cost_schedule(loan_schedule=loan_result, **inputs),
        }
    elif step == "revenue_tax":
        result["loan_result"] = loan_result
        result["cost_result"] = cost_result
        result["revenue_tax_result"] = {
            "table_type": "revenue_tax",
            "inputs": inputs,
            **calculate_revenue_tax_schedule(loan_schedule=loan_result, cost_schedule=cost_result, **inputs),
        }
    elif step == "income_tax":
        result["loan_result"] = loan_result
        result["cost_result"] = cost_result
        result["revenue_tax_result"] = revenue_tax_result
        result["income_tax_result"] = {
            "table_type": "income_tax",
            "inputs": inputs,
            **calculate_income_tax_schedule(
                cost_schedule=cost_result, revenue_tax_schedule=revenue_tax_result, **inputs,
            ),
        }
    elif step == "cash_flow":
        result["loan_result"] = loan_result
        result["cost_result"] = cost_result
        result["revenue_tax_result"] = revenue_tax_result
        result["income_tax_result"] = income_tax_result
        result["cash_flow_result"] = {
            "table_type": "cash_flow",
            "inputs": inputs,
            **calculate_cash_flow_schedule(
                loan_schedule=loan_result, cost_schedule=cost_result,
                revenue_tax_schedule=revenue_tax_result, income_tax_schedule=income_tax_result,
                **inputs,
            ),
        }
    else:
        raise ValueError(f"未知经济测算步骤：{step}")

    return result


def revise_loan_scheme(saved: dict, loan_inputs: dict) -> list[dict]:
    """修改借款输入后，沿用已提交参数依次重算已有表格。"""
    loan = calculate_economic_step(saved["scheme_id"], "loan", loan_inputs)
    results = [loan]
    old_calendar = [(row["year"], row["phase"]) for row in saved["loan_result"]["schedule"]]
    new_calendar = [(row["year"], row["phase"]) for row in loan["loan_result"]["schedule"]]
    if "cost_result" not in saved or new_calendar != old_calendar:
        return results

    cost = calculate_economic_step(
        saved["scheme_id"], "cost", saved["cost_result"]["inputs"],
        loan_result=loan["loan_result"],
    )
    results.append(cost)
    if "revenue_tax_result" in saved:
        revenue_tax = calculate_economic_step(
            saved["scheme_id"], "revenue_tax", saved["revenue_tax_result"]["inputs"],
            loan_result=loan["loan_result"], cost_result=cost["cost_result"],
        )
        results.append(revenue_tax)
        if "income_tax_result" in saved:
            income_tax = calculate_economic_step(
                saved["scheme_id"], "income_tax", saved["income_tax_result"]["inputs"],
                loan_result=loan["loan_result"], cost_result=cost["cost_result"],
                revenue_tax_result=revenue_tax["revenue_tax_result"],
            )
            results.append(income_tax)
            if "cash_flow_result" in saved:
                results.append(calculate_economic_step(
                    saved["scheme_id"], "cash_flow", saved["cash_flow_result"]["inputs"],
                    loan_result=loan["loan_result"], cost_result=cost["cost_result"],
                    revenue_tax_result=revenue_tax["revenue_tax_result"],
                    income_tax_result=income_tax["income_tax_result"],
                ))
    return results
