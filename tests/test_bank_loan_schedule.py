import pytest

from heatcalc.finance import DEFAULT_LOAN_SCHEDULE_INPUTS, calculate_loan_schedule


def test_default_inputs_match_excel_loan_schedule():
    result = calculate_loan_schedule(**DEFAULT_LOAN_SCHEDULE_INPUTS)  # 默认场景计算结果

    assert result["unit"] == "万元"
    assert len(result["schedule"]) == 30
    assert result["summary"]["loan_amount"] == pytest.approx(21321.17645)
    assert result["summary"]["construction_interest_total"] == pytest.approx(
        796.87683770
    )
    assert result["summary"]["operating_initial_balance"] == pytest.approx(
        22118.05328770
    )
    assert result["summary"]["annual_principal"] == pytest.approx(1474.53688585)
    assert result["summary"]["total_interest"] == pytest.approx(5839.79298730)
    assert result["summary"]["total_investment_with_interest"] == pytest.approx(
        31255.70033770
    )
    assert result["summary"]["repayment_end_year"] == 17
    assert result["summary"]["final_ending_balance"] == pytest.approx(0)


def test_schedule_rows_match_excel_formulas():
    rows = calculate_loan_schedule(**DEFAULT_LOAN_SCHEDULE_INPUTS)["schedule"]  # 逐年还本付息明细

    first_year = rows[0]  # 第1年明细
    second_year = rows[1]  # 第2年明细
    third_year = rows[2]  # 第3年明细
    final_year = rows[16]  # 还本结束年份明细

    assert first_year["new_borrowing"] == pytest.approx(17056.94116)
    assert first_year["interest_expense"] == pytest.approx(243.06141153)
    assert first_year["ending_balance"] == pytest.approx(17300.00257153)

    assert second_year["new_borrowing"] == pytest.approx(4264.23529)
    assert second_year["interest_expense"] == pytest.approx(553.81542617)
    assert second_year["ending_balance"] == pytest.approx(22118.05328770)

    assert third_year["new_borrowing"] == 0
    assert third_year["principal_repayment"] == pytest.approx(1474.53688585)
    assert third_year["interest_expense"] == pytest.approx(630.36451870)
    assert third_year["ending_balance"] == pytest.approx(20643.51640185)

    for row in rows[2:17]:
        assert row["principal_repayment"] == pytest.approx(1474.53688585)

    assert final_year["principal_repayment"] == pytest.approx(1474.53688585)
    assert final_year["ending_balance"] == pytest.approx(0)


def test_years_after_repayment_are_zero():
    rows = calculate_loan_schedule(**DEFAULT_LOAN_SCHEDULE_INPUTS)["schedule"]  # 逐年还本付息明细

    for row in rows[17:]:  # 还本结束后的年度明细
        assert row["principal_repayment"] == 0
        assert row["interest_expense"] == 0
        assert row["ending_balance"] == 0


def test_operating_year_second_drawdown_example(capsys):
    """调用示例：建设期两年，运营期第一年提款剩余 0.2。"""
    inputs = {  # 测试输入参数
        "static_investment": 34320.0,              # 静态投资，万元
        "loan_ratio": 0.80,                        # 贷款比例
        "investment_interest_rate": 0.03,          # 投资贷款利率
        "construction_interest_rate": 0.03,        # 建设期贷款利率
        "construction_years": 2,                   # 建设期年数
        "first_drawdown_ratio": 0.80,              # 第1年提款比例
        "second_drawdown_year": 3,                 # 第3年提款剩余贷款
        "repayment_years": 15,                     # 还本期
        "schedule_years": 30,                      # 表内列示年数
    }

    result = calculate_loan_schedule(**inputs)  # 测试场景计算结果

    # 运行 pytest -s 时可以看到调用结果，默认打印前两年建设期和汇总。
    print("建设期明细：", result["schedule"][:2])
    print("汇总结果：", result["summary"])

    rows = result["schedule"]  # 逐年还本付息明细
    assert rows[0]["new_borrowing"] == pytest.approx(21964.8)
    assert rows[1]["new_borrowing"] == pytest.approx(0)
    assert rows[2]["new_borrowing"] == pytest.approx(5491.2)
    assert rows[0]["interest_expense"] == pytest.approx(329.472)
    assert rows[1]["interest_expense"] == pytest.approx(668.82816)
    assert rows[2]["interest_expense"] == pytest.approx(853.6290048)
    assert result["summary"]["operating_initial_balance"] == pytest.approx(
        28454.30016
    )
    assert rows[2]["principal_repayment"] == pytest.approx(1896.953344)
    assert rows[2]["ending_balance"] == pytest.approx(26557.346816)
    assert result["summary"]["repayment_end_year"] == 17


def test_construction_interest_uses_every_construction_year():
    inputs = {  # 测试输入参数
        **DEFAULT_LOAN_SCHEDULE_INPUTS,
        "construction_years": 3,
        "second_drawdown_year": 4,
    }
    rows = calculate_loan_schedule(**inputs)["schedule"]  # 逐年还本付息明细

    assert rows[0]["new_borrowing"] == pytest.approx(17056.94116)
    assert rows[1]["new_borrowing"] == pytest.approx(0)
    assert rows[2]["new_borrowing"] == pytest.approx(0)
    assert rows[3]["new_borrowing"] == pytest.approx(4264.23529)
    assert rows[2]["interest_expense"] == pytest.approx(
        (rows[2]["beginning_balance"] + rows[2]["new_borrowing"] / 2) * 0.0285
    )
