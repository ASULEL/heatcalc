import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from heatcalc.agent.economic_tool import calculate_economic_scheme
from heatcalc.agent.formatting import format_result_for_display
from heatcalc.agent.parameter_specs import build_parameter_form, build_economic_form
from heatcalc.agent.tool import ALL_TOOLS
from heatcalc.backend.main import app
from heatcalc.finance import DEFAULT_LOAN_SCHEDULE_INPUTS


@pytest.fixture
def loan_request():
    return {"request": {
        "step": "loan", "scheme_id": "scheme-1",
        "inputs": {**DEFAULT_LOAN_SCHEDULE_INPUTS, "second_drawdown_year": 2},
    }}


@pytest.fixture
def cost_request(loan_request):
    loan = calculate_economic_scheme.invoke(loan_request)["loan_result"]
    return {"request": {
        "step": "cost", "scheme_id": "scheme-1", "loan_result": loan,
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
            "water_cost_by_year": [0] * 30,
            "labor_cost_by_year": [0] * 30,
            "amortization_expense_by_year": [0] * 30,
            "working_capital_loan_interest_by_year": [0] * 30,
        },
    }}


@pytest.fixture
def agent_core(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:1/v1")
    from heatcalc.agent import agent_core
    return agent_core


def test_only_economic_tool_is_registered_for_financial_calculations(loan_request):
    names = [tool.name for tool in ALL_TOOLS]
    assert names.count("calculate_economic_scheme") == 1
    assert "calculate_bank_loan_schedule" not in names
    assert "calculate_cost_schedule_tool" not in names
    assert len(set(names)) == len(names)
    result = calculate_economic_scheme.invoke(loan_request)
    assert result["scheme_id"] == "scheme-1"
    assert result["step"] == "loan"
    assert len(result["loan_result"]["schedule"]) == 30
    assert result["loan_result"]["schedule"][1]["interest_expense"] == pytest.approx(553.81542617)
    assert result["loan_result"]["schedule"][2]["interest_expense"] == pytest.approx(630.36451870)


def test_cost_step_reuses_exact_loan_result_without_recalculation(cost_request, monkeypatch):
    from heatcalc.finance import economic_calculation
    original = deepcopy(cost_request)
    # 修改已保存的当年利息，验证成本读取该来源，而不是重新计算或换用其他方案。
    cost_request["request"]["loan_result"]["schedule"][2]["interest_expense"] = 123.456789
    monkeypatch.setattr(economic_calculation, "calculate_loan_schedule", lambda **_: pytest.fail("不应重新计算借款"))
    result = calculate_economic_scheme.invoke(cost_request)
    assert result["scheme_id"] == "scheme-1"
    assert result["loan_result"] == cost_request["request"]["loan_result"]
    assert result["cost_result"]["schedule"][2]["long_term_loan_interest"] == 123.456789
    assert result["cost_result"]["inputs"] == original["request"]["inputs"]
    assert cost_request["request"]["loan_result"]["schedule"][2]["interest_expense"] == 123.456789


def test_display_preserves_original_nested_data(loan_request):
    raw = calculate_economic_scheme.invoke(loan_request)
    original = deepcopy(raw)
    display = format_result_for_display(raw)
    assert display["loan_result"]["summary"]["annual_principal"] == {"value": 1474.5369, "unit": "万元"}
    assert display["loan_result"]["summary"]["repayment_end_year"] == {"value": 17, "unit": "年"}
    assert raw == original


def test_loan_form_uses_its_own_input_definition():
    fields = {field["name"]: field for field in build_parameter_form(
        calculate_economic_scheme, {"static_investment": 31151},
    )}
    assert len(fields) == 9
    assert fields["static_investment"]["value"] == 31151
    assert fields["static_investment"]["isDefault"] is False
    assert fields["second_drawdown_year"]["value"] == 2
    assert all(field["toolName"] == "calculate_economic_scheme" for field in fields.values())
    assert all(field["schemeStep"] == "loan" for field in fields.values())
    assert all(field["required"] for field in fields.values())


def test_http_five_step_workflow(loan_request, cost_request):
    with TestClient(app) as client:
        start = client.get("/api/tools/calculate_economic_scheme/parameters").json()
        loan_response = client.post("/api/tools/calculate_economic_scheme", json=loan_request)
        loan_data = loan_response.json()
        cost_request["request"]["loan_result"] = loan_data["calculation_results"][0]["loan_result"]
        cost_response = client.post("/api/tools/calculate_economic_scheme", json=cost_request)

    assert start["parameter_form"][0]["schemeStep"] == "loan"
    assert loan_response.status_code == 200
    assert loan_data["parameter_form"][0]["schemeStep"] == "cost"
    assert loan_data["calculation_results"][0]["loan_result"]["inputs"] == loan_request["request"]["inputs"]
    assert cost_response.status_code == 200
    data = cost_response.json()
    assert data["parameter_form"][0]["schemeStep"] == "revenue_tax"
    result = data["calculation_results"][0]
    assert result["scheme_id"] == "scheme-1"
    assert result["step"] == "cost"
    assert result["cost_result"]["schedule"][2]["total_cost"] == pytest.approx(18100.5824919)
    assert result["loan_result"] == loan_data["calculation_results"][0]["loan_result"]
    with TestClient(app) as client:
        tax_response = client.post("/api/tools/calculate_economic_scheme", json={"request": {
            "step": "revenue_tax", "scheme_id": "scheme-1", "loan_result": result["loan_result"],
            "cost_result": result["cost_result"], "inputs": revenue_tax_parameters(),
        }})
    assert tax_response.status_code == 200
    tax_data = tax_response.json()
    assert tax_data["parameter_form"][0]["schemeStep"] == "income_tax"
    tax_result = tax_data["calculation_results"][0]
    assert tax_result["scheme_id"] == "scheme-1"
    assert tax_result["step"] == "revenue_tax"
    assert tax_result["cost_result"] == result["cost_result"]
    assert tax_result["revenue_tax_result"]["schedule"][2]["input_vat"] == pytest.approx(17651.8226 / 1.13 * 0.13)
    assert tax_result["revenue_tax_result"]["schedule"][27]["phase"] == "运营结束"
    with TestClient(app) as client:
        income_tax_response = client.post("/api/tools/calculate_economic_scheme", json={"request": {
            "step": "income_tax", "scheme_id": "scheme-1",
            "loan_result": tax_result["loan_result"], "cost_result": tax_result["cost_result"],
            "revenue_tax_result": tax_result["revenue_tax_result"],
            "inputs": income_tax_parameters(),
        }})
    assert income_tax_response.status_code == 200
    income_data = income_tax_response.json()
    assert income_data["parameter_form"][0]["schemeStep"] == "cash_flow"
    income_result = income_data["calculation_results"][0]
    assert income_result["step"] == "income_tax"
    assert income_result["income_tax_result"]["schedule"][2]["income_tax"] == pytest.approx(92.8214702)
    with TestClient(app) as client:
        cash_response = client.post("/api/tools/calculate_economic_scheme", json={"request": {
            "step": "cash_flow", "scheme_id": "scheme-1",
            "loan_result": income_result["loan_result"], "cost_result": income_result["cost_result"],
            "revenue_tax_result": income_result["revenue_tax_result"],
            "income_tax_result": income_result["income_tax_result"],
            "inputs": cash_flow_parameters(),
        }})
    assert cash_response.status_code == 200
    cash_data = cash_response.json()
    assert cash_data["parameter_form"] == []
    cash_result = cash_data["calculation_results"][0]
    assert cash_result["step"] == "cash_flow"
    assert cash_result["cash_flow_result"]["capital"]["summary"]["irr"] == pytest.approx(0.07999117)
    assert cash_result["cash_flow_result"]["total_investment"]["summary"]["irr"] == pytest.approx(0.05536966)


def test_cost_step_requires_existing_loan_source(cost_request):
    del cost_request["request"]["loan_result"]
    with TestClient(app) as client:
        response = client.post("/api/tools/calculate_economic_scheme", json=cost_request)
    assert response.status_code == 422
    assert "loan_result" in str(response.json())


def test_new_tool_calls_create_distinct_schemes(loan_request):
    del loan_request["request"]["scheme_id"]
    first = calculate_economic_scheme.invoke(loan_request)
    second = calculate_economic_scheme.invoke(loan_request)
    assert first["scheme_id"] != second["scheme_id"]


def test_agent_returns_next_step_and_raw_result(agent_core, monkeypatch, loan_request):
    replies = iter([
        AIMessage(content="", tool_calls=[{
            "name": "calculate_economic_scheme", "args": loan_request, "id": "loan-1",
        }]),
        AIMessage(content="请继续填写成本参数。"),
    ])
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: next(replies)))
    _, messages, form, results = agent_core.chat("开始经济测算", [])
    assert form[0]["schemeStep"] == "cost"
    assert results[0]["tool_name"] == "calculate_economic_scheme"
    assert results[0]["scheme_id"] == "scheme-1"
    tool_message = next(message for message in messages if isinstance(message, ToolMessage))
    assert json.loads(tool_message.content)["raw_result"]["loan_result"] == results[0]["loan_result"]


