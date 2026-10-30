import type { CalculationResult, LoanCalculationResult } from '../src/types.ts'

export const bankResult: LoanCalculationResult = {
  table_type: 'loan',
  inputs: {
    static_investment: 34320, loan_ratio: 0.8, investment_interest_rate: 0.03,
    construction_interest_rate: 0.03, construction_years: 2, first_drawdown_ratio: 0.8,
    second_drawdown_year: 2, repayment_years: 15, schedule_years: 30,
  },
  unit: '万元',
  summary: {
    static_investment: 34320, total_investment_with_interest: 35400.66816,
    loan_amount: 27456, construction_interest_total: 1080.66816,
    annual_principal: 1902.444544, total_interest: 7929.4685184,
  },
  schedule: [
    {
      year: 1, phase: '建设期', beginning_balance: 0, new_borrowing: 21964.8,
      principal_repayment: 0, interest_expense: 329.472, capitalized_interest: 329.472,
      cash_interest: 0, ending_balance: 22294.272,
    },
    {
      year: 2, phase: '建设期', beginning_balance: 22294.272, new_borrowing: 5491.2,
      principal_repayment: 0, interest_expense: 751.19616, capitalized_interest: 751.19616,
      cash_interest: 0, ending_balance: 28536.66816,
    },
    {
      year: 3, phase: '运营期', beginning_balance: 28536.66816, new_borrowing: 0,
      principal_repayment: 1902.444544, interest_expense: 856.1000448, capitalized_interest: 0,
      cash_interest: 856.1000448, ending_balance: 26634.223616,
    },
  ],
}

export const economicLoanResult: CalculationResult = {
  tool_name: 'calculate_economic_scheme', scheme_id: 'scheme-1', step: 'loan', loan_result: bankResult,
}
