import type { CalculationResult, CostCalculationResult, CostScheduleInputs, LoanCalculationResult, ParameterField } from '../src/types.ts'
import { bankResult } from './fixtures.ts'

export const costFields: ParameterField[] = [
  { name: 'equipment_total_cost', label: '设备总成本', value: 26400 },
  { name: 'depreciation_years', label: '折旧年限', value: 20 },
  {
    name: 'maintenance_ratio_periods', label: '维修费比例区间', value: null,
    periodDefaults: { years: 5, first_ratio: 0.003, ratio_step: 0.002 },
  },
  { name: 'total_electricity_by_year', label: '各年含税总电费', value: null, annualDefault: 2390.4133 },
  { name: 'water_cost_by_year', label: '各年水费', value: null, annualDefault: 0 },
  { name: 'labor_cost_by_year', label: '各年人工费', value: null, annualDefault: 216 },
  { name: 'amortization_expense_by_year', label: '各年摊销费', value: null, annualDefault: 0 },
  { name: 'working_capital_loan_interest_by_year', label: '各年流动资金借款利息', value: null, annualDefault: 0 },
].map(field => ({
  ...field, unit: '万元', group: '计算参数', advanced: false,
  required: true, toolName: 'calculate_economic_scheme', schemeStep: 'cost' as const,
}))

export const costInputs: CostScheduleInputs = {
  equipment_total_cost: 26400,
  depreciation_years: 20,
  maintenance_ratio_periods: [{ start_year: 3, end_year: 3, ratio: 0.003 }],
  total_electricity_by_year: [0, 0, 2390.4133],
  water_cost_by_year: [0, 0, 0],
  labor_cost_by_year: [0, 0, 216],
  amortization_expense_by_year: [0, 0, 0],
  working_capital_loan_interest_by_year: [0, 0, 0],
}

export const costResult: CostCalculationResult = {
  table_type: 'cost', inputs: costInputs, unit: '万元',
  summary: {
    operating_cost_total: 2496.4100000000003,
    depreciation_amortization_total: 1488.0811837168144,
    financial_cost_total: 856.1000448,
    total_cost: 4840.591228516814,
  },
  schedule: bankResult.schedule.map(row => ({
    year: row.year, phase: row.phase,
    maintenance_ratio: row.year === 3 ? 0.003 : 0,
    electricity_cost: row.year === 3 ? 2115.4100000000003 : 0,
    water_cost: 0, labor_cost: row.year === 3 ? 216 : 0,
    insurance_cost: row.year === 3 ? 85.8 : 0,
    maintenance_cost: row.year === 3 ? 79.2 : 0,
    depreciation_cost: row.year === 3 ? 1488.0811837168144 : 0,
    amortization_expense: 0,
    long_term_loan_interest: row.year === 3 ? 856.1000448 : 0,
    working_capital_loan_interest: 0,
    operating_cost: row.year === 3 ? 2496.4100000000003 : 0,
    depreciation_amortization: row.year === 3 ? 1488.0811837168144 : 0,
    financial_cost: row.year === 3 ? 856.1000448 : 0,
    total_cost: row.year === 3 ? 4840.591228516814 : 0,
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
