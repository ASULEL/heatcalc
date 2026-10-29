export interface UserProfile {
  displayName: string
}

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
  schemeStep?: 'loan' | 'cost' // 经济测算的当前步骤
  annualDefault?: number // 年度费用的可修改示例
  periodDefaults?: { years: number; first_ratio: number; ratio_step: number } // 维修区间的可修改示例
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  parameterForm?: ParameterField[]
  calculationResults?: CalculationResult[]
  schemeName?: string // 本条消息所属方案名称
  economicStep?: { schemeId: string; step: 'loan' | 'cost'; loanResult?: LoanCalculationResult } // 本消息固定的方案来源
  submitted?: boolean // 已成功提交的历史表单只读
  submittedValues?: Record<string, string> // 本次提交的标量参数快照
  submittedCostInputs?: CostScheduleInputs // 本次提交的年度费用快照
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
  equipment_total_cost: number // 设备总成本，万元
  depreciation_years: number // 折旧年限，年
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

export interface CalculationResult {
  tool_name: 'calculate_economic_scheme' // 对外统一的方案工具
  scheme_id: string // 方案编号
  step: 'loan' | 'cost' // 本次完成的步骤
  loan_result: LoanCalculationResult // 当前方案的借款原始结果
  cost_result?: CostCalculationResult // 成本步骤完成后生成
}

export interface EconomicScheme {
  id: string // 方案编号
  name: string // 方案名称
  stage: 'loan' | 'cost' | 'completed' // 当前进度
  loanResult?: LoanCalculationResult // 本方案借款表
  costResult?: CostCalculationResult // 本方案成本表
}

export type EconomicRequest =
  | { step: 'loan'; scheme_id: string; inputs: Record<string, unknown> }
  | { step: 'cost'; scheme_id: string; loan_result: LoanCalculationResult; inputs: CostScheduleInputs }

export interface Conversation {
  id: string
  title: string
  hasCustomTitle: boolean
  messages: ChatMessage[]
  scenario: {
    calculationResults: CalculationResult[] // 每次测算结果，供对话继续引用
    economicSchemes: EconomicScheme[] // 当前对话的经济测算方案，暂存在页面内存
  }
}
