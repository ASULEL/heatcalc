"""按借款表年份计算项目成本。"""

from math import isfinite
from typing import Any


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    """检查数值为有限数；需要时要求大于零。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}必须为数值")
    if not isfinite(value):
        raise ValueError(f"{label}必须为有限数值")
    if positive and value <= 0:
        raise ValueError(f"{label}必须大于零")
    return float(value)


def _zero_row(year: int, phase: str) -> dict[str, Any]:
    """建设期及运营年数以外的年度，各列填零。"""
    return {
        "year": year,
        "phase": phase,
        "maintenance_ratio": 0.0,
        "electricity_cost": 0.0,
        "water_cost": 0.0,
        "labor_cost": 0.0,
        "insurance_cost": 0.0,
        "maintenance_cost": 0.0,
        "depreciation_cost": 0.0,
        "amortization_expense": 0.0,
        "long_term_loan_interest": 0.0,
        "working_capital_loan_interest": 0.0,
        "operating_cost": 0.0,
        "depreciation_amortization": 0.0,
        "financial_cost": 0.0,
        "total_cost": 0.0,
    }


def calculate_cost_schedule(
    loan_schedule: dict[str, Any],
    operating_years: int,
    depreciation_years: int,
    maintenance_ratio_periods: list[dict[str, Any]],
    total_electricity_by_year: list[float],
    water_cost_by_year: list[float],
    labor_cost_by_year: list[float],
    amortization_expense_by_year: list[float],
    working_capital_loan_interest_by_year: list[float],
    construction_credit_ratio: float,
    depreciable_ratio: float,
    insurance_rate: float,
    insurance_divisor: float,
    tax_divisor: float,
) -> dict[str, Any]:
    """按 Excel 成本计算表口径，根据借款表和成本输入计算逐年成本。

    计价基数 = 静态投资 × 可折旧比例 − 静态投资 × 建设期抵扣比例 + 建设期利息合计。
    电费、维修费分别按含税换算系数除税；保险费再按保险费除税系数换算；
    折旧费以计价基数乘可折旧比例后按折旧年限平均计提。
    所有金额单位为万元，年度列表的下标为项目年份减一，长度须与借款表一致。
    运营年数以外的年份保留行，但各列填零。

    :param loan_schedule: 借款表原始 summary 和 schedule，保留原始精度
    :param operating_years: 成本表计列费用的运营年数
    :param depreciation_years: 折旧年限，年
    :param maintenance_ratio_periods: 起止项目年份及维修比例，小数；未覆盖年份按零
    :param total_electricity_by_year: 各年含税电费，万元
    :param water_cost_by_year: 各年水费，万元
    :param labor_cost_by_year: 各年人工费，万元
    :param amortization_expense_by_year: 各年摊销费，当前手动输入，万元
    :param working_capital_loan_interest_by_year: 各年流动资金利息，当前手动输入，万元
    :param construction_credit_ratio: 建设期可抵扣税额占静态投资比例，小数
    :param depreciable_ratio: 扣除残值后的可折旧比例，小数
    :param insurance_rate: 保险费率，小数
    :param insurance_divisor: 保险费除税系数
    :param tax_divisor: 电费及维修费的含税换算系数
    :return: unit、全周期成本 summary、与借款表年份一致的成本 schedule。
        年度明细包含经营成本、折旧摊销、财务成本的各分项、小计和总成本。
    """
    loan_rows = loan_schedule["schedule"]  # 借款表逐年明细
    loan_summary = loan_schedule["summary"]  # 借款表汇总
    if not loan_rows:
        raise ValueError("借款表不能为空")
    years = len(loan_rows)  # 表内项目年份数
    if any(row["year"] != index for index, row in enumerate(loan_rows, start=1)):
        raise ValueError("借款表年份必须从第1年起连续排列")

    construction_years = sum(row["phase"] == "建设期" for row in loan_rows)  # 建设期年数
    available_years = years - construction_years  # 可用的运营年份数
    if (
        isinstance(operating_years, bool) or not isinstance(operating_years, int)
        or not 1 <= operating_years <= available_years
    ):
        raise ValueError("运营年数必须为正整数，且不超过借款表的运营年份")
    if (
        isinstance(depreciation_years, bool) or not isinstance(depreciation_years, int)
        or depreciation_years < 1
    ):
        raise ValueError("折旧年限必须为正整数")

    for label, rate in (
        ("建设期抵扣比例", construction_credit_ratio),
        ("可折旧比例", depreciable_ratio),
        ("保险费率", insurance_rate),
    ):
        if not 0 <= _number(rate, label) <= 1:
            raise ValueError(f"{label}须在0至1之间")
    for label, divisor in (
        ("保险费除税系数", insurance_divisor),
        ("含税换算系数", tax_divisor),
    ):
        _number(divisor, label, positive=True)

    annual_inputs = (
        ("各年含税总电费", total_electricity_by_year),
        ("各年水费", water_cost_by_year),
        ("各年人工费", labor_cost_by_year),
        ("各年摊销费", amortization_expense_by_year),
        ("各年流动资金借款利息", working_capital_loan_interest_by_year),
    )
    for label, values in annual_inputs:
        if len(values) != years:
            raise ValueError(f"{label}年度列表须包含借款表的全部{years}个项目年份")
        for value in values:
            if _number(value, label) < 0:
                raise ValueError(f"{label}必须大于等于零")

    for period in maintenance_ratio_periods:
        if period["start_year"] > period["end_year"]:
            raise ValueError("维修费区间的开始年份不能大于结束年份")
        if _number(period["ratio"], "维修费比例") < 0:
            raise ValueError("维修费比例必须大于等于零")

    static_investment = _number(loan_summary["static_investment"], "静态投资")  # 静态投资，万元
    construction_interest = _number(  # 建设期资本化利息合计，万元
        loan_summary.get("total_capitalized_interest", 0.0), "建设期利息合计",
    )
    construction_credit = (  # 建设期可抵扣税额，万元
        static_investment * construction_credit_ratio
    )
    cost_base = (  # 保险费、维修费和折旧费的计价基数，万元
        static_investment * depreciable_ratio
        - construction_credit
        + construction_interest
    )
    annual_depreciation = (  # 年折旧费，万元
        cost_base * depreciable_ratio / depreciation_years
    )

    schedule: list[dict[str, Any]] = []  # 成本表逐年明细
    operating_index = 0  # 已进入的运营年份序号

    for loan_row in loan_rows:
        year = loan_row["year"]
        if loan_row["phase"] == "建设期":
            # 建设期成本为零，建设期利息已经在借款表中资本化。
            schedule.append(_zero_row(year, loan_row["phase"]))
            continue

        operating_index += 1
        if operating_index > operating_years:
            # 运营年数以外的年份与 Excel 一致，保留行但填零。
            schedule.append(_zero_row(year, loan_row["phase"]))
            continue

        ratio = next(  # 当前年份的维修费比例，未覆盖年份按零
            (
                period["ratio"] for period in maintenance_ratio_periods
                if period["start_year"] <= year <= period["end_year"]
            ),
            0.0,
        )
        electricity_cost = total_electricity_by_year[year - 1] / tax_divisor  # 不含税电费
        insurance_cost = cost_base * insurance_rate / insurance_divisor  # 保险费
        maintenance_cost = cost_base * ratio / tax_divisor  # 维修费
        depreciation_cost = (  # 折旧费，计提到折旧年限为止
            annual_depreciation
            if year <= construction_years + depreciation_years else 0.0
        )
        long_term_loan_interest = loan_row["interest_expense"]  # 长期借款利息取自借款表
        operating_cost = (  # 经营成本小计
            electricity_cost
            + water_cost_by_year[year - 1]
            + labor_cost_by_year[year - 1]
            + insurance_cost
            + maintenance_cost
        )
        depreciation_amortization = (  # 折旧摊销小计
            depreciation_cost + amortization_expense_by_year[year - 1]
        )
        financial_cost = (  # 财务成本小计
            long_term_loan_interest + working_capital_loan_interest_by_year[year - 1]
        )

        schedule.append({
            "year": year,
            "phase": loan_row["phase"],
            "maintenance_ratio": ratio,
            "electricity_cost": electricity_cost,
            "water_cost": water_cost_by_year[year - 1],
            "labor_cost": labor_cost_by_year[year - 1],
            "insurance_cost": insurance_cost,
            "maintenance_cost": maintenance_cost,
            "depreciation_cost": depreciation_cost,
            "amortization_expense": amortization_expense_by_year[year - 1],
            "long_term_loan_interest": long_term_loan_interest,
            "working_capital_loan_interest": working_capital_loan_interest_by_year[year - 1],
            "operating_cost": operating_cost,
            "depreciation_amortization": depreciation_amortization,
            "financial_cost": financial_cost,
            "total_cost": operating_cost + depreciation_amortization + financial_cost,
        })

    return {
        "unit": "万元",
        "summary": {
            "static_investment": static_investment,
            "construction_credit": construction_credit,
            "construction_interest": construction_interest,
            "cost_base": cost_base,
            "annual_depreciation": annual_depreciation,
            "operating_cost_total": sum(row["operating_cost"] for row in schedule),
            "depreciation_amortization_total": sum(
                row["depreciation_amortization"] for row in schedule
            ),
            "financial_cost_total": sum(row["financial_cost"] for row in schedule),
            "total_cost": sum(row["total_cost"] for row in schedule),
        },
        "schedule": schedule,
    }
