"""经济测算统一工具，借款与成本按方案顺序执行。"""

from typing import Annotated, Any, Literal
from uuid import uuid4

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from heatcalc.agent.cost_inputs import CostScheduleInputs
from heatcalc.agent.loan_inputs import BankLoanInputs
from heatcalc.finance.economic_calculation import calculate_economic_step


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


class EconomicSchemeInputs(BaseModel):
    """经济测算的分步输入，两种步骤各自明确需要的参数。"""

    request: Annotated[LoanStep | CostStep, Field(discriminator="step")]  # 当前步骤的完整输入


@tool(args_schema=EconomicSchemeInputs)
def calculate_economic_scheme(request: LoanStep | CostStep) -> dict[str, Any]:
    """执行经济测算方案。先调用 loan 步骤，生成借款还本付息表。

    再调用 cost 步骤，传入同一 scheme_id、该方案的 loan_result 和成本输入。
    不得自行构造借款结果。缺少输入时请求经济测算参数表。
    金额单位为万元，比例使用小数，年度费用从项目第1年排列。
    """
    values = request.model_dump()  # 本步骤参数，不修改调用方数据
    return calculate_economic_step(**values)
