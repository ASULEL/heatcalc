from copy import deepcopy

import pytest

from heatcalc.agent.parameter_specs import build_economic_form
from heatcalc.finance import DEFAULT_LOAN_SCHEDULE_INPUTS, calculate_loan_schedule
from heatcalc.finance import calculate_cost_schedule


EXCEL_ELECTRICITY = 17651.8226  # 当前 Excel 经济性表的年度总成本，万元
EXCEL_MAINTENANCE_PERIODS = [  # 运营第1年起每5年一段的维修费比例
    {"start_year": 3, "end_year": 7, "ratio": 0.003},
    {"start_year": 8, "end_year": 12, "ratio": 0.005},
    {"start_year": 13, "end_year": 17, "ratio": 0.007},
    {"start_year": 18, "end_year": 22, "ratio": 0.009},
    {"start_year": 23, "end_year": 27, "ratio": 0.011},
]


@pytest.fixture
def cost_inputs():
    loan_inputs = dict(DEFAULT_LOAN_SCHEDULE_INPUTS)
    loan = {
        "table_type": "loan",
        "inputs": loan_inputs,
        **calculate_loan_schedule(**loan_inputs),
    }
    return {
        "loan_schedule": loan,
        "operating_years": 25,
        "depreciation_years": 15,
        "maintenance_ratio_periods": deepcopy(EXCEL_MAINTENANCE_PERIODS),
        "total_electricity_by_year": [0.0] * 2 + [EXCEL_ELECTRICITY] * 25 + [0.0] * 3,
        "water_cost_by_year": [0.0] * 30,
        "labor_cost_by_year": [0.0] * 30,
        "amortization_expense_by_year": [0.0] * 30,
        "working_capital_loan_interest_by_year": [0.0] * 30,
        "construction_credit_ratio": 0.10,
        "depreciable_ratio": 0.95,
        "insurance_rate": 0.0035,
        "insurance_divisor": 1.06,
        "tax_divisor": 1.13,
    }


def test_first_operating_year_matches_excel(cost_inputs):
    result = calculate_cost_schedule(**cost_inputs)
    row = result["schedule"][2]

    assert result["unit"] == "万元"
    assert result["summary"]["cost_base"] == pytest.approx(26686.8768127)
    assert row["electricity_cost"] == pytest.approx(15621.0819469)
    assert row["water_cost"] == 0
    assert row["labor_cost"] == 0
    assert row["insurance_cost"] == pytest.approx(88.11704608)
    assert row["maintenance_cost"] == pytest.approx(70.85011543)
    assert row["depreciation_cost"] == pytest.approx(1690.16886480)
    assert row["long_term_loan_interest"] == pytest.approx(630.36451870)
    assert row["total_cost"] == pytest.approx(18100.5824919)


def test_depreciation_ends_after_fifteen_years_and_year_18_cost_matches_excel(cost_inputs):
    rows = calculate_cost_schedule(**cost_inputs)["schedule"]

    assert rows[16]["depreciation_cost"] == pytest.approx(1690.16886480)
    assert rows[17]["depreciation_cost"] == 0
    assert rows[17]["total_cost"] == pytest.approx(15921.7493393)


def test_cost_years_follow_loan_rows_and_stop_after_operating_years(cost_inputs):
    rows = calculate_cost_schedule(**cost_inputs)["schedule"]
    loans = cost_inputs["loan_schedule"]["schedule"]

    assert [row["year"] for row in rows] == [row["year"] for row in loans]
    for row, loan in zip(rows, loans):
        if loan["phase"] == "建设期":
            assert row["total_cost"] == 0
            assert row["long_term_loan_interest"] == 0
        elif row["year"] <= 27:
            assert row["long_term_loan_interest"] == loan["interest_expense"]
        else:
            assert row["total_cost"] == 0
    assert rows[27]["total_cost"] == 0


@pytest.mark.parametrize("year, ratio, amount", [
    (7, 0.003, 70.85011543), (8, 0.005, 118.08352583),
    (12, 0.005, 118.08352583), (13, 0.007, 165.31693617),
    (22, 0.009, 212.55034630), (23, 0.011, 259.78375683),
    (27, 0.011, 259.78375683),
])
def test_maintenance_period_boundaries(cost_inputs, year, ratio, amount):
    row = calculate_cost_schedule(**cost_inputs)["schedule"][year - 1]

    assert row["maintenance_ratio"] == ratio
    assert row["maintenance_cost"] == pytest.approx(amount)


def test_uncovered_maintenance_years_use_zero_ratio(cost_inputs):
    cost_inputs["operating_years"] = 28
    cost_inputs["total_electricity_by_year"][27] = EXCEL_ELECTRICITY
    cost_inputs["total_electricity_by_year"][28] = EXCEL_ELECTRICITY
    rows = calculate_cost_schedule(**cost_inputs)["schedule"]

    assert rows[27]["maintenance_ratio"] == 0
    assert rows[27]["maintenance_cost"] == 0
    assert rows[27]["electricity_cost"] > 0


