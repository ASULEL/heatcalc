export interface UserProfile {
  displayName: string
}

export type EconomicStep = 'loan' | 'cost' | 'revenue_tax' | 'income_tax' | 'cash_flow'

export interface ParameterField {
  name: string
  label: string
  unit: string
  group: string
  advanced: boolean
  value: unknown // 标量或成本表的年度、区间输入
  required: boolean
  isDefault?: boolean
  inputType?: 'text' | 'select'
  options?: Array<{ value: string; label: string }>
  toToolFactor?: number
  toolName?: string // 表单所属工具
  schemeStep?: EconomicStep // 经济测算的当前步骤
  annualDefault?: number | null // 年度金额或数量的可修改示例
  periodDefaults?: { years: number; first_ratio: number; ratio_step: number } // 维修区间的可修改示例
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  parameterForm?: ParameterField[]
  calculationResults?: CalculationResult[]
  schemeName?: string // 本条消息所属方案名称
  economicStep?: { schemeId: string; step: EconomicStep; loanResult?: LoanCalculationResult; costResult?: CostCalculationResult; revenueTaxResult?: RevenueTaxResult; incomeTaxResult?: IncomeTaxResult }
  submitted?: boolean // 已成功提交的历史表单只读
  superseded?: boolean // 来源已被后续修改替代，不能继续提交
  submittedValues?: Record<string, string> // 本次提交的标量参数快照
  submittedCostInputs?: CostScheduleInputs // 本次提交的年度费用快照
  submittedRevenueTaxInputs?: RevenueTaxInputs // 本次提交的收入及税金快照
  submittedIncomeTaxInputs?: IncomeTaxInputs // 本次提交的所得税快照
  submittedCashFlowInputs?: CashFlowInputs // 本次提交的现金流量快照
}

export interface LoanScheduleRow {
  year: number // 项目年份
  phase: string // 建设期或运营期
  beginning_balance: number // 年初贷款余额，万元
  new_borrowing: number // 当年新增贷款，万元
  principal_repayment: number // 当年偿还本金，万元
  interest_expense: number // 当年利息，万元
  capitalized_interest: number // 资本化利息，万元
  cash_interest: number // 现金支付利息，万元
  ending_balance: number // 年末贷款余额，万元
}

export interface LoanCalculationResult {
  table_type: 'loan' // 借款表
  inputs: Record<string, number> // 实际使用的输入参数
  unit: string // 金额单位
  summary: Record<string, number> // 原始汇总结果
  schedule: LoanScheduleRow[] // 原始逐年数据，可按字段提取整列
}

export interface MaintenanceRatioPeriod {
  start_year: number // 起始项目年份
  end_year: number // 结束项目年份
  ratio: number // 维修费比例，小数
}

export interface CostScheduleInputs {
  operating_years: number // 运营年数，年
  depreciation_years: number // 折旧年限，年
  construction_credit_ratio: number // 建设期可抵扣税额占静态投资比例，小数
  depreciable_ratio: number // 扣除残值后的可折旧比例，小数
  insurance_rate: number // 保险费率，小数
  insurance_divisor: number // 保险费除税系数
  tax_divisor: number // 电费及维修费的含税换算系数
  maintenance_ratio_periods: MaintenanceRatioPeriod[] // 维修费比例区间
  total_electricity_by_year: number[] // 含税总电费，万元
  water_cost_by_year: number[] // 水费，万元
  labor_cost_by_year: number[] // 人工费，万元
  amortization_expense_by_year: number[] // 摊销费，万元
  working_capital_loan_interest_by_year: number[] // 流动资金借款利息，万元
}

export type AnnualCostField =
  | 'total_electricity_by_year' | 'water_cost_by_year' | 'labor_cost_by_year'
  | 'amortization_expense_by_year' | 'working_capital_loan_interest_by_year'

export interface CostScheduleRow {
  year: number // 项目年份
  phase: string // 建设期或运营期
  maintenance_ratio: number // 当年维修费比例
  electricity_cost: number // 不含税电费，万元
  water_cost: number // 水费，万元
  labor_cost: number // 人工费，万元
  insurance_cost: number // 保险费，万元
  maintenance_cost: number // 维修费，万元
  depreciation_cost: number // 折旧费，万元
  amortization_expense: number // 摊销费，万元
  long_term_loan_interest: number // 长期借款利息，万元
  working_capital_loan_interest: number // 流动资金借款利息，万元
  operating_cost: number // 经营成本小计，万元
  depreciation_amortization: number // 折旧摊销小计，万元
  financial_cost: number // 财务成本小计，万元
  total_cost: number // 总成本，万元
}

export interface CostCalculationResult {
  table_type: 'cost' // 成本表
  inputs: CostScheduleInputs // 实际输入及引用的借款表
  unit: string // 金额单位
  summary: Record<string, number> // 全周期汇总
  schedule: CostScheduleRow[] // 原始年度成本
}

