"""风电或光伏功率驱动的电加热制汽计算。"""

from iapws import IAPWS95


def calculate_steam_flow_from_renewable_power(
    renewable_power: float,
    renewable_conversion_efficiency: float,
    rated_electrical_power: float,
    electrical_efficiency: float,
    heat_exchange_efficiency: float,
    storage_efficiency: float,
    operating_hours: float,
    steam_supply_hours: float,
    steam_pressure: float,
    steam_temp: float,
    feedwater_pressure: float,
    feedwater_temp: float,
) -> dict[str, float]:
    """根据风电或光伏功率及转换效率，计算电加热器能够供给的蒸汽流量。"""
    available_electrical_power = renewable_power * renewable_conversion_efficiency
    electrical_power = min(available_electrical_power, rated_electrical_power)
    charging_power = electrical_power * electrical_efficiency
    heat_energy = charging_power * operating_hours
    supply_thermal_power = heat_energy / steam_supply_hours
    sgs_input_power = supply_thermal_power * storage_efficiency
    water_to_steam_power = sgs_input_power * heat_exchange_efficiency

    steam_state = IAPWS95(P=steam_pressure, T=steam_temp + 273.15)
    feedwater_state = IAPWS95(P=feedwater_pressure, T=feedwater_temp + 273.15)
    enthalpy_diff = steam_state.h - feedwater_state.h
    mass_flow = water_to_steam_power / enthalpy_diff

    return {
        "electrical_power": electrical_power,
        "charging_power": charging_power,
        "heat_energy": heat_energy,
        "sgs_input_power": sgs_input_power,
        "water_to_steam_power": water_to_steam_power,
        "electricity_consumption": electrical_power * operating_hours,
        "mass_flow": mass_flow,
    }
