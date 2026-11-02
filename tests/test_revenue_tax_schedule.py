from copy import deepcopy

import pytest
from pydantic import ValidationError

from heatcalc.agent.revenue_tax_inputs import RevenueTaxInputs
from heatcalc.finance import DEFAULT_LOAN_SCHEDULE_INPUTS, calculate_cost_schedule, calculate_loan_schedule
from heatcalc.finance import calculate_revenue_tax_schedule


@pytest.fixture
def revenue_inputs():
    loan_inputs = {
        **DEFAULT_LOAN_SCHEDULE_INPUTS, "static_investment": 1000,
        "second_drawdown_year": 2, "repayment_years": 3, "schedule_years": 6,
    }
    loan = {"table_type": "loan", "inputs": loan_inputs, **calculate_loan_schedule(**loan_inputs)}
    cost_inputs = {
        "operating_years": 4, "depreciation_years": 15,
        "construction_credit_ratio": 0.10, "depreciable_ratio": 0.95,
        "insurance_rate": 0.0035, "insurance_divisor": 1.06, "tax_divisor": 1.13,
        "maintenance_ratio_periods": [{"start_year": 3, "end_year": 6, "ratio": 0.003}],
        "total_electricity_by_year": [0] * 6, "water_cost_by_year": [0] * 6,
        "labor_cost_by_year": [0] * 6, "amortization_expense_by_year": [0] * 6,
        "working_capital_loan_interest_by_year": [0] * 6,
    }
    cost = {"table_type": "cost", "inputs": cost_inputs, **calculate_cost_schedule(loan, **cost_inputs)}
    return {
        "loan_schedule": loan, "cost_schedule": cost,
        "operating_years": 3, "income_amount_basis": "tax_exclusive",
        "steam_revenue_by_year": [0, 0, 600, 600, 600, 600],
        "carbon_revenue_by_year": [0] * 6, "steam_volume_by_year": [None] * 6,
        "steam_vat_rate": 0.09, "carbon_vat_rate": 0.13, "output_vat_rate": 0.1,
        "input_vat_rate": 0.13, "construction_credit_ratio": 0.1, "surcharge_rate": 0.1,
    }


def test_credit_is_used_fully_then_partly_then_exhausted(revenue_inputs):
    result = calculate_revenue_tax_schedule(**revenue_inputs)
    rows = result["schedule"][2:5]
    assert [row["opening_construction_credit"] for row in rows] == pytest.approx([100, 40, 0])
    assert [row["construction_credit_used"] for row in rows] == pytest.approx([60, 40, 0])
    assert [row["construction_credit_balance"] for row in rows] == pytest.approx([40, 0, 0])
    assert [row["vat_paid"] for row in rows] == pytest.approx([0, 20, 60])
    assert [row["surcharge"] for row in rows] == pytest.approx([0, 2, 6])
    assert result["summary"]["construction_credit_used_total"] == 100
    assert result["summary"]["vat_paid_total"] == 80
    assert result["summary"]["surcharge_total"] == 8


def test_gross_income_is_removed_separately_then_sales_tax_uses_total(revenue_inputs):
    revenue_inputs.update({
        "income_amount_basis": "tax_inclusive", "construction_credit_ratio": 0,
        "steam_revenue_by_year": [0, 0, 1090, 1090, 1090, 0],
        "carbon_revenue_by_year": [0, 0, 113, 113, 113, 0], "output_vat_rate": 0.09,
    })
    revenue_inputs["cost_schedule"]["schedule"][2]["electricity_cost"] = 100
    row = calculate_revenue_tax_schedule(**revenue_inputs)["schedule"][2]
    assert row["steam_revenue_excluding_tax"] == pytest.approx(1000)
    assert row["carbon_revenue_excluding_tax"] == pytest.approx(100)
    assert row["revenue_excluding_tax"] == pytest.approx(1100)
    assert row["output_vat"] == pytest.approx(99)
    assert row["input_vat"] == pytest.approx(13)
    assert row["vat_paid"] == pytest.approx(86)
    assert row["surcharge"] == pytest.approx(8.6)


def test_all_tax_coefficients_can_be_changed(revenue_inputs):
    revenue_inputs.update({
        "income_amount_basis": "tax_inclusive", "construction_credit_ratio": 0.01,
        "steam_revenue_by_year": [0, 0, 1100, 0, 0, 0],
        "carbon_revenue_by_year": [0, 0, 120, 0, 0, 0],
        "steam_vat_rate": 0.1, "carbon_vat_rate": 0.2,
        "output_vat_rate": 0.12, "input_vat_rate": 0.2, "surcharge_rate": 0.05,
    })
    revenue_inputs["cost_schedule"]["schedule"][2]["electricity_cost"] = 100
    row = calculate_revenue_tax_schedule(**revenue_inputs)["schedule"][2]
    assert row["revenue_excluding_tax"] == pytest.approx(1100)
    assert row["output_vat"] == pytest.approx(132)
    assert row["input_vat"] == pytest.approx(20)
    assert row["construction_credit_used"] == pytest.approx(10)
    assert row["vat_paid"] == pytest.approx(102)
    assert row["surcharge"] == pytest.approx(5.1)


def test_net_income_is_not_divided_again_and_each_year_uses_its_electricity(revenue_inputs):
    revenue_inputs["cost_schedule"]["schedule"][3]["electricity_cost"] = 100
    revenue_inputs["carbon_revenue_by_year"][3] = 100
    rows = calculate_revenue_tax_schedule(**revenue_inputs)["schedule"]
    assert rows[2]["revenue_excluding_tax"] == 600
    assert rows[3]["revenue_excluding_tax"] == 700
    assert rows[2]["input_vat"] == 0
    assert rows[3]["input_vat"] == 13
    assert rows[3]["construction_credit_used"] == 40
    assert rows[3]["vat_paid"] == 17
    assert rows[4]["input_vat"] == 0


