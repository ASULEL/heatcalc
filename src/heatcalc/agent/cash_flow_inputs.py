"""经济测算中的现金流量表输入定义。"""

from pydantic import BaseModel, Field


class CashFlowInputs(BaseModel):
    """现金流量表输入。"""

    equity_ratio: float = Field(
        default=0.30,
        description="资本金比例",
        json_schema_extra={
            "unit": "小数", "display_unit": "%", "toToolFactor": 0.01,
            "default": 30, "group": "现金流参数",
        },
    )
