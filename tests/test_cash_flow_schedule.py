import pytest

from heatcalc.finance import (
    DEFAULT_LOAN_SCHEDULE_INPUTS, calculate_cash_flow_schedule, calculate_cost_schedule,
    calculate_income_tax_schedule, calculate_loan_schedule, calculate_revenue_tax_schedule,
)


def default_tables():
    loan = {
        "table_type": "loan", "inputs": dict(DEFAULT_LOAN_SCHEDULE_INPUTS),
        **calculate_loan_schedule(**DEFAULT_LOAN_SCHEDULE_INPUTS),
    }
    cost = calculate_cost_schedule(
        loan_schedule=loan, operating_years=25, depreciation_years=15,
        maintenance_ratio_periods=[
            {"start_year": 3, "end_year": 7, "ratio": 0.003},
            {"start_year": 8, "end_year": 12, "ratio": 0.005},
            {"start_year": 13, "end_year": 17, "ratio": 0.007},
            {"start_year": 18, "end_year": 22, "ratio": 0.009},
            {"start_year": 23, "end_year": 27, "ratio": 0.011},
        ],
        total_electricity_by_year=[0] * 2 + [17651.8226] * 25 + [0] * 3,
        water_cost_by_year=[0] * 30, labor_cost_by_year=[0] * 30,
        amortization_expense_by_year=[0] * 30, working_capital_loan_interest_by_year=[0] * 30,
        construction_credit_ratio=0.10, depreciable_ratio=0.95,
        insurance_rate=0.0035, insurance_divisor=1.06, tax_divisor=1.13,
    )
    revenue = calculate_revenue_tax_schedule(
        loan_schedule=loan, cost_schedule=cost, operating_years=25,
        income_amount_basis="tax_inclusive",
        steam_revenue_by_year=[0] * 2 + [20134.33652629279] * 25 + [0] * 3,
        carbon_revenue_by_year=[0] * 30, steam_volume_by_year=[None] * 30,
        steam_vat_rate=0.09, carbon_vat_rate=0.13, output_vat_rate=0.09,
        input_vat_rate=0.13, construction_credit_ratio=0.10, surcharge_rate=0.10,
    )
    income_tax = calculate_income_tax_schedule(cost, revenue, income_tax_rate=0.25)
    return loan, cost, revenue, income_tax


def default_cash_flow(equity_ratio=0.30):
    loan, cost, revenue, income_tax = default_tables()
    return calculate_cash_flow_schedule(
        loan_schedule=loan, cost_schedule=cost,
        revenue_tax_schedule=revenue, income_tax_schedule=income_tax,
        equity_ratio=equity_ratio,
    )


def test_capital_cash_flow_matches_excel():
    result = default_cash_flow()
    capital = result["capital"]
    rows = capital["schedule"]

    assert result["unit"] == "万元"
    assert rows[0]["construction_investment"] == pytest.approx(7310.11764)
    assert rows[1]["construction_investment"] == pytest.approx(1827.52941)
    assert rows[2]["principal_repayment"] == pytest.approx(1474.5368858)
    assert rows[2]["interest"] == pytest.approx(630.3645187)
    assert rows[2]["operating_cost"] == pytest.approx(15780.0491084)
    assert rows[2]["income_tax"] == pytest.approx(92.8214702)
    assert rows[2]["net_cash_flow"] == pytest.approx(494.0963896)
    assert rows[2]["cumulative_cash_flow"] == pytest.approx(-8643.5506604)
    assert rows[26]["residual_value"] == pytest.approx(1334.3438406)
    assert rows[26]["net_cash_flow"] == pytest.approx(3211.5080580)
    assert capital["summary"]["irr"] == pytest.approx(0.07999117)
    assert capital["summary"]["static_payback_period"] == pytest.approx(13.7751)
    assert capital["summary"]["residual_value"] == pytest.approx(1334.3438406)


def test_total_investment_cash_flow_has_no_debt_and_uses_full_investment():
    result = default_cash_flow()
    total = result["total_investment"]
    rows = total["schedule"]

    assert rows[0]["construction_investment"] == pytest.approx(24367.0588)
    assert rows[1]["construction_investment"] == pytest.approx(6091.7647)
    assert all(row["principal_repayment"] == 0 for row in rows[:27])
    assert all(row["interest"] == 0 for row in rows[:27])
    assert rows[2]["net_cash_flow"] == pytest.approx(2598.9977941)
    assert total["summary"]["irr"] == pytest.approx(0.05536966)
    assert total["summary"]["static_payback_period"] == pytest.approx(12.1178466)


