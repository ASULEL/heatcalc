import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from heatcalc.agent.economic_tool import calculate_economic_scheme
from heatcalc.agent.formatting import format_result_for_display
from heatcalc.agent.parameter_specs import build_parameter_form
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
            "equipment_total_cost": 26400, "depreciation_years": 20,
            "maintenance_ratio_periods": [{"start_year": 3, "end_year": 30, "ratio": 0.003}],
            "total_electricity_by_year": [0] * 2 + [2390.4133] * 28,
            "water_cost_by_year": [0] * 30,
            "labor_cost_by_year": [0] * 2 + [216] * 28,
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
    assert result["loan_result"]["schedule"][1]["interest_expense"] == pytest.approx(751.19616)
    assert result["loan_result"]["schedule"][2]["interest_expense"] == pytest.approx(856.1000448)


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
    assert display["loan_result"]["summary"]["annual_principal"] == {"value": 1902.4445, "unit": "万元"}
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


def test_http_two_step_workflow(loan_request, cost_request):
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
    assert data["parameter_form"] == []
    result = data["calculation_results"][0]
    assert result["scheme_id"] == "scheme-1"
    assert result["step"] == "cost"
    assert result["cost_result"]["schedule"][2]["total_cost"] == pytest.approx(4840.591228516814)
    assert result["loan_result"] == loan_data["calculation_results"][0]["loan_result"]


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
    assert any('"interest_expense": 751.19616' in message.content for message in seen_messages)


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
    assert data["parameter_form"] == []
    assert data["calculation_results"][0]["cost_result"]["schedule"][2]["total_cost"] == pytest.approx(4840.591228516814)
