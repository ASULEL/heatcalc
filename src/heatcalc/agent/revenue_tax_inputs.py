"""收入及税金的参数定义；示例税率须经用户提交后才用于计算。"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


Amount = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Rate = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


def rate_field(description: str, example_percent: float):
    return Field(description=description, json_schema_extra={
        "unit": "小数", "display_unit": "%", "toToolFactor": 0.01,
        "default": example_percent, "group": "税率与抵扣参数",
    })


class RevenueTaxInputs(BaseModel):
    """按项目年份提供收入，金额为万元，蒸汽量为万吨。"""

    operating_years: int = Field(
        ge=1, description="运营年数",
        json_schema_extra={"unit": "年", "default": 25, "group": "收入计算口径"},
    )
    income_amount_basis: Literal["tax_inclusive", "tax_exclusive"] = Field(
        description="蒸汽收入与碳收益的输入金额口径",
        json_schema_extra={
            "unit": "金额口径", "default": "tax_inclusive", "group": "收入计算口径",
            "options": [
                {"value": "tax_inclusive", "label": "含税金额（计算时除税）"},
                {"value": "tax_exclusive", "label": "不含税金额（直接相加）"},
            ],
        },
    )
    steam_vat_rate: Rate = rate_field("蒸汽收入除税率", 9)
    carbon_vat_rate: Rate = rate_field("碳收益除税率", 13)
    output_vat_rate: Rate = rate_field("合计不含税收入的销项税率", 9)
    input_vat_rate: Rate = rate_field("购电进项税率", 13)
    construction_credit_ratio: Rate = rate_field("建设期可抵扣税额占静态投资比例", 10)
    surcharge_rate: Rate = rate_field("城建及教育附加系数", 10)
    steam_revenue_by_year: list[Amount] = Field(
        description="蒸汽收入",
        json_schema_extra={"unit": "万元", "annual_default": 20134.33652629279, "group": "年度收入"},
    )
    carbon_revenue_by_year: list[Amount] = Field(
        description="碳收益",
        json_schema_extra={"unit": "万元", "annual_default": 0.0, "group": "年度收入"},
    )
    steam_volume_by_year: list[Amount | None] = Field(
        description="蒸汽量",
        json_schema_extra={"unit": "万吨", "annual_default": None, "group": "年度收入"},
    )
