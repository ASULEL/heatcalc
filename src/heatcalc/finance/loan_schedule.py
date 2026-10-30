"""借款利息计算。"""

from typing import Any


# 来自“熔盐储能项目_借款还本付息表”的默认输入，金额单位为万元。
DEFAULT_LOAN_SCHEDULE_INPUTS = {
    "static_investment": 34320.0,              # 静态投资
    "loan_ratio": 0.80,                        # 贷款比例
    "investment_interest_rate": 0.03,          # 投资贷款利率
    "construction_interest_rate": 0.03,        # 建设期贷款利率
    "construction_years": 2,                   # 建设期年数
    "first_drawdown_ratio": 0.80,              # 第一次贷款比例，在第1年提款
    "second_drawdown_year": 3,                 # 第二次贷款年份
    "repayment_years": 15,                     # 还本期
    "schedule_years": 30,                      # 表内列示年数
}


def calculate_loan_schedule(
    static_investment: float,
    loan_ratio: float,
    investment_interest_rate: float,
    construction_interest_rate: float,
    construction_years: int,
    first_drawdown_ratio: float,
    second_drawdown_year: int,
    repayment_years: int,
    schedule_years: int,
) -> dict[str, Any]:
    """根据借款参数计算逐年还本付息明细。

    金额单位为万元，利率和比例使用小数。函数不把 Excel 中的默认值写入
    计算逻辑，调用方应明确传入全部输入；默认值由
    ``DEFAULT_LOAN_SCHEDULE_INPUTS`` 提供。

    :param static_investment: 静态投资 (万元)
    :param loan_ratio: 贷款比例 (小数)
    :param investment_interest_rate: 投资贷款利率 (小数)
    :param construction_interest_rate: 建设期贷款利率 (小数)
    :param construction_years: 建设期年数
    :param first_drawdown_ratio: 第一次贷款比例，在项目第1年提款 (小数)
    :param second_drawdown_year: 第二次贷款年份，第二次贷款比例为剩余比例
    :param repayment_years: 还本期 (年)
    :param schedule_years: 表内列示年数
    :return: 包含 summary 和 schedule 的字典。
        summary 为汇总结果，金额单位为万元；schedule 为逐年明细列表，
        每一行包含 year、phase、beginning_balance、new_borrowing、
        principal_repayment、interest_expense、capitalized_interest、
        cash_interest 和 ending_balance。
    """
    # 贷款提款参数。
    loan_amount = static_investment * loan_ratio
    second_drawdown_ratio = 1 - first_drawdown_ratio  # 第二次贷款比例
    first_drawdown_amount = loan_amount * first_drawdown_ratio  # 第一次贷款金额，万元
    second_drawdown_amount = loan_amount * second_drawdown_ratio  # 第二次贷款金额，万元

    # 还本期间参数。
    repayment_start_year = construction_years + 1  # 还本开始年份
    repayment_end_year = repayment_start_year + repayment_years - 1  # 还本结束年份

    schedule: list[dict[str, Any]] = []  # 逐年还本付息明细
    beginning_balance = 0.0  # 年初借款余额，万元
    operating_initial_balance = 0.0  # 运营期初借款余额，万元
    annual_principal = 0.0  # 每年等额还本金额，万元

    # 建设期：利息资本化，不偿还本金。
    for year in range(1, construction_years + 1):
        if year == 1:
            new_borrowing = first_drawdown_amount  # 当年新增借款，万元
        elif year == second_drawdown_year:
            new_borrowing = second_drawdown_amount  # 当年新增借款，万元
        else:
            new_borrowing = 0.0  # 当年新增借款，万元

        interest_expense = (  # 当年利息，万元
            beginning_balance + new_borrowing / 2
        ) * construction_interest_rate
        principal_repayment = 0.0  # 当年偿还本金，万元
        capitalized_interest = interest_expense  # 当年资本化利息，万元
        cash_interest = 0.0  # 当年现金支付利息，万元
        ending_balance = (  # 年末借款余额，万元
            beginning_balance + new_borrowing + capitalized_interest
        )
        phase = "建设期"  # 当前阶段

        schedule.append({
            "year": year,
            "phase": phase,
            "beginning_balance": beginning_balance,
            "new_borrowing": new_borrowing,
            "principal_repayment": principal_repayment,
            "interest_expense": interest_expense,
            "capitalized_interest": capitalized_interest,
            "cash_interest": cash_interest,
            "ending_balance": ending_balance,
        })
        beginning_balance = ending_balance

    # 运营期：支付现金利息，并按等额本金偿还贷款。
    for year in range(repayment_start_year, schedule_years + 1):
        if year == second_drawdown_year:
            new_borrowing = second_drawdown_amount  # 当年新增借款，万元
        else:
            new_borrowing = 0.0  # 当年新增借款，万元

        if year == repayment_start_year:
            operating_initial_balance = (  # 运营期初借款余额，万元
                beginning_balance + new_borrowing
            )
            annual_principal = (  # 每年等额还本金额，万元
                operating_initial_balance / repayment_years
            )

        interest_expense = (  # 当年利息，万元
            beginning_balance + new_borrowing
        ) * investment_interest_rate
        balance_before_repayment = (  # 还本前借款余额，万元
            beginning_balance + new_borrowing
        )

        if year <= repayment_end_year:
            principal_repayment = annual_principal
        else:
            principal_repayment = 0.0

        capitalized_interest = 0.0  # 当年资本化利息，万元
        cash_interest = interest_expense  # 当年现金支付利息，万元
        ending_balance = max(
            0.0,
            balance_before_repayment - principal_repayment,
        )  # 年末借款余额，万元
        phase = "运营期"  # 当前阶段

        schedule.append({
            "year": year,
            "phase": phase,
            "beginning_balance": beginning_balance,
            "new_borrowing": new_borrowing,
            "principal_repayment": principal_repayment,
            "interest_expense": interest_expense,
            "capitalized_interest": capitalized_interest,
            "cash_interest": cash_interest,
            "ending_balance": ending_balance,
        })
        beginning_balance = ending_balance

    # 汇总结果，金额单位为万元。
    construction_interest_total = sum(
        row["interest_expense"] for row in schedule[:construction_years]
    )  # 建设期利息合计，万元
    total_interest = sum(
        row["interest_expense"] for row in schedule
    )  # 全周期利息合计，万元
    total_principal_repayment = sum(
        row["principal_repayment"] for row in schedule
    )  # 全周期偿还本金合计，万元

    summary = {
        "static_investment": static_investment,
        "loan_amount": loan_amount,
        "construction_interest_total": construction_interest_total,
        "operating_initial_balance": operating_initial_balance,
        "annual_principal": annual_principal,
        "total_principal_repayment": total_principal_repayment,
        "total_interest": total_interest,
        "total_capitalized_interest": construction_interest_total,
        "total_cash_interest": total_interest - construction_interest_total,
        "total_investment_with_interest": (
            static_investment + construction_interest_total
        ),
        "repayment_end_year": repayment_end_year,
        "final_ending_balance": schedule[-1]["ending_balance"],
    }

    return {
        "unit": "万元",
        "summary": summary,
        "schedule": schedule,
    }