def test_chat_can_start_scheme_from_parameter_request(agent_core, monkeypatch):
    replies = iter([
        AIMessage(content="", tool_calls=[{
            "name": "request_parameter_form", "args": {"tool_name": "calculate_economic_scheme"}, "id": "form-1",
        }]),
        AIMessage(content="请先填写借款参数。"),
    ])
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: next(replies)))
    with TestClient(app) as client:
        data = client.post("/api/chat", json={"message": "我要生成成本表"}).json()
    assert data["parameter_form"][0]["schemeStep"] == "loan"
    assert data["calculation_results"] == []


def test_chat_references_saved_scheme_without_recalculation(agent_core, monkeypatch, loan_request):
    saved = [{"tool_name": "calculate_economic_scheme", **calculate_economic_scheme.invoke(loan_request)}]
    seen_messages = []

    def reply(messages):
        seen_messages.extend(messages)
        return AIMessage(content="可以引用该方案的当年利息列。")

    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=reply))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "取当年利息列", "calculation_results": saved})
    assert response.status_code == 200
    assert response.json()["calculation_results"] == []
    assert any('"interest_expense": 553.81542617' in message.content for message in seen_messages)


def test_agent_cost_step_returns_structured_scheme(agent_core, monkeypatch, cost_request):
    replies = iter([
        AIMessage(content="", tool_calls=[{
            "name": "calculate_economic_scheme", "args": cost_request, "id": "cost-1",
        }]),
        AIMessage(content="经济测算完成。"),
    ])
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: next(replies)))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "完成经济测算", "parameter_values": cost_request})
    data = response.json()
    assert response.status_code == 200
    assert data["parameter_form"][0]["schemeStep"] == "revenue_tax"
    assert data["calculation_results"][0]["cost_result"]["schedule"][2]["total_cost"] == pytest.approx(18100.5824919)


