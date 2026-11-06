import type { CalculationResult, ParameterField, RevenueTaxInputs, RevenueTaxResult } from '../src/types.ts'
import { bankResult } from './fixtures.ts'
import { costResult } from './cost-fixtures.ts'

export const revenueTaxFields: ParameterField[] = [
  { name: 'operating_years', label: '运营年数', unit: '年', value: 1 },
  {
    name: 'income_amount_basis', label: '收入金额口径', unit: '金额口径', value: 'tax_inclusive', inputType: 'select',
    options: [{ value: 'tax_inclusive', label: '含税金额（计算时除税）' }, { value: 'tax_exclusive', label: '不含税金额（直接相加）' }],
  },
  ...[
    ['steam_vat_rate', '蒸汽收入除税率', 9], ['carbon_vat_rate', '碳收益除税率', 13],
    ['output_vat_rate', '合计不含税收入的销项税率', 9], ['input_vat_rate', '购电进项税率', 13],
    ['construction_credit_ratio', '建设期可抵扣税额占静态投资比例', 10], ['surcharge_rate', '城建及教育附加系数', 10],
  ].map(([name, label, value]) => ({ name: String(name), label: String(label), value, unit: '%', toToolFactor: 0.01 })),
  { name: 'steam_revenue_by_year', label: '蒸汽收入', unit: '万元', value: null, annualDefault: 20134.33652629279 },
  { name: 'carbon_revenue_by_year', label: '碳收益', unit: '万元', value: null, annualDefault: 0 },
  { name: 'steam_volume_by_year', label: '蒸汽量', unit: '万吨', value: null, annualDefault: null },
].map(field => ({
  ...field, group: '收入及税金参数', advanced: false, required: true,
  toolName: 'calculate_economic_scheme', schemeStep: 'revenue_tax',
})) as ParameterField[]

export const revenueTaxInputs: RevenueTaxInputs = {
  operating_years: 1, income_amount_basis: 'tax_exclusive',
  steam_vat_rate: 0.09, carbon_vat_rate: 0.13, output_vat_rate: 0.1, input_vat_rate: 0,
  construction_credit_ratio: 0.001, surcharge_rate: 0.1,
  steam_revenue_by_year: [0, 0, 600], carbon_revenue_by_year: [0, 0, 0],
  steam_volume_by_year: [null, null, null],
}

export const revenueTaxResult: RevenueTaxResult = {
  table_type: 'revenue_tax', unit: '万元', inputs: revenueTaxInputs,
  summary: {
    initial_construction_credit: 34.32, construction_credit_used_total: 34.32,
    final_construction_credit_balance: 0, revenue_excluding_tax_total: 600, vat_paid_total: 25.68, surcharge_total: 2.568,
  },
  schedule: bankResult.schedule.map(row => {
    const active = row.phase === '运营期'
    return {
      year: row.year, phase: row.phase, steam_volume: null,
      steam_revenue_excluding_tax: active ? 600 : 0, carbon_revenue_excluding_tax: 0,
      revenue_excluding_tax: active ? 600 : 0, electricity_cost: active ? 2115.4100000000003 : 0,
      output_vat: active ? 60 : 0, input_vat: 0, vat_before_credit: active ? 60 : 0,
      opening_construction_credit: 34.32, construction_credit_used: active ? 34.32 : 0,
      construction_credit_balance: active ? 0 : 34.32, vat_paid: active ? 25.68 : 0, surcharge: active ? 2.568 : 0,
    }
  }),
}

export const economicRevenueTaxResult: CalculationResult = {
  tool_name: 'calculate_economic_scheme', scheme_id: 'scheme-1', step: 'revenue_tax',
  loan_result: bankResult, cost_result: costResult, revenue_tax_result: revenueTaxResult,
}
