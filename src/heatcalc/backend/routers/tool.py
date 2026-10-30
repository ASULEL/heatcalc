from fastapi import APIRouter

from heatcalc.agent.economic_tool import EconomicSchemeInputs, calculate_economic_scheme
from heatcalc.agent.parameter_specs import build_economic_form

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("/calculate_economic_scheme/parameters")
def economic_parameters():
    """方案入口先展示借款输入，成本参数在借款计算完成后展示。"""
    return {
        "response": "经济测算 · 第1步：请填写借款参数，生成借款还本付息表。",
        "parameter_form": build_economic_form("loan"),
    }


@router.post("/calculate_economic_scheme")
def economic_scheme(inputs: EconomicSchemeInputs):
    """两步共用一个工具入口，下一步表单随本次结果返回。"""
    result = calculate_economic_scheme.invoke(inputs.model_dump())  # 本方案原始计算结果
    is_loan_step = result["step"] == "loan"  # 借款完成后进入成本输入
    return {
        "response": (
            "已生成借款还本付息表。经济测算 · 第2步：请填写成本参数。"
            if is_loan_step else "经济测算完成，已生成成本计算表。"
        ),
        "parameter_form": build_economic_form("cost") if is_loan_step else [],
        "calculation_results": [{"tool_name": calculate_economic_scheme.name, **result}],
    }