def revenue_tax_parameters():
    return {
        "operating_years": 25, "income_amount_basis": "tax_inclusive",
        "steam_vat_rate": 0.09, "carbon_vat_rate": 0.13, "output_vat_rate": 0.09,
        "input_vat_rate": 0.13, "construction_credit_ratio": 0.1, "surcharge_rate": 0.1,
        "steam_revenue_by_year": [0, 0] + [20134.33652629279] * 28,
        "carbon_revenue_by_year": [0] * 30, "steam_volume_by_year": [None] * 30,
    }


def test_tax_step_reuses_sources_and_display_keeps_original_precision(cost_request, monkeypatch):
    from heatcalc.finance import economic_calculation
    saved = calculate_economic_scheme.invoke(cost_request)
    saved["cost_result"]["schedule"][3]["electricity_cost"] = 123.456789
    request = {"request": {
        "step": "revenue_tax", "scheme_id": "scheme-1", "loan_result": saved["loan_result"],
        "cost_result": saved["cost_result"], "inputs": revenue_tax_parameters(),
    }}
    original = deepcopy(request)
    monkeypatch.setattr(economic_calculation, "calculate_cost_schedule", lambda **_: pytest.fail("不应重算成本"))
    monkeypatch.setattr(economic_calculation, "calculate_loan_schedule", lambda **_: pytest.fail("不应重算借款"))
    result = calculate_economic_scheme.invoke(request)
    assert result["cost_result"] == saved["cost_result"]
    assert result["revenue_tax_result"]["schedule"][3]["input_vat"] == pytest.approx(123.456789 * 0.13)
    assert "revenue_tax_result" in format_result_for_display(result)
    assert request == original


