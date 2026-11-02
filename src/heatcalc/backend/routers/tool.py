from datetime import datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from heatcalc.agent.economic_tool import ECONOMIC_STEP_MESSAGES, EconomicSchemeInputs, calculate_economic_scheme
from heatcalc.agent.parameter_specs import build_economic_form, build_next_economic_form
from heatcalc.export.excel_export import build_scheme_workbook

router = APIRouter(prefix="/api/tools", tags=["tools"])


class ExportSchemeRequest(BaseModel):
    """导出当前方案六张财务表所需的原始结果。"""

    scheme_name: str
    loan_result: dict[str, Any]
    cost_result: dict[str, Any]
    revenue_tax_result: dict[str, Any]
    income_tax_result: dict[str, Any]
    cash_flow_result: dict[str, Any]


@router.get("/calculate_economic_scheme/parameters")
def economic_parameters():
    """方案入口先展示借款输入，成本参数在借款计算完成后展示。"""
    return {
        "response": "经济测算 · 第1步：请填写借款参数，生成借款还本付息表。",
        "parameter_form": build_economic_form("loan"),
    }


@router.post("/calculate_economic_scheme")
def economic_scheme(inputs: EconomicSchemeInputs):
    """各步骤共用入口，下一步表单随本次原始结果返回。"""
    try:
        result = calculate_economic_scheme.invoke(inputs.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "response": ECONOMIC_STEP_MESSAGES[result["step"]],
        "parameter_form": build_next_economic_form(result),
        "calculation_results": [{"tool_name": calculate_economic_scheme.name, **result}],
    }


@router.post("/calculate_economic_scheme/export")
def export_economic_scheme(request: ExportSchemeRequest):
    """按当前方案结果生成六张财务表的公式版 Excel 并下载。"""
    exported_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    content = build_scheme_workbook(
        scheme_name=request.scheme_name,
        loan_result=request.loan_result,
        cost_result=request.cost_result,
        revenue_tax_result=request.revenue_tax_result,
        income_tax_result=request.income_tax_result,
        cash_flow_result=request.cash_flow_result,
        exported_at=exported_at,
    )
    filename = f"经济测算_{request.scheme_name}_{datetime.now():%Y%m%d}.xlsx"
    return Response(
        content=content,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