def test_both_tables_use_the_same_columns():
    result = default_cash_flow()
    capital_row = result["capital"]["schedule"][2]
    total_row = result["total_investment"]["schedule"][2]

    assert capital_row.keys() == total_row.keys()


def test_equity_ratio_only_changes_capital_table():
    baseline = default_cash_flow()
    changed = default_cash_flow(equity_ratio=0.40)

    assert changed["capital"]["schedule"][0]["construction_investment"] == pytest.approx(
        baseline["capital"]["schedule"][0]["construction_investment"] * 4 / 3
    )
    assert changed["total_investment"]["schedule"] == baseline["total_investment"]["schedule"]


def test_residual_value_is_counted_once_in_the_last_operating_year():
    result = default_cash_flow()

    for table in (result["capital"], result["total_investment"]):
        years = [row["year"] for row in table["schedule"] if row["residual_value"]]
        assert years == [27]
        row = table["schedule"][26]
        assert row["inflow"] == pytest.approx(row["revenue"] + row["residual_value"])


def test_post_operation_rows_are_blank_and_excluded_from_totals():
    loan, cost, revenue, income = default_tables()
    for table in (loan, cost, revenue, income):
        for row in table['schedule'][27:]:
            for key in row:
                if key not in ('year', 'phase'):
                    row[key] = 999999
    result = calculate_cash_flow_schedule(loan, cost, revenue, income, 0.3)
    baseline = default_cash_flow()
    for name in ('capital', 'total_investment'):
        assert result[name]['summary'] == baseline[name]['summary']
        for row in result[name]['schedule'][27:]:
            assert row['phase'] == '运营结束'
            assert all(value is None for key, value in row.items() if key not in ('year', 'phase'))


def test_annual_estimate_matches_excel_and_stops_after_first_recovery():
    result = default_cash_flow()
    for name in ('capital', 'total_investment'):
        table = result[name]
        rows = table['schedule']
        actual = table['summary']['static_payback_period']
        recovered = False
        for row in rows:
            if row['payback_period'] is not None:
                assert row['estimated_payback_period'] == pytest.approx(actual)
            if row['phase'] == '运营期' and row['net_cash_flow'] > 0 and not recovered:
                expected = row['year'] - 2 - row['cumulative_cash_flow'] / row['net_cash_flow']
                assert row['estimated_payback_period'] == pytest.approx(expected)
            else:
                assert row['estimated_payback_period'] is None
            recovered |= row['payback_period'] is not None


def test_no_recovery_with_zero_or_negative_cash_flow_has_no_payback():
    loan, cost, revenue, income = default_tables()
    for row in revenue['schedule']:
        row['revenue_excluding_tax'] = 0
    result = calculate_cash_flow_schedule(loan, cost, revenue, income, 0.3)
    for name in ('capital', 'total_investment'):
        table = result[name]
        assert table['summary']['static_payback_period'] is None
        assert all(row['estimated_payback_period'] is None for row in table['schedule'])


def test_short_operation_recovers_undepreciated_value_at_its_own_end():
    loan, cost, revenue, income = default_tables()
    for row in revenue['schedule'][7:]:
        row['phase'] = '运营结束'
    result = calculate_cash_flow_schedule(loan, cost, revenue, income, 0.3)
    expected = cost['summary']['cost_base'] - sum(row['depreciation_cost'] for row in cost['schedule'][:7])
    for name in ('capital', 'total_investment'):
        rows = result[name]['schedule']
        assert result[name]['summary']['residual_value'] == pytest.approx(expected)
        assert rows[6]['residual_value'] == pytest.approx(expected)
        assert rows[6]['net_cash_flow'] == pytest.approx(
            rows[6]['revenue'] + expected - rows[6]['principal_repayment'] - rows[6]['interest']
            - rows[6]['operating_cost'] - rows[6]['surcharge'] - rows[6]['income_tax']
        )
        assert rows[7]['net_cash_flow'] is None