def test_tax_source_and_calendar_errors_are_reported(cost_request):
    saved = calculate_economic_scheme.invoke(cost_request)
    request = {"request": {
        "step": "revenue_tax", "scheme_id": "scheme-1", "loan_result": saved["loan_result"],
        "inputs": revenue_tax_parameters(),
    }}
    with TestClient(app) as client:
        assert client.post("/api/tools/calculate_economic_scheme", json=request).status_code == 422
        request["request"]["cost_result"] = saved["cost_result"]
        request["request"]["cost_result"]["schedule"][2]["year"] = 4
        response = client.post("/api/tools/calculate_economic_scheme", json=request)
    assert response.status_code == 422
    assert "年份" in response.json()["detail"]


def test_revenue_form_exposes_income_basis_and_percent_conversion():
    fields = {field["name"]: field for field in build_economic_form("revenue_tax", {"output_vat_rate": 0.06})}
    assert fields["income_amount_basis"]["value"] == "tax_inclusive"
    assert fields["output_vat_rate"]["value"] == 6
    assert fields["output_vat_rate"]["unit"] == "%"
    assert fields["output_vat_rate"]["toToolFactor"] == 0.01
    assert fields["steam_volume_by_year"]["annualDefault"] is None
    assert all(field["schemeStep"] == "revenue_tax" for field in fields.values())


def income_tax_parameters():
    return {"income_tax_rate": 0.25}


def cash_flow_parameters():
    return {"equity_ratio": 0.30}


def test_agent_tax_step_returns_next_step(agent_core, monkeypatch, cost_request):
    saved = calculate_economic_scheme.invoke(cost_request)
    request = {"request": {
        "step": "revenue_tax", "scheme_id": "scheme-1", "loan_result": saved["loan_result"],
        "cost_result": saved["cost_result"], "inputs": revenue_tax_parameters(),
    }}
    replies = iter([
        AIMessage(content="", tool_calls=[{"name": "calculate_economic_scheme", "args": request, "id": "tax-1"}]),
        AIMessage(content="已生成收入及税金表。"),
    ])
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: next(replies)))
    _, _, form, results = agent_core.chat("生成收入及税金表", [])
    assert form[0]["schemeStep"] == "income_tax"
    assert results[0]["revenue_tax_result"]["table_type"] == "revenue_tax"


@pytest.mark.parametrize("message", [
    "将静态投资改成32000", "把静态投资改为 32,000 万元。",
    "请帮我将静态投资修改为32000\n，",
])
def test_static_investment_change_uses_saved_inputs_without_model(
    agent_core, monkeypatch, loan_request, message,
):
    saved = calculate_economic_scheme.invoke(loan_request)
    original = deepcopy(saved)
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: pytest.fail("明确改参不应请求模型")))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": message, "calculation_results": [saved]})
    assert response.status_code == 200
    data = response.json()
    result = data["calculation_results"][0]
    assert result["scheme_id"] == saved["scheme_id"]
    assert result["loan_result"]["inputs"] == {**saved["loan_result"]["inputs"], "static_investment": 32000}
    assert result["loan_result"]["summary"]["loan_amount"] == pytest.approx(32000 * 0.7)
    assert data["parameter_form"][0]["schemeStep"] == "cost"
    assert "32000.0000万元" in data["response"]
    assert saved == original