export interface RevenueTaxInputs {
  operating_years: number
  income_amount_basis: 'tax_inclusive' | 'tax_exclusive'
  steam_vat_rate: number
  carbon_vat_rate: number
  output_vat_rate: number
  input_vat_rate: number
  construction_credit_ratio: number
  surcharge_rate: number
  steam_revenue_by_year: number[]
  carbon_revenue_by_year: number[]
  steam_volume_by_year: Array<number | null>
}

export type RevenueTaxAnnualField = 'steam_revenue_by_year' | 'carbon_revenue_by_year' | 'steam_volume_by_year'

export interface RevenueTaxRow {
  year: number
  phase: string
  steam_volume: number | null
  steam_revenue_excluding_tax: number
  carbon_revenue_excluding_tax: number
  revenue_excluding_tax: number
  electricity_cost: number
  output_vat: number
  input_vat: number
  vat_before_credit: number
  opening_construction_credit: number
  construction_credit_used: number
  construction_credit_balance: number
  vat_paid: number
  surcharge: number
}

export interface RevenueTaxResult {
  table_type: 'revenue_tax'
  inputs: RevenueTaxInputs
  unit: string
  summary: Record<string, number>
  schedule: RevenueTaxRow[]
}

export interface IncomeTaxInputs {
  income_tax_rate: number // 所得税率，小数
}

export interface IncomeTaxRow {
  year: number
  phase: string
  revenue: number
  surcharge: number
  total_cost: number
  total_profit: number
  current_year_loss: number
  carryforward_loss: number
  loss_offset: number
  taxable_income: number
  income_tax: number
  net_profit: number
}

export interface IncomeTaxResult {
  table_type: 'income_tax'
  inputs: IncomeTaxInputs
  unit: string
  summary: Record<string, number>
  schedule: IncomeTaxRow[]
}

export interface CashFlowInputs {
  equity_ratio: number // 资本金比例，小数
}

export interface CashFlowRow {
  year: number
  phase: string
  revenue: number | null
  residual_value: number | null
  inflow: number | null
  construction_investment: number | null
  principal_repayment: number | null
  interest: number | null
  operating_cost: number | null
  surcharge: number | null
  income_tax: number | null
  net_cash_flow: number | null
  cumulative_cash_flow: number | null
  estimated_payback_period: number | null
  payback_period: number | null
}

export interface CashFlowTableResult {
  title: string
  unit: string
  summary: Record<string, number | null>
  schedule: CashFlowRow[]
}

export interface CashFlowResult {
  table_type: 'cash_flow'
  inputs: CashFlowInputs
  unit: string
  capital: CashFlowTableResult
  total_investment: CashFlowTableResult
}

export interface CalculationResult {
  tool_name: 'calculate_economic_scheme' // 对外统一的方案工具
  scheme_id: string // 方案编号
  step: EconomicStep // 本次完成的步骤
  loan_result: LoanCalculationResult // 当前方案的借款原始结果
  cost_result?: CostCalculationResult // 成本步骤完成后生成
  revenue_tax_result?: RevenueTaxResult
  income_tax_result?: IncomeTaxResult
  cash_flow_result?: CashFlowResult
}

export interface EconomicScheme {
  id: string // 方案编号
  name: string // 方案名称
  stage: EconomicStep | 'completed' // 当前进度
  loanResult?: LoanCalculationResult // 本方案借款表
  costResult?: CostCalculationResult // 本方案成本表
  revenueTaxResult?: RevenueTaxResult
  incomeTaxResult?: IncomeTaxResult
  cashFlowResult?: CashFlowResult
}

export type EconomicRequest =
  | { step: 'loan'; scheme_id: string; inputs: Record<string, unknown> }
  | { step: 'cost'; scheme_id: string; loan_result: LoanCalculationResult; inputs: CostScheduleInputs }
  | { step: 'revenue_tax'; scheme_id: string; loan_result: LoanCalculationResult; cost_result: CostCalculationResult; inputs: RevenueTaxInputs }
  | {
    step: 'income_tax'; scheme_id: string; loan_result: LoanCalculationResult
    cost_result: CostCalculationResult; revenue_tax_result: RevenueTaxResult; inputs: IncomeTaxInputs
  }
  | {
    step: 'cash_flow'; scheme_id: string; loan_result: LoanCalculationResult
    cost_result: CostCalculationResult; revenue_tax_result: RevenueTaxResult
    income_tax_result: IncomeTaxResult; inputs: CashFlowInputs
  }

export interface Conversation {
  id: string
  title: string
  hasCustomTitle: boolean
  messages: ChatMessage[]
  scenario: {
    calculationResults: CalculationResult[] // 每个方案的最新结果，历史版本保留在消息中
    economicSchemes: EconomicScheme[] // 当前对话的经济测算方案，暂存在页面内存
  }
}
