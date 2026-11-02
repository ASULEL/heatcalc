"""所得税计算。"""

from typing import Any


def calculate_income_tax_schedule(
    cost_schedule: dict[str, Any],
    revenue_tax_schedule: dict[str, Any],
    income_tax_rate: float,
) -> dict[str, Any]:
    """按成本表和收入及税金表的年度数据计算所得税。

    利润总额 = 营业收入 − 附加税 − 总成本。亏损年度不缴税，亏损余额结转到
    以后年度，盈利时先弥补再计税；当前不设结转年限。
    金额单位为万元，所得税率使用小数。
    """
    carryforward_loss = 0.0  # 年初可弥补亏损余额，万元
    schedule: list[dict[str, Any]] = []  # 所得税逐年明细

    for cost_row, revenue_row in zip(
        cost_schedule["schedule"], revenue_tax_schedule["schedule"]
    ):
        revenue = revenue_row["revenue_excluding_tax"]  # 不含税营业收入，万元
        surcharge = revenue_row["surcharge"]  # 城建及教育附加，万元
        total_cost = cost_row["total_cost"]  # 总成本，万元
        total_profit = revenue - surcharge - total_cost  # 利润总额，万元
        current_year_loss = min(total_profit, 0.0)  # 本年亏损，亏损为负数
        loss_offset = min(max(total_profit, 0.0), carryforward_loss)  # 弥补以前年度亏损
        taxable_income = max(total_profit, 0.0) - loss_offset  # 应纳税所得额
        income_tax = taxable_income * income_tax_rate  # 所得税
        net_profit = total_profit - income_tax  # 净利润

        carryforward_loss = (  # 年末可弥补亏损余额
            carryforward_loss + max(-total_profit, 0.0) - loss_offset
        )

        schedule.append({
            "year": cost_row["year"],
            "phase": revenue_row["phase"],
            "revenue": revenue,
            "surcharge": surcharge,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "current_year_loss": current_year_loss,
            "carryforward_loss": carryforward_loss,
            "loss_offset": loss_offset,
            "taxable_income": taxable_income,
            "income_tax": income_tax,
            "net_profit": net_profit,
        })

    return {
        "unit": "万元",
        "summary": {
            "revenue_total": sum(row["revenue"] for row in schedule),
            "surcharge_total": sum(row["surcharge"] for row in schedule),
            "total_cost_total": sum(row["total_cost"] for row in schedule),
            "total_profit": sum(row["total_profit"] for row in schedule),
            "income_tax_total": sum(row["income_tax"] for row in schedule),
            "net_profit_total": sum(row["net_profit"] for row in schedule),
            "final_carryforward_loss": carryforward_loss,
        },
        "schedule": schedule,
    }
