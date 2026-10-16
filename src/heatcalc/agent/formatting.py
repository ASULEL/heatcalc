def format_result_for_display(data: dict) -> dict:
    """
    将核心库返回的SI单位计算结果，转换为工业场景常用单位展示格式

    :param data: calculate_cost_from_steam 返回的原始结果字典（单位：kW, kWh, 元）
    :return: 结构化的展示结果，每项包含 value 和 unit
    """
    return {
        'water_to_steam_power': {
            'value': round(data['water_to_steam_power'] / 1000, 5),
            'unit': 'MWt'
        },
        'sgs_input_power':{
            'value': round(data['sgs_input_power'] / 1000, 5),
            'unit': 'MWt'
        },
        'charging_power': {
            'value': round(data['charging_power'] / 1000, 5),
            'unit': 'MWt'
        },
        'electrical_power': {
            'value': round(data['electrical_power'] / 1000, 5),
            'unit': 'MWe'
        },
        'electricity_consumption': {
            'value': round(data['electricity_consumption'] / 1000, 5),
            'unit': 'MWhe'
        },
        'electricity_cost': {
            'value': round(data['electricity_cost'], 5),
            'unit': '元'
        }
    }
