import type { CalculationResult, IncomeTaxInputs, IncomeTaxResult, ParameterField } from '../src/types.ts'
import { bankResult } from './fixtures.ts'
import { costResult } from './cost-fixtures.ts'
import { revenueTaxResult } from './revenue-tax-fixtures.ts'

export const incomeTaxFields: ParameterField[] = [{
  name: 'income_tax_rate', label: '所得税率', unit: '%', value: 25, toToolFactor: 0.01,
  group: '所得税参数', advanced: false, required: true,
  toolName: 'calculate_economic_scheme', schemeStep: 'income_tax',
}]

export const incomeTaxInputs: IncomeTaxInputs = { income_tax_rate: 0.25 }

export const incomeTaxResult: IncomeTaxResult = {
  table_type: 'income_tax', unit: '万元', inputs: incomeTaxInputs,
  summary: {
    revenue_total: 1000, surcharge_total: 10, total_cost_total: 600,
    total_profit: 390, income_tax_total: 97.5, net_profit_total: 292.5,
    final_carryforward_loss: 0,
  },
  schedule: bankResult.schedule.map(row => {
    const active = row.phase === '运营期'
    return {
      year: row.year, phase: row.phase,
      revenue: active ? 1000 : 0, surcharge: active ? 10 : 0, total_cost: active ? 600 : 0,
      total_profit: active ? 390 : 0, current_year_loss: 0, carryforward_loss: 0, loss_offset: 0,
      taxable_income: active ? 390 : 0, income_tax: active ? 97.5 : 0, net_profit: active ? 292.5 : 0,
    }
  }),
}

export const economicIncomeTaxResult: CalculationResult = {
  tool_name: 'calculate_economic_scheme', scheme_id: 'scheme-1', step: 'income_tax',
  loan_result: bankResult, cost_result: costResult,
  revenue_tax_result: revenueTaxResult, income_tax_result: incomeTaxResult,
}
