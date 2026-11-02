DISPLAY_DECIMALS = 2
MONEY_DECIMALS = 4  # 金额展示精度，原始计算结果不舍入


def format_result_for_display(data: dict, decimals: int = DISPLAY_DECIMALS) -> dict:
    """
    将计算结果中实际包含的字段转换为工业场景常用单位展示格式。

    :param data: 正算、反算或储盐工具返回的结果 (kW、kWh、元、kg/s、吨及无量纲 COP)
    :param decimals: 非金额结果的展示小数位数，默认两位；金额统一四位
    :return: 结构化的展示结果，每项包含 value 和 unit
    """
    if "loan_result" in data:
        return {
            name: format_result_for_display(data[name], decimals)
            for name in (
                "loan_result", "cost_result", "revenue_tax_result",
                "income_tax_result", "cash_flow_result",
            ) if name in data
        }

    if "capital" in data and "total_investment" in data:
        # 现金流量表同时包含资本金和全投资两张表。
        return {
            "unit": data["unit"],
            "capital": format_result_for_display(data["capital"], decimals),
            "total_investment": format_result_for_display(data["total_investment"], decimals),
        }

    if "schedule" in data:
        summary = {}
        for name, value in data["summary"].items():
            if name == "irr":
                summary[name] = {
                    "value": None if value is None else round(value * 100, 2),
                    "unit": "%",
                }
            elif name == "static_payback_period":
                summary[name] = {
                    "value": None if value is None else round(value, 2),
                    "unit": "年",
                }
            else:
                summary[name] = {
                    "value": value if name == "repayment_end_year" else round(value, MONEY_DECIMALS),
                    "unit": "年" if name == "repayment_end_year" else data["unit"],
                }
        return {"unit": data["unit"], "summary": summary}

    # 功率和电量从 kW、kWh 转换为 MW、MWh。
    scaled_units = {
        "water_to_steam_power": "MWt",
        "sgs_input_power": "MWt",
        "charging_power": "MWt",
        "electrical_power": "MWe",
        "heat_energy": "MWht",
        "electricity_consumption": "MWhe",
    }
    display_result = {}
    for field, unit in scaled_units.items():
        if field in data:
            display_result[field] = {
                "value": round(data[field] / 1000, decimals),
                "unit": unit,
            }

    if "electricity_cost" in data:
        display_result["electricity_cost"] = {
            "value": round(data["electricity_cost"], MONEY_DECIMALS),
            "unit": "元",
        }

    # 反算结果包含流量时，转换为 t/h
    if "mass_flow" in data:
        display_result["mass_flow"] = {
            "value": round(data["mass_flow"] * 3.6, decimals),
            "unit": "t/h",
        }

    if "cycle_mass_flow" in data:
        display_result["cycle_mass_flow"] = {
            "value": round(data["cycle_mass_flow"], decimals),
            "unit": "kg/s",
        }

    # 储盐算法已经返回吨，仅作舍入。
    if "salt_mass" in data:
        display_result["salt_mass"] = {
            "value": round(data["salt_mass"], decimals),
            "unit": "t",
        }

    if "cop" in data:
        display_result["cop"] = {
            "value": round(data["cop"], decimals),
            "unit": "无量纲",
        }

    return display_result
