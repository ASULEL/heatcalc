DISPLAY_DECIMALS = 2


def format_result_for_display(data: dict, decimals: int = DISPLAY_DECIMALS) -> dict:
    """
    将计算结果中实际包含的字段转换为工业场景常用单位展示格式。

    :param data: 正算、反算或储盐工具返回的结果 (kW、kWh、元、kg/s、吨及无量纲 COP)
    :param decimals: 展示结果保留的小数位数，默认两位
    :return: 结构化的展示结果，每项包含 value 和 unit
    """
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
            "value": round(data["electricity_cost"], decimals),
            "unit": "元",
        }

    # 反算结果包含流量时，转换为 t/h
    if "mass_flow" in data:
        display_result["mass_flow"] = {
            "value": round(data["mass_flow"] * 3.6, decimals),
            "unit": "t/h",
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
