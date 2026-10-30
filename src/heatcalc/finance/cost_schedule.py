"""按借款表年份计算项目成本。"""

from typing import Any


INSURANCE_RATE = 0.0025
# 保险费率，图片中按静态投资计取 0.25%，后续可能改为输入

DEPRECIATION_RESIDUAL_RATE = 0.95
# 扣除 5% 残值后的可折旧比例，目前固定为 0.95，后续可能改为输入

TAX_INCLUSIVE_FACTOR = 1.13
# 含税金额换算为不含税金额的除数，目前固定为 1.13，后续可能改为输入


def calculate_cost_schedule(
    loan_schedule: dict[str, Any],
    equipment_total_cost: float,
    depreciation_years: int,
    maintenance_ratio_periods: list[dict[str, Any]],
    total_electricity_by_year: list[float],
    water_cost_by_year: list[float],
    labor_cost_by_year: list[float],
    amortization_expense_by_year: list[float],
    working_capital_loan_interest_by_year: list[float],
) -> dict[str, Any]:
    """根据借款表和成本输入，计算逐年成本表。

    所有金额单位为万元。各年度输入列表的下标为项目年份减一，
    维修费比例使用起止年份区间输入，并覆盖全部运营年份。

    :param loan_schedule: 借款表原始 summary 和 schedule，保留原始精度
    :param equipment_total_cost: 设备总成本，万元
    :param depreciation_years: 用户输入的折旧年限，年
    :param maintenance_ratio_periods: 起止项目年份及维修比例，小数
    :param total_electricity_by_year: 各年含税电费，万元
    :param water_cost_by_year: 各年水费，万元
    :param labor_cost_by_year: 各年人工费，万元
    :param amortization_expense_by_year: 各年摊销费，当前手动输入，万元
    :param working_capital_loan_interest_by_year: 各年流动资金利息，当前手动输入，万元
    :return: unit、全周期成本 summary、与借款表年份一致的成本 schedule。
        年度明细包含经营成本、折旧摊销、财务成本的各分项、小计和总成本。
    """
    loan_rows = loan_schedule["schedule"]  # 借款表逐年明细
    loan_summary = loan_schedule["summary"]  # 借款表汇总
    construction_years = sum(row["phase"] == "建设期" for row in loan_rows)  # 建设期年数
    static_investment = loan_summary["static_investment"]  # 静态投资，万元
    depreciation_base = loan_summary["total_investment_with_interest"]  # 折旧费基数，万元
    annual_depreciation = (  # 年折旧费，万元
        depreciation_base
        * DEPRECIATION_RESIDUAL_RATE
        / TAX_INCLUSIVE_FACTOR
        / depreciation_years
    )
    schedule: list[dict[str, Any]] = []  # 成本表逐年明细
    year = 0  # 当前项目年份
    ratio = 0.0  # 当前维修费比例
    electricity_cost = 0.0  # 不含税电费，万元
    water_cost = 0.0  # 水费，万元
    labor_cost = 0.0  # 人工费，万元
    insurance_cost = 0.0  # 保险费，万元
    maintenance_cost = 0.0  # 维修费，万元
    depreciation_cost = 0.0  # 折旧费，万元
    amortization_expense = 0.0  # 摊销费，万元
    long_term_loan_interest = 0.0  # 长期借款利息，万元
    working_capital_loan_interest = 0.0  # 流动资金借款利息，万元
    operating_cost = 0.0  # 经营成本，万元
    depreciation_amortization = 0.0  # 折旧摊销，万元
    financial_cost = 0.0  # 财务成本，万元
    total_cost = 0.0  # 总成本，万元

    # 建设期成本为零，建设期利息已经在借款表中资本化。
    for loan_row in loan_rows[:construction_years]:
        schedule.append({
            "year": loan_row["year"],
            "phase": loan_row["phase"],
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
        })

    # 运营期逐年计算费用，年份和长期借款利息直接取自借款表。
    for loan_row in loan_rows[construction_years:]:
        year = loan_row["year"]
        ratio = next(
            period["ratio"] for period in maintenance_ratio_periods
            if period["start_year"] <= year <= period["end_year"]
        )
        electricity_cost = total_electricity_by_year[year - 1] / TAX_INCLUSIVE_FACTOR
        water_cost = water_cost_by_year[year - 1]
        labor_cost = labor_cost_by_year[year - 1]
        insurance_cost = static_investment * INSURANCE_RATE
        maintenance_cost = equipment_total_cost * ratio
        depreciation_cost = (
            annual_depreciation
            if year <= construction_years + depreciation_years else 0.0
        )
        amortization_expense = amortization_expense_by_year[year - 1]
        long_term_loan_interest = loan_row["interest_expense"]
        working_capital_loan_interest = working_capital_loan_interest_by_year[year - 1]

        operating_cost = (
            electricity_cost
            + water_cost
            + labor_cost
            + insurance_cost
            + maintenance_cost
        )
        depreciation_amortization = (
            depreciation_cost + amortization_expense
        )
        financial_cost = (
            long_term_loan_interest + working_capital_loan_interest
        )
        total_cost = (
            operating_cost + depreciation_amortization + financial_cost
        )

        schedule.append({
            "year": year,
            "phase": loan_row["phase"],
            "maintenance_ratio": ratio,
            "electricity_cost": electricity_cost,
            "water_cost": water_cost,
            "labor_cost": labor_cost,
            "insurance_cost": insurance_cost,
            "maintenance_cost": maintenance_cost,
            "depreciation_cost": depreciation_cost,
            "amortization_expense": amortization_expense,
            "long_term_loan_interest": long_term_loan_interest,
            "working_capital_loan_interest": working_capital_loan_interest,
            "operating_cost": operating_cost,
            "depreciation_amortization": depreciation_amortization,
            "financial_cost": financial_cost,
            "total_cost": total_cost,
        })

    return {
        "unit": "万元",
        "summary": {
            "operating_cost_total": sum(row["operating_cost"] for row in schedule),
            "depreciation_amortization_total": sum(
                row["depreciation_amortization"] for row in schedule
            ),
            "financial_cost_total": sum(row["financial_cost"] for row in schedule),
            "total_cost": sum(row["total_cost"] for row in schedule),
        },
        "schedule": schedule,
    }
