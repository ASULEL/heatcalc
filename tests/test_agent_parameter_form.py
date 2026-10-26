from heatcalc.agent.parameter_specs import build_parameter_form
from heatcalc.agent.tools import (
    calculate_heat_pump_cop,
    calculate_salt_mass,
    calculate_steam_flow_from_renewable_power,
)


def test_renewable_parameter_form_uses_chinese_labels_and_units():
    form = build_parameter_form(
        calculate_steam_flow_from_renewable_power,
        {"renewable_power": 8000},
    )

    assert form[0] == {
        "name": "renewable_power",
        "label": "风电或光伏功率",
        "unit": "kW",
        "group": "风光与电加热参数",
        "advanced": False,
        "value": 8000,
        "required": True,
    }


def test_salt_mass_form_uses_context_specific_power_label():
    form = build_parameter_form(calculate_salt_mass)

    assert form[0]["label"] == "充热端热功率"
    assert form[0]["unit"] == "kW"
    assert form[0]["group"] == "储热系统参数"


def test_heat_pump_cop_form_uses_excel_example_defaults():
    form = build_parameter_form(calculate_heat_pump_cop)
    fields = {field["name"]: field for field in form}

    assert fields["working_fluid"]["value"] == "air"
    assert fields["working_fluid"]["options"] == [
        {"value": "air", "label": "air（空气）"},
    ]
    assert fields["charging_power"]["value"] == 100
    assert fields["charging_power"]["unit"] == "MWt"
    assert fields["charging_power"]["toToolFactor"] == 1000
    assert fields["compressor_inlet_pressure"]["value"] == 2.7
    assert fields["compressor_inlet_pressure"]["unit"] == "MPa"
    assert fields["compressor_inlet_pressure"]["toToolFactor"] == 1000
    assert fields["expander_outlet_pressure"]["value"] == 2.95
    assert "compressor_mechanical_loss" not in fields or fields["compressor_mechanical_loss"]["value"] is None