def test_excess_operating_input_tax_does_not_consume_construction_credit(revenue_inputs):
    revenue_inputs["cost_schedule"]["schedule"][2]["electricity_cost"] = 1000
    rows = calculate_revenue_tax_schedule(**revenue_inputs)["schedule"]
    assert rows[2]["vat_before_credit"] == 0
    assert rows[2]["construction_credit_used"] == 0
    assert rows[2]["construction_credit_balance"] == 100
    assert rows[2]["surcharge"] == 0
    assert rows[3]["vat_before_credit"] == 60
    assert rows[3]["construction_credit_balance"] == 40


@pytest.mark.parametrize("ratio,expected_used,expected_paid", [(0, 0, 100), (0.1, 100, 0)])
def test_zero_credit_and_exact_exhaustion(revenue_inputs, ratio, expected_used, expected_paid):
    revenue_inputs["construction_credit_ratio"] = ratio
    revenue_inputs["steam_revenue_by_year"][2] = 1000
    row = calculate_revenue_tax_schedule(**revenue_inputs)["schedule"][2]
    assert row["construction_credit_used"] == expected_used
    assert row["vat_paid"] == expected_paid
    assert row["construction_credit_balance"] == 0


def test_construction_and_post_operation_have_no_income_or_vat(revenue_inputs):
    result = calculate_revenue_tax_schedule(**revenue_inputs)
    for index in [0, 1, 5]:
        row = result["schedule"][index]
        assert row["revenue_excluding_tax"] == 0
        assert row["output_vat"] == row["input_vat"] == 0
        assert row["vat_paid"] == row["surcharge"] == 0
        assert row["steam_volume"] is None
    assert result["schedule"][5]["phase"] == "运营结束"
    assert result["summary"]["revenue_excluding_tax_total"] == 1800


def test_excel_reference_values_and_zero_tax_preserve_credit(revenue_inputs):
    revenue_inputs["loan_schedule"]["summary"]["static_investment"] = 30458.823529411766
    revenue_inputs.update({
        "income_amount_basis": "tax_inclusive", "output_vat_rate": 0.09,
        "steam_revenue_by_year": [0, 0] + [20134.33652629279] * 4,
    })
    for row in revenue_inputs["cost_schedule"]["schedule"][2:]:
        row["electricity_cost"] = 15621.081929126227
    result = calculate_revenue_tax_schedule(**revenue_inputs)
    row = result["schedule"][2]
    assert row["revenue_excluding_tax"] == pytest.approx(18471.868372745677)
    assert row["output_vat"] == pytest.approx(1662.468153547111)
    assert row["input_vat"] == pytest.approx(2030.7406507864096)
    assert row["vat_paid"] == row["construction_credit_used"] == row["surcharge"] == 0
    assert result["summary"]["final_construction_credit_balance"] == pytest.approx(3045.8823529411766)


def test_recalculation_restarts_credit_and_never_mutates_sources(revenue_inputs):
    revenue_inputs["steam_volume_by_year"][2] = 81.79117939457045
    revenue_inputs["steam_revenue_by_year"][2] = 600.123456789
    original = deepcopy(revenue_inputs)
    first = calculate_revenue_tax_schedule(**revenue_inputs)
    assert first == calculate_revenue_tax_schedule(**revenue_inputs)
    assert revenue_inputs == original
    assert first["schedule"][2]["revenue_excluding_tax"] == 600.123456789
    assert first["schedule"][2]["steam_volume"] == 81.79117939457045
    revenue_inputs["steam_revenue_by_year"][2] = 0
    changed = calculate_revenue_tax_schedule(**revenue_inputs)
    assert changed["schedule"][3]["opening_construction_credit"] == 100
    assert first["schedule"][3]["opening_construction_credit"] != 100


@pytest.mark.parametrize("field,value", [
    ("operating_years", 5), ("operating_years", 0),
    ("output_vat_rate", float("nan")), ("input_vat_rate", -0.1),
    ("surcharge_rate", 1.1), ("steam_revenue_by_year", [0]),
    ("carbon_revenue_by_year", [0, 0, -1, 0, 0, 0]),
])
def test_invalid_financial_inputs_are_rejected(revenue_inputs, field, value):
    revenue_inputs[field] = value
    with pytest.raises(ValueError):
        calculate_revenue_tax_schedule(**revenue_inputs)


def test_mismatched_source_calendar_and_invalid_electricity_are_rejected(revenue_inputs):
    revenue_inputs["cost_schedule"]["schedule"][2]["year"] = 4
    with pytest.raises(ValueError, match="年份"):
        calculate_revenue_tax_schedule(**revenue_inputs)
    revenue_inputs["cost_schedule"]["schedule"][2]["year"] = 3
    revenue_inputs["cost_schedule"]["schedule"][2]["electricity_cost"] = float("inf")
    with pytest.raises(ValueError, match="不含税电费"):
        calculate_revenue_tax_schedule(**revenue_inputs)


def test_input_model_requires_explicit_parameters_and_finite_rates(revenue_inputs):
    inputs = {name: revenue_inputs[name] for name in RevenueTaxInputs.model_fields}
    assert RevenueTaxInputs(**inputs).output_vat_rate == 0.1
    del inputs["output_vat_rate"]
    with pytest.raises(ValidationError):
        RevenueTaxInputs(**inputs)
    inputs["output_vat_rate"] = float("inf")
    with pytest.raises(ValidationError):
        RevenueTaxInputs(**inputs)
