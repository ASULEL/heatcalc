"""经济测算中的成本输入定义。"""

from pydantic import BaseModel, ConfigDict, Field


def ratio_field(description: str, default_percent: float, group: str):
    """按百分数展示、按小数提交的比例字段。"""
    return Field(description=description, json_schema_extra={
        "unit": "小数", "display_unit": "%", "toToolFactor": 0.01,
        "default": default_percent, "group": group,
    })


class MaintenanceRatioPeriod(BaseModel):
    """维修费比例适用的年份区间。"""

    start_year: int = Field(description="开始年份")  # 起始项目年份
    end_year: int = Field(description="结束年份")  # 结束项目年份
    ratio: float = Field(description="维修费比例")  # 维修费比例，小数


class CostScheduleInputs(BaseModel):
    """成本表输入，金额单位为万元，年度列表按项目年份排列。"""

    model_config = ConfigDict(
        json_schema_extra={
            "form_defaults": {
                "operating_years": 25,
                "depreciation_years": 15,
            },
        },
    )

    operating_years: int = Field(
        description="运营年数",
        json_schema_extra={"unit": "年", "default": 25, "group": "计算口径"},
    )
    depreciation_years: int = Field(
        description="折旧年限",
        json_schema_extra={"unit": "年", "default": 15, "group": "计算口径"},
    )
    construction_credit_ratio: float = ratio_field("建设期抵扣比例", 10, "计价系数")
    depreciable_ratio: float = ratio_field("可折旧比例", 95, "计价系数")
    insurance_rate: float = ratio_field("保险费率", 0.35, "计价系数")
    insurance_divisor: float = Field(
        default=1.06,
        description="保险费除税系数",
        json_schema_extra={"unit": "系数", "default": 1.06, "group": "计价系数"},
    )
    tax_divisor: float = Field(
        default=1.13,
        description="含税换算系数（电费、维修费）",
        json_schema_extra={"unit": "系数", "default": 1.13, "group": "计价系数"},
    )
    maintenance_ratio_periods: list[MaintenanceRatioPeriod] = Field(
        description="维修费比例区间",
        json_schema_extra={
            "unit": "区间列表",
            # Excel 当前案例：运营第1年起每5年一段，从 0.003 起每段增加 0.002。
            "period_defaults": {"years": 5, "first_ratio": 0.003, "ratio_step": 0.002},
            "group": "维修费",
        },
    )
    total_electricity_by_year: list[float] = Field(
        description="各年含税总电费",
        # 当前 Excel 经济性表的年度总成本 17651.8226 万元。
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 17651.8226, "group": "年度费用"},
    )
    water_cost_by_year: list[float] = Field(
        description="各年水费",
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 0.0, "group": "年度费用"},
    )
    labor_cost_by_year: list[float] = Field(
        description="各年人工费",
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 0.0, "group": "年度费用"},
    )
    amortization_expense_by_year: list[float] = Field(
        description="各年摊销费",
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 0.0, "group": "年度费用"},
    )
    working_capital_loan_interest_by_year: list[float] = Field(
        description="各年流动资金借款利息",
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 0.0, "group": "年度费用"},
    )
