import type { CalculationResult, CostCalculationResult, CostScheduleInputs, LoanCalculationResult, ParameterField } from '../src/types.ts'
import { bankResult } from './fixtures.ts'

function field(partial: Omit<ParameterField, 'advanced' | 'required' | 'toolName' | 'schemeStep'>): ParameterField {
  return {
    advanced: false, required: true, toolName: 'calculate_economic_scheme', schemeStep: 'cost', ...partial,
  }
}

export const costFields: ParameterField[] = [
  field({ name: 'operating_years', label: '运营年数', value: 25, unit: '年', group: '计算口径' }),
  field({ name: 'depreciation_years', label: '折旧年限', value: 15, unit: '年', group: '计算口径' }),
  field({
    name: 'construction_credit_ratio', label: '建设期抵扣比例', value: 10,
    unit: '%', group: '计价系数', toToolFactor: 0.01, isDefault: true,
  }),
  field({
    name: 'depreciable_ratio', label: '可折旧比例', value: 95,
    unit: '%', group: '计价系数', toToolFactor: 0.01, isDefault: true,
  }),
  field({
    name: 'insurance_rate', label: '保险费率', value: 0.35,
    unit: '%', group: '计价系数', toToolFactor: 0.01, isDefault: true,
  }),
  field({ name: 'insurance_divisor', label: '保险费除税系数', value: 1.06, unit: '系数', group: '计价系数', isDefault: true }),
  field({ name: 'tax_divisor', label: '含税换算系数（电费、维修费）', value: 1.13, unit: '系数', group: '计价系数', isDefault: true }),
  field({
    name: 'maintenance_ratio_periods', label: '维修费比例区间', value: null,
    unit: '区间列表', group: '维修费',
    periodDefaults: { years: 5, first_ratio: 0.003, ratio_step: 0.002 },
  }),
  field({ name: 'total_electricity_by_year', label: '各年含税总电费', value: null, unit: '万元，按年份排列', group: '年度费用', annualDefault: 17651.8226 }),
  field({ name: 'water_cost_by_year', label: '各年水费', value: null, unit: '万元，按年份排列', group: '年度费用', annualDefault: 0 }),
  field({ name: 'labor_cost_by_year', label: '各年人工费', value: null, unit: '万元，按年份排列', group: '年度费用', annualDefault: 0 }),
  field({ name: 'amortization_expense_by_year', label: '各年摊销费', value: null, unit: '万元，按年份排列', group: '年度费用', annualDefault: 0 }),
  field({ name: 'working_capital_loan_interest_by_year', label: '各年流动资金借款利息', value: null, unit: '万元，按年份排列', group: '年度费用', annualDefault: 0 }),
]

export const costInputs: CostScheduleInputs = {
  operating_years: 1,
  depreciation_years: 15,
  construction_credit_ratio: 0.10,
  depreciable_ratio: 0.95,
  insurance_rate: 0.0035,
  insurance_divisor: 1.06,
  tax_divisor: 1.13,
  maintenance_ratio_periods: [{ start_year: 3, end_year: 3, ratio: 0.003 }],
  total_electricity_by_year: [0, 0, 17651.8226],
  water_cost_by_year: [0, 0, 0],
  labor_cost_by_year: [0, 0, 0],
  amortization_expense_by_year: [0, 0, 0],
  working_capital_loan_interest_by_year: [0, 0, 0],
}

export const costResult: CostCalculationResult = {
  table_type: 'cost', inputs: costInputs, unit: '万元',
  summary: {
    operating_cost_total: 15780.0491084,
    depreciation_amortization_total: 1690.1688648,
    financial_cost_total: 630.3645187,
    total_cost: 18100.5824919,
  },
  schedule: bankResult.schedule.map(row => ({
    year: row.year, phase: row.phase,
    maintenance_ratio: row.year === 3 ? 0.003 : 0,
    electricity_cost: row.year === 3 ? 15621.0819469 : 0,
    water_cost: 0, labor_cost: 0,
    insurance_cost: row.year === 3 ? 88.1170461 : 0,
    maintenance_cost: row.year === 3 ? 70.8501154 : 0,
    depreciation_cost: row.year === 3 ? 1690.1688648 : 0,
    amortization_expense: 0,
    long_term_loan_interest: row.year === 3 ? 630.3645187 : 0,
    working_capital_loan_interest: 0,
    operating_cost: row.year === 3 ? 15780.0491084 : 0,
    depreciation_amortization: row.year === 3 ? 1690.1688648 : 0,
    financial_cost: row.year === 3 ? 630.3645187 : 0,
    total_cost: row.year === 3 ? 18100.5824919 : 0,
  })),
}

export function loanWithCalendar(years: number, constructionYears: number): LoanCalculationResult {
  // 仅为前端输入测试扩展年份；费用计算仍在 Python 测试中验证。
  return {
    ...bankResult,
    inputs: { ...bankResult.inputs, schedule_years: years, construction_years: constructionYears },
    schedule: Array.from({ length: years }, (_, index) => ({
      ...bankResult.schedule[2]!, year: index + 1,
      phase: index < constructionYears ? '建设期' : '运营期',
    })),
  }
}

export const economicCostResult: CalculationResult = {
  tool_name: 'calculate_economic_scheme', scheme_id: 'scheme-1', step: 'cost',
  loan_result: bankResult, cost_result: costResult,
}