def test_investment_change_recalculates_existing_cost_and_taxes(agent_core, monkeypatch, cost_request):
    cost = calculate_economic_scheme.invoke(cost_request)
    saved = calculate_economic_scheme.invoke({"request": {
        "step": "revenue_tax", "scheme_id": cost["scheme_id"],
        "loan_result": cost["loan_result"], "cost_result": cost["cost_result"],
        "inputs": revenue_tax_parameters(),
    }})
    original = deepcopy(saved)
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: pytest.fail("不应请求模型")))
    # 兼容原界面发来的同一方案多个历史步骤，只取最新版本。
    _, _, form, results = agent_core.chat("将静态投资改成32000", [], calculation_results=[cost, saved])
    assert [result["step"] for result in results] == ["loan", "cost", "revenue_tax"]
    revised = results[-1]
    assert revised["scheme_id"] == saved["scheme_id"]
    assert revised["cost_result"]["inputs"] == original["cost_result"]["inputs"]
    assert revised["revenue_tax_result"]["inputs"] == original["revenue_tax_result"]["inputs"]
    loan_row = revised["loan_result"]["schedule"][2]
    cost_row = revised["cost_result"]["schedule"][2]
    assert cost_row["long_term_loan_interest"] == loan_row["interest_expense"]
    assert cost_row["insurance_cost"] == pytest.approx(
        revised["cost_result"]["summary"]["cost_base"] * 0.0035 / 1.06
    )
    assert cost_row["depreciation_cost"] != original["cost_result"]["schedule"][2]["depreciation_cost"]
    assert revised["revenue_tax_result"]["summary"]["initial_construction_credit"] == pytest.approx(3200)
    assert saved == original
    assert form[0]["schemeStep"] == "income_tax"


def test_loan_rate_change_converts_percent_without_changing_other_inputs(agent_core, monkeypatch, loan_request):
    saved = calculate_economic_scheme.invoke(loan_request)
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: pytest.fail("不应请求模型")))
    _, _, _, results = agent_core.chat("贷款比例改成75%", [], calculation_results=[saved])
    assert results[0]["loan_result"]["inputs"] == {**saved["loan_result"]["inputs"], "loan_ratio": 0.75}


def test_calendar_change_restarts_cost_entry_instead_of_reusing_old_years(agent_core, monkeypatch, cost_request):
    saved = calculate_economic_scheme.invoke(cost_request)
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: pytest.fail("不应请求模型")))
    _, _, form, results = agent_core.chat("建设期年数改成3年", [], calculation_results=[saved])
    assert len(results) == 1
    assert results[0]["loan_result"]["schedule"][2]["phase"] == "建设期"
    assert "cost_result" not in results[0]
    assert form[0]["schemeStep"] == "cost"


def test_multiple_schemes_require_a_target_and_only_recalculate_that_scheme(agent_core, monkeypatch, loan_request):
    first = calculate_economic_scheme.invoke(loan_request)
    second = {**deepcopy(first), "scheme_id": "scheme-2"}
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: pytest.fail("不应请求模型")))
    reply, _, _, results = agent_core.chat("静态投资改成32000", [], calculation_results=[first, second])
    assert "请指定编号" in reply
    assert results == []
    _, _, _, results = agent_core.chat("将经济测算2的静态投资改成32000", [], calculation_results=[first, second])
    assert results[0]["scheme_id"] == "scheme-2"
    assert first["loan_result"]["inputs"]["static_investment"] == 30458.8235


