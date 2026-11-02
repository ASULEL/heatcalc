"""经济测算统一工具，借款与成本按方案顺序执行。"""

from typing import Annotated, Any, Literal
from uuid import uuid4

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from heatcalc.agent.cash_flow_inputs import CashFlowInputs
from heatcalc.agent.cost_inputs import CostScheduleInputs
from heatcalc.agent.income_tax_inputs import IncomeTaxInputs
from heatcalc.agent.loan_inputs import BankLoanInputs
from heatcalc.agent.revenue_tax_inputs import RevenueTaxInputs
from heatcalc.finance.economic_calculation import calculate_economic_step


ECONOMIC_STEP_MESSAGES = {
    "loan": "已生成借款还本付息表。经济测算 · 第2步：请填写成本参数。",
    "cost": "已生成成本计算表。经济测算 · 第3步：请填写收入及税金参数。",
    "revenue_tax": "已生成收入及税金表。经济测算 · 第4步：请填写所得税参数。",
    "income_tax": "已生成所得税表。经济测算 · 第5步：请填写资本金比例。",
    "cash_flow": "经济测算完成，已生成资本金和全投资现金流量表。",
}


class LoanStep(BaseModel):
    """经济测算第一步：填写借款参数并生成借款表。"""

    step: Literal["loan"]  # 当前步骤
    scheme_id: str = Field(default_factory=lambda: str(uuid4()))  # 方案唯一编号
    inputs: BankLoanInputs  # 用户明确提交的借款参数


class CostStep(BaseModel):
    """经济测算第二步：引用本方案借款表并生成成本表。"""

    step: Literal["cost"]  # 当前步骤
    scheme_id: str  # 借款步骤所属的方案编号
    loan_result: dict[str, Any]  # 本方案已生成的借款原始结果
    inputs: CostScheduleInputs  # 用户明确提交的成本参数


class RevenueTaxStep(BaseModel):
    """经济测算第三步：引用本方案借款和成本结果计算收入及税金。"""

    step: Literal["revenue_tax"]
    scheme_id: str
    loan_result: dict[str, Any]
    cost_result: dict[str, Any]
    inputs: RevenueTaxInputs


class IncomeTaxStep(BaseModel):
    """经济测算第四步：引用本方案成本和收入税金结果计算所得税。"""

    step: Literal["income_tax"]
    scheme_id: str
    loan_result: dict[str, Any]
    cost_result: dict[str, Any]
    revenue_tax_result: dict[str, Any]
    inputs: IncomeTaxInputs


class CashFlowStep(BaseModel):
    """经济测算第五步：引用本方案前四张表计算资本金和全投资现金流量。"""

    step: Literal["cash_flow"]
    scheme_id: str
    loan_result: dict[str, Any]
    cost_result: dict[str, Any]
    revenue_tax_result: dict[str, Any]
    income_tax_result: dict[str, Any]
    inputs: CashFlowInputs


class EconomicSchemeInputs(BaseModel):
    """经济测算的分步输入，每一步明确其输入及已生成的来源。"""

    request: Annotated[
        LoanStep | CostStep | RevenueTaxStep | IncomeTaxStep | CashFlowStep,
        Field(discriminator="step"),
    ]


@tool(args_schema=EconomicSchemeInputs)
def calculate_economic_scheme(
    request: LoanStep | CostStep | RevenueTaxStep | IncomeTaxStep | CashFlowStep,
) -> dict[str, Any]:
    """执行经济测算方案。先调用 loan 步骤，生成借款还本付息表。

    再调用 cost 步骤，传入同一 scheme_id、该方案的 loan_result 和成本输入。
    再调用 revenue_tax 步骤，传入同一方案的 loan_result、cost_result 和税金输入。
    再调用 income_tax 步骤，传入同一方案的 cost_result、revenue_tax_result 和所得税率。
    最后调用 cash_flow 步骤，传入同一方案的前四张表和资本金比例。
    不得自行构造或重新计算来源。缺少输入时使用该方案的下一步参数表。
    金额单位为万元，比例使用小数，年度费用从项目第1年排列。
    """
    values = request.model_dump()  # 本步骤参数，不修改调用方数据
    return calculate_economic_step(**values)
