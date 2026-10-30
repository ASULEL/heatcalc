from copy import deepcopy

import pytest

from heatcalc.agent.parameter_specs import build_economic_form
from heatcalc.finance import DEFAULT_LOAN_SCHEDULE_INPUTS, calculate_loan_schedule
from heatcalc.finance import calculate_cost_schedule


@pytest.fixture
def cost_inputs():
    loan_inputs = {**DEFAULT_LOAN_SCHEDULE_INPUTS, "second_drawdown_year": 2}
    loan = {
        "table_type": "loan",
        "inputs": loan_inputs,
        **calculate_loan_schedule(**loan_inputs),
    }
    return {
        "loan_schedule": loan,
        "equipment_total_cost": 26400.0,
        "depreciation_years": 20,
        "maintenance_ratio_periods": [
            {"start_year": 3, "end_year": 7, "ratio": 0.003},
            {"start_year": 8, "end_year": 12, "ratio": 0.005},
            {"start_year": 13, "end_year": 17, "ratio": 0.007},
            {"start_year": 18, "end_year": 22, "ratio": 0.009},
            {"start_year": 23, "end_year": 27, "ratio": 0.011},
            {"start_year": 28, "end_year": 30, "ratio": 0.013},
        ],
        "total_electricity_by_year": [0.0] * 2 + [2390.4133] * 28,
        "water_cost_by_year": [0.0] * 30,
        "labor_cost_by_year": [0.0] * 2 + [216.0] * 28,
        "amortization_expense_by_year": [0.0] * 30,
        "working_capital_loan_interest_by_year": [0.0] * 30,
    }


def test_first_operating_year_matches_image(cost_inputs):
    result = calculate_cost_schedule(**cost_inputs)
    row = result["schedule"][2]

    assert result["unit"] == "万元"
    assert row["electricity_cost"] == pytest.approx(2115.41)
    assert row["water_cost"] == 0
    assert row["labor_cost"] == 216
    assert row["insurance_cost"] == pytest.approx(85.8)
    assert row["maintenance_cost"] == pytest.approx(79.2)
    assert row["depreciation_cost"] == pytest.approx(1488.0811837168144)
    assert row["long_term_loan_interest"] == pytest.approx(856.1000448)
    assert row["total_cost"] == pytest.approx(4840.591228516814)


def test_cost_years_and_interest_reference_loan_rows(cost_inputs):
    rows = calculate_cost_schedule(**cost_inputs)["schedule"]
    loans = cost_inputs["loan_schedule"]["schedule"]

    assert [row["year"] for row in rows] == [row["year"] for row in loans]
    for row, loan in zip(rows, loans):
        if loan["phase"] == "建设期":
            assert row["total_cost"] == 0
            assert row["long_term_loan_interest"] == 0
        else:
            assert row["long_term_loan_interest"] == loan["interest_expense"]
    assert rows[16]["financial_cost"] == pytest.approx(57.07333632)
    assert rows[17]["financial_cost"] == 0


@pytest.mark.parametrize("year, ratio, amount", [
    (7, 0.003, 79.2), (8, 0.005, 132),
    (12, 0.005, 132), (13, 0.007, 184.8),
    (22, 0.009, 237.6), (23, 0.011, 290.4),
    (27, 0.011, 290.4), (28, 0.013, 343.2),
])
def test_maintenance_period_boundaries(cost_inputs, year, ratio, amount):
    row = calculate_cost_schedule(**cost_inputs)["schedule"][year - 1]

    assert row["maintenance_ratio"] == ratio
    assert row["maintenance_cost"] == pytest.approx(amount)


def test_depreciation_ends_after_input_years(cost_inputs):
    rows = calculate_cost_schedule(**cost_inputs)["schedule"]
    assert rows[21]["depreciation_cost"] == pytest.approx(1488.0811837168144)
    assert rows[22]["depreciation_cost"] == 0

    cost_inputs["depreciation_years"] = 15
    rows = calculate_cost_schedule(**cost_inputs)["schedule"]
    assert rows[16]["depreciation_cost"] == pytest.approx(1984.1082449557525)
    assert rows[17]["depreciation_cost"] == 0


def test_annual_inputs_and_placeholder_fields_are_included(cost_inputs):
    cost_inputs["total_electricity_by_year"][3] = 1130.0
    cost_inputs["water_cost_by_year"][3] = 12.5
    cost_inputs["labor_cost_by_year"][3] = 220.0
    cost_inputs["amortization_expense_by_year"][3] = 30.25
    cost_inputs["working_capital_loan_interest_by_year"][3] = 8.75
    result = calculate_cost_schedule(**cost_inputs)
    row = result["schedule"][3]

    assert row["electricity_cost"] == pytest.approx(1000)
    assert row["operating_cost"] == pytest.approx(1397.5)
    assert row["amortization_expense"] == 30.25
    assert row["working_capital_loan_interest"] == 8.75
    assert row["depreciation_amortization"] == pytest.approx(row["depreciation_cost"] + 30.25)
    assert row["financial_cost"] == pytest.approx(row["long_term_loan_interest"] + 8.75)
    assert row["total_cost"] == pytest.approx(
        row["operating_cost"] + row["depreciation_amortization"] + row["financial_cost"]
    )
    assert result["summary"]["total_cost"] == pytest.approx(sum(
        item["total_cost"] for item in result["schedule"]
    ))


def test_variable_construction_and_table_years(cost_inputs):
    loan_inputs = {
        **DEFAULT_LOAN_SCHEDULE_INPUTS, "construction_years": 4,
        "second_drawdown_year": 2, "schedule_years": 12,
    }
    cost_inputs["loan_schedule"] = calculate_loan_schedule(**loan_inputs)
    cost_inputs["depreciation_years"] = 3
    cost_inputs["maintenance_ratio_periods"] = [{"start_year": 5, "end_year": 12, "ratio": 0.01}]
    result = calculate_cost_schedule(**cost_inputs)

    assert len(result["schedule"]) == 12
    assert all(row["total_cost"] == 0 for row in result["schedule"][:4])
    assert result["schedule"][4]["depreciation_cost"] > 0
    assert result["schedule"][6]["depreciation_cost"] > 0
    assert result["schedule"][7]["depreciation_cost"] == 0


def test_cost_calculation_preserves_source_and_precision(cost_inputs):
    original = deepcopy(cost_inputs)
    result = calculate_cost_schedule(**cost_inputs)
    assert cost_inputs == original
    assert result["schedule"][2]["depreciation_cost"] != 1488.08


def test_cost_step_form_exposes_inputs_and_annual_examples():
    fields = {field["name"]: field for field in build_economic_form("cost")}

    assert len(fields) == 8
    assert "loan_schedule" not in fields
    assert fields["depreciation_years"]["value"] == 20
    assert fields["maintenance_ratio_periods"]["periodDefaults"] == {
        "years": 5, "first_ratio": 0.003, "ratio_step": 0.002,
    }
    assert fields["total_electricity_by_year"]["annualDefault"] == 2390.4133
    assert fields["water_cost_by_year"]["annualDefault"] == 0
    assert fields["amortization_expense_by_year"]["annualDefault"] == 0
    assert all(field["toolName"] == "calculate_economic_scheme" for field in fields.values())
    assert all(field["schemeStep"] == "cost" for field in fields.values())