def test_revision_uses_displayed_scheme_name_even_when_another_scheme_has_no_result(agent_core, monkeypatch, loan_request):
    saved = {**calculate_economic_scheme.invoke(loan_request), "scheme_name": "经济测算 2"}
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: pytest.fail("不应请求模型")))
    _, _, _, results = agent_core.chat("将经济测算2的静态投资改成32000", [], calculation_results=[saved])
    assert results[0]["scheme_id"] == saved["scheme_id"]
    with TestClient(app) as client:
        response = client.post("/api/chat", json={
            "message": "将经济测算1的静态投资改成32000", "calculation_results": [saved],
        })
    assert response.status_code == 422


@pytest.mark.parametrize("message", [
    "如果将静态投资改成30458.8235会怎样？",
    "解释一下将静态投资改成30458.8235有什么影响",
    "不要将静态投资改成30458.8235",
])
def test_questions_and_negations_do_not_trigger_recalculation(message, loan_request):
    from heatcalc.agent.economic_revision import revise_loan_from_message
    saved = calculate_economic_scheme.invoke(loan_request)
    assert revise_loan_from_message(message, [saved]) is None


def test_wrong_revision_units_return_a_clear_error(agent_core, monkeypatch, loan_request):
    saved = calculate_economic_scheme.invoke(loan_request)
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: pytest.fail("不应请求模型")))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "静态投资改成30年", "calculation_results": [saved]})
    assert response.status_code == 422
    assert "单位应为万元" in response.json()["detail"]


def test_model_timeout_returns_http_error_instead_of_waiting_indefinitely(agent_core, monkeypatch):
    import httpx
    from openai import APITimeoutError

    def timeout(_):
        raise APITimeoutError(request=httpx.Request("POST", "https://example.com/chat/completions"))

    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=timeout))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "解释借款计算原理"})
    assert response.status_code == 504
    assert response.json()["detail"] == "模型响应超时，请重试。"


def test_economic_tool_result_returns_without_another_model_call(agent_core, monkeypatch, loan_request):
    def request_loan(_):
        return AIMessage(content="", tool_calls=[{
            "name": "calculate_economic_scheme", "args": loan_request, "id": "loan-1",
        }])

    calls = []

    def invoke(messages):
        assert not calls, "已算出表格后不应再次请求模型输出相同表格"
        calls.append(messages)
        return request_loan(messages)

    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=invoke))
    reply, _, form, results = agent_core.chat("生成借款表", [])
    assert "已生成借款还本付息表" in reply
    assert form[0]["schemeStep"] == "cost"
    assert results[0]["step"] == "loan"


def test_income_tax_form_exposes_rate():
    fields = {field["name"]: field for field in build_economic_form("income_tax")}

    assert len(fields) == 1
    assert fields["income_tax_rate"]["value"] == 25
    assert fields["income_tax_rate"]["unit"] == "%"
    assert fields["income_tax_rate"]["toToolFactor"] == 0.01
    assert fields["income_tax_rate"]["schemeStep"] == "income_tax"


def test_agent_income_tax_step_returns_next_step(agent_core, monkeypatch, cost_request):
    cost = calculate_economic_scheme.invoke(cost_request)
    revenue = calculate_economic_scheme.invoke({"request": {
        "step": "revenue_tax", "scheme_id": cost["scheme_id"],
        "loan_result": cost["loan_result"], "cost_result": cost["cost_result"],
        "inputs": revenue_tax_parameters(),
    }})
    request = {"request": {
        "step": "income_tax", "scheme_id": cost["scheme_id"],
        "loan_result": revenue["loan_result"], "cost_result": revenue["cost_result"],
        "revenue_tax_result": revenue["revenue_tax_result"], "inputs": income_tax_parameters(),
    }}
    replies = iter([
        AIMessage(content="", tool_calls=[{"name": "calculate_economic_scheme", "args": request, "id": "income-1"}]),
        AIMessage(content="已生成所得税表。"),
    ])
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: next(replies)))
    _, _, form, results = agent_core.chat("生成所得税表", [])
    assert form[0]["schemeStep"] == "cash_flow"
    assert results[0]["income_tax_result"]["table_type"] == "income_tax"
    assert "income_tax_result" in format_result_for_display(results[0])


