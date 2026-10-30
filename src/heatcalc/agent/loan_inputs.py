from pydantic import BaseModel, Field

from heatcalc.finance.loan_schedule import DEFAULT_LOAN_SCHEDULE_INPUTS


class BankLoanInputs(BaseModel):
    """经济测算的借款输入；示例值只供表单预填，实际调用仍须明确提供参数。"""

    static_investment: float = Field(
        description="静态投资",
        json_schema_extra={"unit": "万元", "default": DEFAULT_LOAN_SCHEDULE_INPUTS["static_investment"]},
    )  # 静态投资，万元
    loan_ratio: float = Field(
        description="贷款比例",
        json_schema_extra={"unit": "小数", "default": DEFAULT_LOAN_SCHEDULE_INPUTS["loan_ratio"]},
    )  # 贷款占静态投资的比例
    investment_interest_rate: float = Field(
        description="运营期贷款年利率",
        json_schema_extra={"unit": "小数", "default": DEFAULT_LOAN_SCHEDULE_INPUTS["investment_interest_rate"]},
    )  # 运营期贷款年利率
    construction_interest_rate: float = Field(
        description="建设期贷款年利率",
        json_schema_extra={"unit": "小数", "default": DEFAULT_LOAN_SCHEDULE_INPUTS["construction_interest_rate"]},
    )  # 建设期贷款年利率
    construction_years: int = Field(
        description="建设期年数",
        json_schema_extra={"unit": "年", "default": DEFAULT_LOAN_SCHEDULE_INPUTS["construction_years"]},
    )  # 建设期年数
    first_drawdown_ratio: float = Field(
        description="第1年提款比例",
        json_schema_extra={"unit": "小数", "default": DEFAULT_LOAN_SCHEDULE_INPUTS["first_drawdown_ratio"]},
    )  # 第1年提款占贷款总额的比例
    second_drawdown_year: int = Field(
        description="剩余贷款提款年份",
        json_schema_extra={"unit": "项目第几年", "default": 2},
    )  # 按最新确认口径，第2年提款剩余贷款
    repayment_years: int = Field(
        description="等额本金还本年数",
        json_schema_extra={"unit": "年", "default": DEFAULT_LOAN_SCHEDULE_INPUTS["repayment_years"]},
    )  # 从运营期第1年开始还本
    schedule_years: int = Field(
        description="表格总年数（含建设期）",
        json_schema_extra={"unit": "年", "default": DEFAULT_LOAN_SCHEDULE_INPUTS["schedule_years"]},
    )  # 表内列示年数
