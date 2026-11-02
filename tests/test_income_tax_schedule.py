import pytest

from heatcalc.finance import (
    DEFAULT_LOAN_SCHEDULE_INPUTS, calculate_cost_schedule, calculate_income_tax_schedule,
    calculate_loan_schedule, calculate_revenue_tax_schedule,
)


def default_tables():
    loan = calculate_loan_schedule(**DEFAULT_LOAN_SCHEDULE_INPUTS)
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
    return cost, revenue


def synthetic_tables(profits: list[float]):
    cost_rows = []
    revenue_rows = []
    for year, profit in enumerate(profits, start=1):
        cost_rows.append({"year": year, "phase": "运营期", "total_cost": max(-profit, 0.0)})
        revenue_rows.append({
            "year": year, "phase": "运营期",
            "revenue_excluding_tax": max(profit, 0.0), "surcharge": 0.0,
        })
    return {"schedule": cost_rows}, {"schedule": revenue_rows}


def test_default_case_matches_excel():
    cost, revenue = default_tables()
    result = calculate_income_tax_schedule(cost, revenue, income_tax_rate=0.25)
    rows = result["schedule"]

    assert result["unit"] == "万元"
    assert rows[2]["revenue"] == pytest.approx(18471.8683727)
    assert rows[2]["total_cost"] == pytest.approx(18100.5824919)
    assert rows[2]["total_profit"] == pytest.approx(371.2858808)
    assert rows[2]["income_tax"] == pytest.approx(92.8214702)
    assert rows[2]["net_profit"] == pytest.approx(278.4644106)
    assert rows[17]["income_tax"] == pytest.approx(637.5297627)
    assert result["summary"]["total_profit"] == pytest.approx(34538.3620)
    assert result["summary"]["income_tax_total"] == pytest.approx(8634.5905)
    assert result["summary"]["net_profit_total"] == pytest.approx(25903.7715)
    assert result["summary"]["final_carryforward_loss"] == 0


def test_losses_are_carried_forward_and_offset_before_tax():
    cost, revenue = synthetic_tables([-100, -50, 120, 100])
    rows = calculate_income_tax_schedule(cost, revenue, income_tax_rate=0.25)["schedule"]

    assert [row["current_year_loss"] for row in rows] == [-100, -50, 0, 0]
    assert [row["carryforward_loss"] for row in rows] == [100, 150, 30, 0]
    assert [row["loss_offset"] for row in rows] == [0, 0, 120, 30]
    assert [row["taxable_income"] for row in rows] == [0, 0, 0, 70]
    assert [row["income_tax"] for row in rows] == [0, 0, 0, 17.5]
    assert [row["net_profit"] for row in rows] == [-100, -50, 120, 82.5]


def test_losses_carry_forward_without_year_limit():
    cost, revenue = synthetic_tables([-100, 0, 0, 0, 0, 0, 100])
    rows = calculate_income_tax_schedule(cost, revenue, income_tax_rate=0.25)["schedule"]

    assert rows[3]["carryforward_loss"] == 100
    assert rows[6]["loss_offset"] == 100
    assert rows[6]["income_tax"] == 0
    assert rows[6]["net_profit"] == 100


def test_summary_totals_follow_annual_rows():
    cost, revenue = synthetic_tables([-100, 200])
    result = calculate_income_tax_schedule(cost, revenue, income_tax_rate=0.25)

    assert result["summary"] == pytest.approx({
        "revenue_total": 200,
        "surcharge_total": 0,
        "total_cost_total": 100,
        "total_profit": 100,
        "income_tax_total": 25,
        "net_profit_total": 75,
        "final_carryforward_loss": 0,
    })
