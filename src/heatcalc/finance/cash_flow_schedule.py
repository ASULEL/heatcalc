"""资本金和全投资现金流量表。"""

from typing import Any


def _irr(cash_flows: list[float]) -> float | None:
    """用二分法求内部收益率，现金流从项目第1年开始。"""
    def npv(rate: float) -> float:
        return sum(flow / (1 + rate) ** year for year, flow in enumerate(cash_flows, start=1))

    low, high = -0.9999, 10.0
    if npv(low) * npv(high) > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        if npv(mid) > 0:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def calculate_cash_flow_schedule(
    loan_schedule: dict[str, Any],
    cost_schedule: dict[str, Any],
    revenue_tax_schedule: dict[str, Any],
    income_tax_schedule: dict[str, Any],
    equity_ratio: float,
) -> dict[str, Any]:
    """按同一套现金流公式计算资本金和全投资两张表。

    资本金表只投入静态投资 × 资本金比例，并偿还本金和利息；
    全投资表投入静态投资的 100%，没有借款本金和利息。
    建设投资按借款表的第1年提款比例和第2次提款年份分年投入。
    回收固定资产余值 = 计价基数 − 累计折旧，只在最后一个运营年计入。
    金额单位为万元，资本金比例使用小数。
    """
    loan_rows = loan_schedule["schedule"]
    cost_rows = cost_schedule["schedule"]
    revenue_rows = revenue_tax_schedule["schedule"]
    income_rows = income_tax_schedule["schedule"]

    static_investment = loan_schedule["summary"]["static_investment"]  # 静态投资，万元
    first_ratio = loan_schedule["inputs"]["first_drawdown_ratio"]  # 第1年投入比例
    second_year = loan_schedule["inputs"]["second_drawdown_year"]  # 第2次投入年份
    construction_years = sum(row["phase"] == "建设期" for row in loan_rows)  # 建设期年数
    project_end_year = max(  # 最后一个运营年
        row["year"] for row in revenue_rows if row["phase"] == "运营期"
    )
    residual_value = (  # 截至项目结束的剩余账面价值，作为期末回收金额
        cost_schedule["summary"]["cost_base"]
        - sum(row["depreciation_cost"] for row in cost_rows if row["year"] <= project_end_year)
    )

    def build(equity_factor: float, with_debt: bool) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        cumulative = 0.0
        payback_period = None
        for loan_row, cost_row, revenue_row, income_row in zip(
            loan_rows, cost_rows, revenue_rows, income_rows
        ):
            year = loan_row["year"]
            if year > project_end_year:
                rows.append({
                    **dict.fromkeys(rows[0], None),
                    "year": year, "phase": "运营结束",
                })
                continue

            revenue = revenue_row["revenue_excluding_tax"]  # 营业收入，万元
            recovery = residual_value if year == project_end_year else 0.0  # 回收余值
            inflow = revenue + recovery  # 现金流入
            if year == 1:
                investment = static_investment * equity_factor * first_ratio
            elif year == second_year:
                investment = static_investment * equity_factor * (1 - first_ratio)
            else:
                investment = 0.0
            principal = loan_row["principal_repayment"] if with_debt else 0.0
            interest = (  # 长期借款利息和流动资金借款利息
                cost_row["long_term_loan_interest"] + cost_row["working_capital_loan_interest"]
            ) if with_debt else 0.0
            operating_cost = cost_row["operating_cost"]
            surcharge = revenue_row["surcharge"]
            income_tax = income_row["income_tax"]
            net_cash_flow = (  # 净现金流量
                inflow - investment - principal - interest
                - operating_cost - surcharge - income_tax
            )
            previous_cumulative = cumulative
            cumulative += net_cash_flow
            estimated_payback = actual_payback = None
            if year > construction_years and payback_period is None and net_cash_flow > 0:
                estimated_payback = year - construction_years - cumulative / net_cash_flow
                if previous_cumulative < 0 <= cumulative:
                    actual_payback = estimated_payback
                    payback_period = actual_payback

            rows.append({
                "year": year,
                "phase": revenue_row["phase"],
                "revenue": revenue,
                "residual_value": recovery,
                "inflow": inflow,
                "construction_investment": investment,
                "principal_repayment": principal,
                "interest": interest,
                "operating_cost": operating_cost,
                "surcharge": surcharge,
                "income_tax": income_tax,
                "net_cash_flow": net_cash_flow,
                "cumulative_cash_flow": cumulative,
                "estimated_payback_period": estimated_payback,
                "payback_period": actual_payback,
            })

        active_rows = rows[:project_end_year]
        irr = _irr([row["net_cash_flow"] for row in active_rows])
        return {
            "summary": {
                "irr": irr,
                "static_payback_period": payback_period,
                "inflow_total": sum(row["inflow"] for row in active_rows),
                "construction_investment_total": sum(row["construction_investment"] for row in active_rows),
                "principal_repayment_total": sum(row["principal_repayment"] for row in active_rows),
                "interest_total": sum(row["interest"] for row in active_rows),
                "operating_cost_total": sum(row["operating_cost"] for row in active_rows),
                "surcharge_total": sum(row["surcharge"] for row in active_rows),
                "income_tax_total": sum(row["income_tax"] for row in active_rows),
                "net_cash_flow_total": sum(row["net_cash_flow"] for row in active_rows),
                "residual_value": residual_value,
            },
            "schedule": rows,
        }

    return {
        "unit": "万元",
        "capital": {"title": "资本金现金流量表", "unit": "万元", **build(equity_ratio, True)},
        "total_investment": {"title": "全投资现金流量表", "unit": "万元", **build(1.0, False)},
    }
