import type { CalculationResult, CashFlowInputs, CashFlowResult, ParameterField } from '../src/types.ts'
import { bankResult } from './fixtures.ts'
import { costResult } from './cost-fixtures.ts'
import { incomeTaxResult } from './income-tax-fixtures.ts'
import { revenueTaxResult } from './revenue-tax-fixtures.ts'

export const cashFlowFields: ParameterField[] = [{
  name: 'equity_ratio', label: '资本金比例', unit: '%', value: 30, toToolFactor: 0.01,
  group: '现金流参数', advanced: false, required: true,
  toolName: 'calculate_economic_scheme', schemeStep: 'cash_flow',
}]

export const cashFlowInputs: CashFlowInputs = { equity_ratio: 0.30 }

const capitalSchedule = [
  {
    year: 1, phase: '建设期', revenue: 0, residual_value: 0, inflow: 0,
    construction_investment: 100, principal_repayment: 0, interest: 0,
    operating_cost: 0, surcharge: 0, income_tax: 0, net_cash_flow: -100,
    cumulative_cash_flow: -100, estimated_payback_period: null, payback_period: null,
  },
  {
    year: 2, phase: '建设期', revenue: 0, residual_value: 0, inflow: 0,
    construction_investment: 25, principal_repayment: 0, interest: 0,
    operating_cost: 0, surcharge: 0, income_tax: 0, net_cash_flow: -25,
    cumulative_cash_flow: -125, estimated_payback_period: null, payback_period: null,
  },
  {
    year: 3, phase: '运营期', revenue: 200, residual_value: 20, inflow: 220,
    construction_investment: 0, principal_repayment: 10, interest: 5,
    operating_cost: 50, surcharge: 0, income_tax: 10, net_cash_flow: 145,
    cumulative_cash_flow: 20, estimated_payback_period: 0.8621, payback_period: 0.8621,
  },
]

const totalSchedule = [
  { ...capitalSchedule[0]!, construction_investment: 100, net_cash_flow: -100, cumulative_cash_flow: -100 },
  { ...capitalSchedule[1]!, construction_investment: 25, net_cash_flow: -25, cumulative_cash_flow: -125 },
  {
    ...capitalSchedule[2]!, principal_repayment: 0, interest: 0,
    net_cash_flow: 160, cumulative_cash_flow: 35, estimated_payback_period: 0.7813, payback_period: 0.7813,
  },
]

export const cashFlowResult: CashFlowResult = {
  table_type: 'cash_flow', unit: '万元', inputs: cashFlowInputs,
  capital: {
    title: '资本金现金流量表', unit: '万元',
    summary: {
      irr: 0.10, static_payback_period: 0.8621,
      inflow_total: 220, construction_investment_total: 125,
      principal_repayment_total: 10, interest_total: 5,
      operating_cost_total: 50, surcharge_total: 0, income_tax_total: 10,
      net_cash_flow_total: 20, residual_value: 20,
    },
    schedule: capitalSchedule,
  },
  total_investment: {
    title: '全投资现金流量表', unit: '万元',
    summary: {
      irr: 0.06, static_payback_period: 0.7813,
      inflow_total: 220, construction_investment_total: 125,
      principal_repayment_total: 0, interest_total: 0,
      operating_cost_total: 50, surcharge_total: 0, income_tax_total: 10,
      net_cash_flow_total: 35, residual_value: 20,
    },
    schedule: totalSchedule,
  },
}

export const economicCashFlowResult: CalculationResult = {
  tool_name: 'calculate_economic_scheme', scheme_id: 'scheme-1', step: 'cash_flow',
  loan_result: bankResult, cost_result: costResult,
  revenue_tax_result: revenueTaxResult,
  income_tax_result: incomeTaxResult,
  cash_flow_result: cashFlowResult,
}
