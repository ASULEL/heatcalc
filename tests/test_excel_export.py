from io import BytesIO
from zipfile import ZipFile

import pytest

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from heatcalc.agent.economic_tool import calculate_economic_scheme
from heatcalc.backend.main import app
from heatcalc.export.excel_export import build_scheme_workbook
from heatcalc.finance import DEFAULT_LOAN_SCHEDULE_INPUTS


def scheme_results(*, loan_overrides=None, operating_years=25):
    loan = calculate_economic_scheme.invoke({"request": {
        "step": "loan", "scheme_id": "scheme-1", "inputs": {**DEFAULT_LOAN_SCHEDULE_INPUTS, **(loan_overrides or {})},
    }})
    cost = calculate_economic_scheme.invoke({"request": {
        "step": "cost", "scheme_id": "scheme-1", "loan_result": loan["loan_result"],
        "inputs": {
            "operating_years": 25, "depreciation_years": 15,
            "construction_credit_ratio": 0.10, "depreciable_ratio": 0.95,
            "insurance_rate": 0.0035, "insurance_divisor": 1.06, "tax_divisor": 1.13,
            "maintenance_ratio_periods": [
                {"start_year": 3, "end_year": 7, "ratio": 0.003},
                {"start_year": 8, "end_year": 12, "ratio": 0.005},
                {"start_year": 13, "end_year": 17, "ratio": 0.007},
                {"start_year": 18, "end_year": 22, "ratio": 0.009},
                {"start_year": 23, "end_year": 27, "ratio": 0.011},
            ],
            "total_electricity_by_year": [0] * 2 + [17651.8226] * 25 + [0] * 3,
            "water_cost_by_year": [0] * 30, "labor_cost_by_year": [0] * 30,
            "amortization_expense_by_year": [0] * 30,
            "working_capital_loan_interest_by_year": [0] * 30,
        },
    }})
    revenue = calculate_economic_scheme.invoke({"request": {
        "step": "revenue_tax", "scheme_id": "scheme-1",
        "loan_result": loan["loan_result"], "cost_result": cost["cost_result"],
        "inputs": {
            "operating_years": operating_years, "income_amount_basis": "tax_inclusive",
            "steam_vat_rate": 0.09, "carbon_vat_rate": 0.13, "output_vat_rate": 0.09,
            "input_vat_rate": 0.13, "construction_credit_ratio": 0.10, "surcharge_rate": 0.10,
            "steam_revenue_by_year": [0] * 2 + [20134.33652629279] * 25 + [0] * 3,
            "carbon_revenue_by_year": [0] * 30, "steam_volume_by_year": [None] * 30,
        },
    }})
    income = calculate_economic_scheme.invoke({"request": {
        "step": "income_tax", "scheme_id": "scheme-1",
        "loan_result": revenue["loan_result"], "cost_result": revenue["cost_result"],
        "revenue_tax_result": revenue["revenue_tax_result"],
        "inputs": {"income_tax_rate": 0.25},
    }})
    cash = calculate_economic_scheme.invoke({"request": {
        "step": "cash_flow", "scheme_id": "scheme-1",
        "loan_result": income["loan_result"], "cost_result": income["cost_result"],
        "revenue_tax_result": income["revenue_tax_result"],
        "income_tax_result": income["income_tax_result"],
        "inputs": {"equity_ratio": 0.30},
    }})
    return loan, cost, revenue, income, cash


def workbook():
    loan, cost, revenue, income, cash = scheme_results()
    content = build_scheme_workbook(
        '经济测算 1', loan['loan_result'], cost['cost_result'],
        revenue['revenue_tax_result'], income['income_tax_result'],
        cash['cash_flow_result'], '2026-10-30 12:00',
    )
    return load_workbook(BytesIO(content)), content


def test_export_contains_six_tables_and_notes():
    wb, _ = workbook()

    assert wb.sheetnames == [
        '借款利息计算', '成本计算', '收入及税金', '所得税计算',
        '资本金现金流量表', '全投资现金流量表', '测算说明',
    ]
    assert wb.calculation.fullCalcOnLoad is False
    assert wb['测算说明']['B2'].value == '经济测算 1'


def test_loan_and_cost_sheets_use_cross_sheet_formulas():
    wb, _ = workbook()
    loan = wb['借款利息计算']
    cost = wb['成本计算']

    assert loan['B3'].value == '=B2*H2'
    assert loan['C8'].value == '=B3*H3'
    assert loan['E8'].value == '=(B8+C8/2)*$B$4'
    assert loan['B10'].value == '=F9'
    assert loan['F10'].value == '=MAX(0,B10+C10-D10)'
    assert cost['O10'].value == '=O1*O3-O1*O2+O9'
    assert cost['C5'].value.startswith('=IF(AND($A5>$O$11')
    assert cost['H37'].value == '=$O$10-SUM(H5:INDEX(H5:H34,\'收入及税金\'!$O$11))'
    assert loan['B8'].number_format == '#,##0.0000'


