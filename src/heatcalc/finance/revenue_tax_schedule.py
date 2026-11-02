"""收入及税金：收入除税、购电进项税和建设期额度的逐年抵扣。"""

from math import isfinite
from typing import Any, Literal


def calculate_revenue_tax_schedule(
    loan_schedule: dict[str, Any],
    cost_schedule: dict[str, Any],
    operating_years: int,
    income_amount_basis: Literal["tax_inclusive", "tax_exclusive"],
    steam_revenue_by_year: list[float],
    carbon_revenue_by_year: list[float],
    steam_volume_by_year: list[float | None],
    steam_vat_rate: float,
    carbon_vat_rate: float,
    output_vat_rate: float,
    input_vat_rate: float,
    construction_credit_ratio: float,
    surcharge_rate: float,
) -> dict[str, Any]:
    """金额单位为万元，蒸汽量为万吨，年度列表从项目第1年排列。

    销项税按原表对不含税收入合计统一计税；购电进项取同年成本表的不含税
    电费。留抵余额只跟踪建设期初始额度，年度进项大于销项时应缴额归零。
    """
    loan_rows = loan_schedule["schedule"]
    cost_rows = cost_schedule["schedule"]
    years = len(loan_rows)
    if not years or len(cost_rows) != years:
        raise ValueError("收入及税金表需要年份完整且一致的借款表和成本表")
    for index, (loan_row, cost_row) in enumerate(zip(loan_rows, cost_rows), start=1):
        if loan_row["year"] != index or cost_row["year"] != index or loan_row["phase"] != cost_row["phase"]:
            raise ValueError("借款表和成本表的项目年份、建设期及运营期必须一致")
    available_years = sum(row["phase"] == "运营期" for row in loan_rows)
    if isinstance(operating_years, bool) or not isinstance(operating_years, int) or not 1 <= operating_years <= available_years:
        raise ValueError("运营年数必须为正整数，且借款表和成本表须覆盖全部运营年份")
    if income_amount_basis not in ("tax_inclusive", "tax_exclusive"):
        raise ValueError("收入金额口径必须为含税或不含税")

    def nonnegative(value: float, label: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
            raise ValueError(f"{label}必须为大于等于零的有限数值")

    for label, values in (
        ("蒸汽收入", steam_revenue_by_year), ("碳收益", carbon_revenue_by_year),
        ("蒸汽量", steam_volume_by_year),
    ):
        if len(values) != years:
            raise ValueError(f"{label}年度列表须包含表内全部{years}个项目年份")
        for value in values:
            if label == "蒸汽量" and value is None:
                continue
            nonnegative(value, label)
    for label, rate in (
        ("蒸汽收入除税率", steam_vat_rate), ("碳收益除税率", carbon_vat_rate),
        ("销项税率", output_vat_rate), ("购电进项税率", input_vat_rate),
        ("建设期抵扣比例", construction_credit_ratio), ("附加税系数", surcharge_rate),
    ):
        nonnegative(rate, label)
        if rate > 1:
            raise ValueError(f"{label}须在0至1之间")
    static_investment = loan_schedule["summary"]["static_investment"]
    nonnegative(static_investment, "静态投资")
    for row in cost_rows:
        nonnegative(row["electricity_cost"], f"第{row['year']}年不含税电费")

    initial_credit = static_investment * construction_credit_ratio
    remaining_credit = initial_credit
    operating_index = 0
    schedule = []
    for loan_row, cost_row in zip(loan_rows, cost_rows):
        year = loan_row["year"]
        phase = loan_row["phase"]
        if phase == "运营期":
            operating_index += 1
        active = phase == "运营期" and operating_index <= operating_years
        if phase == "运营期" and not active:
            phase = "运营结束"

        steam_net = carbon_net = electricity_cost = output_vat = input_vat = 0.0
        if active:
            steam_net = steam_revenue_by_year[year - 1]
            carbon_net = carbon_revenue_by_year[year - 1]
            if income_amount_basis == "tax_inclusive":
                steam_net /= 1 + steam_vat_rate
                carbon_net /= 1 + carbon_vat_rate
            electricity_cost = cost_row["electricity_cost"]
            output_vat = (steam_net + carbon_net) * output_vat_rate
            input_vat = electricity_cost * input_vat_rate

        vat_before_credit = max(output_vat - input_vat, 0.0)
        opening_credit = remaining_credit
        credit_used = min(vat_before_credit, opening_credit)
        vat_paid = vat_before_credit - credit_used
        remaining_credit = opening_credit - credit_used
        schedule.append({
            "year": year,
            "phase": phase,
            "steam_volume": steam_volume_by_year[year - 1] if active else None,
            "steam_revenue_excluding_tax": steam_net,
            "carbon_revenue_excluding_tax": carbon_net,
            "revenue_excluding_tax": steam_net + carbon_net,
            "electricity_cost": electricity_cost,
            "output_vat": output_vat,
            "input_vat": input_vat,
            "vat_before_credit": vat_before_credit,
            "opening_construction_credit": opening_credit,
            "construction_credit_used": credit_used,
            "construction_credit_balance": remaining_credit,
            "vat_paid": vat_paid,
            "surcharge": vat_paid * surcharge_rate,
        })

    total_fields = (
        "steam_revenue_excluding_tax", "carbon_revenue_excluding_tax", "revenue_excluding_tax",
        "output_vat", "input_vat", "vat_before_credit", "construction_credit_used", "vat_paid", "surcharge",
    )
    return {
        "unit": "万元",
        "summary": {
            "initial_construction_credit": initial_credit,
            **{f"{field}_total": sum(row[field] for row in schedule) for field in total_fields},
            "final_construction_credit_balance": remaining_credit,
        },
        "schedule": schedule,
    }