def test_agent_cash_flow_step_finishes_workflow(agent_core, monkeypatch, cost_request):
    cost = calculate_economic_scheme.invoke(cost_request)
    revenue = calculate_economic_scheme.invoke({"request": {
        "step": "revenue_tax", "scheme_id": cost["scheme_id"],
        "loan_result": cost["loan_result"], "cost_result": cost["cost_result"],
        "inputs": revenue_tax_parameters(),
    }})
    income = calculate_economic_scheme.invoke({"request": {
        "step": "income_tax", "scheme_id": cost["scheme_id"],
        "loan_result": revenue["loan_result"], "cost_result": revenue["cost_result"],
        "revenue_tax_result": revenue["revenue_tax_result"], "inputs": income_tax_parameters(),
    }})
    request = {"request": {
        "step": "cash_flow", "scheme_id": cost["scheme_id"],
        "loan_result": income["loan_result"], "cost_result": income["cost_result"],
        "revenue_tax_result": income["revenue_tax_result"],
        "income_tax_result": income["income_tax_result"], "inputs": cash_flow_parameters(),
    }}
    replies = iter([
        AIMessage(content="", tool_calls=[{"name": "calculate_economic_scheme", "args": request, "id": "cash-1"}]),
        AIMessage(content="经济测算完成。"),
    ])
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: next(replies)))
    _, _, form, results = agent_core.chat("生成现金流量表", [])
    assert form == []
    assert results[0]["cash_flow_result"]["table_type"] == "cash_flow"
    display = format_result_for_display(results[0])
    assert display["cash_flow_result"]["capital"]["summary"]["irr"] == {"value": 8.0, "unit": "%"}
    assert display["cash_flow_result"]["total_investment"]["summary"]["irr"] == {"value": 5.54, "unit": "%"}


def test_investment_change_recalculates_income_tax_and_cash_flow(agent_core, monkeypatch, cost_request):
    cost = calculate_economic_scheme.invoke(cost_request)
    revenue = calculate_economic_scheme.invoke({"request": {
        "step": "revenue_tax", "scheme_id": cost["scheme_id"],
        "loan_result": cost["loan_result"], "cost_result": cost["cost_result"],
        "inputs": revenue_tax_parameters(),
    }})
    income = calculate_economic_scheme.invoke({"request": {
        "step": "income_tax", "scheme_id": cost["scheme_id"],
        "loan_result": revenue["loan_result"], "cost_result": revenue["cost_result"],
        "revenue_tax_result": revenue["revenue_tax_result"], "inputs": income_tax_parameters(),
    }})
    cash = calculate_economic_scheme.invoke({"request": {
        "step": "cash_flow", "scheme_id": cost["scheme_id"],
        "loan_result": income["loan_result"], "cost_result": income["cost_result"],
        "revenue_tax_result": income["revenue_tax_result"],
        "income_tax_result": income["income_tax_result"], "inputs": cash_flow_parameters(),
    }})
    original = deepcopy(cash)
    monkeypatch.setattr(agent_core, "llm_with_tools", SimpleNamespace(invoke=lambda _: pytest.fail("不应请求模型")))
    _, _, form, results = agent_core.chat("将静态投资改成32000", [], calculation_results=[cash])
    assert [result["step"] for result in results] == [
        "loan", "cost", "revenue_tax", "income_tax", "cash_flow",
    ]
    assert results[-1]["income_tax_result"]["inputs"] == original["income_tax_result"]["inputs"]
    assert results[-1]["income_tax_result"]["schedule"][2]["income_tax"] != original["income_tax_result"]["schedule"][2]["income_tax"]
    assert results[-1]["cash_flow_result"]["inputs"] == original["cash_flow_result"]["inputs"]
    assert results[-1]["cash_flow_result"]["capital"]["summary"]["irr"] != original["cash_flow_result"]["capital"]["summary"]["irr"]
    assert form == []
    assert cash == original