def test_revenue_income_and_cash_flow_formulas():
    wb, _ = workbook()
    revenue = wb['收入及税金']
    income = wb['所得税计算']
    capital = wb['资本金现金流量表']
    total = wb['全投资现金流量表']

    assert revenue['C5'].value.startswith('=IF(AND($A5>$O$10')
    assert revenue['G6'].value == '=MIN(F6,MAX($O$9-SUM($G$5:G5),0))'
    assert income['G6'].value == '=MAX(G5+MAX(-E6,0)-H6,0)'
    assert income['H6'].value == '=MIN(MAX(E6,0),G5)'
    assert capital['E5'].value.startswith('=IF(A5>$P$5,"",IF(A5=1,\'借款利息计算\'!$B$2*$P$1*$P$2')
    assert capital['F5'].value == '=IF(A5>$P$5,"",\'借款利息计算\'!D8)'
    assert capital['K5'].value == '=IF(A5>$P$5,"",D5-SUM(E5:J5))'
    assert 'COUNT($N$5:N5)=0' in capital['M6'].value
    assert 'L6>=0,L5<0' in capital['N6'].value
    assert capital['B36'].value == '=IFERROR(IRR(K5:INDEX(K5:K34,$P$5)),"")'
    assert total['F5'].value == '=IF(A5>$P$5,"",0)'
    assert total['G5'].value == '=IF(A5>$P$5,"",0)'
    assert total['P1'].value == 1


def test_formula_results_are_available_before_opening_and_recalculating():
    formulas, content = workbook()
    values = load_workbook(BytesIO(content), data_only=True)
    assert ZipFile(BytesIO(content)).testzip() is None
    assert formulas.calculation.calcMode == 'auto'
    assert formulas.calculation.forceFullCalc is False
    loan = values['借款利息计算']
    assert [loan.cell(7, col).value for col in range(1, 7)] == [
        '年份', '年初借款余额', '当年新增借款', '当期还本', '当期利息', '年末借款余额',
    ]
    assert loan['B24'].value == pytest.approx(1474.5368858)
    assert loan['D24'].value == pytest.approx(1474.5368858)
    assert loan['F24'].value == 0
    assert loan['B25'].value == loan['D25'].value == loan['F25'].value == 0
    assert values['成本计算']['O10'].value == pytest.approx(26686.876812)
    assert values['资本金现金流量表']['K7'].value == pytest.approx(494.0963896)
    assert values['资本金现金流量表']['B36'].value == pytest.approx(0.07999117)
    assert values['全投资现金流量表']['B37'].value == pytest.approx(12.1178466)
    for name in ('资本金现金流量表', '全投资现金流量表'):
        sheet = values[name]
        assert sheet['M8'].value is not None
        assert sheet['P2'].value == 0.8
        assert sheet['P3'].value == 2
        assert sheet['C31'].value == pytest.approx(1334.3438406)
        assert sheet['C30'].value == 0
        for row in sheet.iter_rows(min_row=32, max_row=34, min_col=2, max_col=14):
            assert all(cell.value is None for cell in row)
    assert not [(s.title, c.coordinate) for s in values for row in s for c in row if c.data_type == 'e']


def test_export_endpoint_returns_downloadable_workbook():
    loan, cost, revenue, income, cash = scheme_results()
    payload = {
        'scheme_name': '经济测算 1',
        'loan_result': loan['loan_result'],
        'cost_result': cost['cost_result'],
        'revenue_tax_result': revenue['revenue_tax_result'],
        'income_tax_result': income['income_tax_result'],
        'cash_flow_result': cash['cash_flow_result'],
    }
    with TestClient(app) as client:
        response = client.post('/api/tools/calculate_economic_scheme/export', json=payload)

    assert response.status_code == 200
    assert response.headers['content-type'].startswith(
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    assert "filename*=UTF-8''" in response.headers['content-disposition']
    exported = load_workbook(BytesIO(response.content))
    assert '资本金现金流量表' in exported.sheetnames


def test_export_short_operation_uses_remaining_book_value_and_loan_drawdown_inputs():
    loan, cost, revenue, income, cash = scheme_results(
        loan_overrides={'first_drawdown_ratio': 0.65, 'second_drawdown_year': 3},
        operating_years=5,
    )
    # 导出按来源重新生成现金流，不能沿用旧快照中结束后的金额。
    cash['cash_flow_result']['capital']['schedule'][7]['net_cash_flow'] = 999999
    content = build_scheme_workbook(
        '短运营方案', loan['loan_result'], cost['cost_result'],
        revenue['revenue_tax_result'], income['income_tax_result'], cash['cash_flow_result'], '',
    )
    values = load_workbook(BytesIO(content), data_only=True)
    expected_residual = cost['cost_result']['summary']['cost_base'] - sum(
        row['depreciation_cost'] for row in cost['cost_result']['schedule'][:7]
    )
    assert values['成本计算']['H37'].value == pytest.approx(expected_residual)
    for name in ('资本金现金流量表', '全投资现金流量表'):
        sheet = values[name]
        assert sheet['P2'].value == 0.65
        assert sheet['P3'].value == 3
        assert sheet['P5'].value == 7
        assert sheet['C11'].value == pytest.approx(expected_residual)
        assert sheet['C10'].value == 0
        assert sheet['E6'].value == 0
        assert sheet['E7'].value > 0
        assert all(cell.value is None for row in sheet.iter_rows(
            min_row=12, max_row=34, min_col=2, max_col=14,
        ) for cell in row)
