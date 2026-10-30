"""经济测算中的成本输入定义。"""

from pydantic import BaseModel, ConfigDict, Field


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
                "equipment_total_cost": 26400.0,
                "depreciation_years": 20,
            },
        },
    )

    equipment_total_cost: float = Field(
        description="设备总成本",
        json_schema_extra={"unit": "万元"},
    )
    depreciation_years: int = Field(
        description="折旧年限",
        json_schema_extra={"unit": "年"},
    )
    maintenance_ratio_periods: list[MaintenanceRatioPeriod] = Field(
        description="维修费比例区间",
        json_schema_extra={
            "unit": "区间列表",
            # 图片中的可修改示例：每5年一段，从 0.003 起每段增加 0.002。
            "period_defaults": {"years": 5, "first_ratio": 0.003, "ratio_step": 0.002},
        },
    )
    total_electricity_by_year: list[float] = Field(
        description="各年含税总电费",
        # 由图片中的不含税电费 2115.41 反推的可修改示例，不作为计算默认值。
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 2390.4133},
    )
    water_cost_by_year: list[float] = Field(
        description="各年水费",
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 0.0},
    )
    labor_cost_by_year: list[float] = Field(
        description="各年人工费",
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 216.0},
    )
    amortization_expense_by_year: list[float] = Field(
        description="各年摊销费",
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 0.0},
    )
    working_capital_loan_interest_by_year: list[float] = Field(
        description="各年流动资金借款利息",
        json_schema_extra={"unit": "万元，按年份排列", "annual_default": 0.0},
    )