def test_depreciation_uses_input_years(cost_inputs):
    cost_inputs["depreciation_years"] = 20
    rows = calculate_cost_schedule(**cost_inputs)["schedule"]
    assert rows[21]["depreciation_cost"] == pytest.approx(26686.8768127 * 0.95 / 20)
    assert rows[22]["depreciation_cost"] == 0


def test_cost_coefficients_are_inputs(cost_inputs):
    baseline = calculate_cost_schedule(**deepcopy(cost_inputs))["schedule"][2]
    cost_inputs["insurance_rate"] = 0.007
    cost_inputs["tax_divisor"] = 1.0
    row = calculate_cost_schedule(**cost_inputs)["schedule"][2]

    assert row["insurance_cost"] == pytest.approx(baseline["insurance_cost"] * 2)
    assert row["maintenance_cost"] == pytest.approx(
        cost_inputs["maintenance_ratio_periods"][0]["ratio"] * 26686.8768127
    )
    assert row["electricity_cost"] == pytest.approx(EXCEL_ELECTRICITY)


def test_annual_inputs_and_placeholder_fields_are_included(cost_inputs):
    cost_inputs["total_electricity_by_year"][3] = 1130.0
    cost_inputs["water_cost_by_year"][3] = 12.5
    cost_inputs["labor_cost_by_year"][3] = 220.0
    cost_inputs["amortization_expense_by_year"][3] = 30.25
    cost_inputs["working_capital_loan_interest_by_year"][3] = 8.75
    result = calculate_cost_schedule(**cost_inputs)
    row = result["schedule"][3]

    assert row["electricity_cost"] == pytest.approx(1000)
    assert row["operating_cost"] == pytest.approx(
        1000 + 12.5 + 220 + row["insurance_cost"] + row["maintenance_cost"]
    )
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
        **DEFAULT_LOAN_SCHEDULE_INPUTS, "construction_years": 4, "schedule_years": 12,
    }
    cost_inputs["loan_schedule"] = calculate_loan_schedule(**loan_inputs)
    cost_inputs["operating_years"] = 8
    cost_inputs["depreciation_years"] = 3
    cost_inputs["maintenance_ratio_periods"] = [{"start_year": 5, "end_year": 12, "ratio": 0.01}]
    for name in (
        "total_electricity_by_year", "water_cost_by_year", "labor_cost_by_year",
        "amortization_expense_by_year", "working_capital_loan_interest_by_year",
    ):
        cost_inputs[name] = [0.0] * 12
    result = calculate_cost_schedule(**cost_inputs)

    assert len(result["schedule"]) == 12
    assert all(row["total_cost"] == 0 for row in result["schedule"][:4])
    assert result["schedule"][4]["depreciation_cost"] > 0
    assert result["schedule"][6]["depreciation_cost"] > 0
    assert result["schedule"][7]["depreciation_cost"] == 0


@pytest.mark.parametrize("change, message", [
    ({"operating_years": 0}, "运营年数"),
    ({"operating_years": 29}, "运营年数"),
    ({"depreciation_years": 0}, "折旧年限"),
    ({"total_electricity_by_year": [0.0] * 29}, "年度列表"),
    ({"tax_divisor": 0}, "含税换算系数"),
    ({"construction_credit_ratio": 1.5}, "建设期抵扣比例"),
    ({"maintenance_ratio_periods": [{"start_year": 8, "end_year": 7, "ratio": 0.003}]}, "开始年份"),
])
def test_invalid_cost_inputs_are_rejected(cost_inputs, change, message):
    cost_inputs.update(change)
    with pytest.raises(ValueError, match=message):
        calculate_cost_schedule(**cost_inputs)


def test_cost_calculation_preserves_source_and_precision(cost_inputs):
    original = deepcopy(cost_inputs)
    result = calculate_cost_schedule(**cost_inputs)
    assert cost_inputs == original
    assert result["schedule"][2]["depreciation_cost"] != 1690.17


def test_cost_step_form_exposes_excel_defaults():
    fields = {field["name"]: field for field in build_economic_form("cost")}

    assert len(fields) == 13
    assert "equipment_total_cost" not in fields
    assert "loan_schedule" not in fields
    assert fields["operating_years"]["value"] == 25
    assert fields["depreciation_years"]["value"] == 15
    assert fields["construction_credit_ratio"]["value"] == 10
    assert fields["construction_credit_ratio"]["unit"] == "%"
    assert fields["construction_credit_ratio"]["toToolFactor"] == 0.01
    assert fields["depreciable_ratio"]["value"] == 95
    assert fields["insurance_rate"]["value"] == 0.35
    assert fields["insurance_divisor"]["value"] == 1.06
    assert fields["tax_divisor"]["value"] == 1.13
    assert fields["maintenance_ratio_periods"]["periodDefaults"] == {
        "years": 5, "first_ratio": 0.003, "ratio_step": 0.002,
    }
    assert fields["total_electricity_by_year"]["annualDefault"] == 17651.8226
    assert fields["water_cost_by_year"]["annualDefault"] == 0
    assert fields["labor_cost_by_year"]["annualDefault"] == 0
    assert fields["amortization_expense_by_year"]["annualDefault"] == 0
    assert all(field["toolName"] == "calculate_economic_scheme" for field in fields.values())
    assert all(field["schemeStep"] == "cost" for field in fields.values())
