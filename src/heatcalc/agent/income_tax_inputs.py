"""经济测算中的所得税输入定义。"""

from pydantic import BaseModel, Field


class IncomeTaxInputs(BaseModel):
    """所得税输入。"""

    income_tax_rate: float = Field(
        default=0.25,
        description="所得税率",
        json_schema_extra={
            "unit": "小数", "display_unit": "%", "toToolFactor": 0.01,
            "default": 25, "group": "所得税参数",
        },
    )
