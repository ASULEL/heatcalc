"""熔盐储量的公共计算。"""

from math import isfinite


def calculate_salt_mass(
    charging_power: float,
    storage_duration: float,
    salt_specific_heat: float,
    salt_temp_delta: float,
) -> float:
    """根据充热端热功率计算熔盐储量。

    :param charging_power: 充热端热功率 (kW)
    :param storage_duration: 按充热功率配置的储热容量时长 (h)
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_delta: 熔盐温差 (K)
    :return: 熔盐质量 (吨)
    """
    parameters = {
        "充热功率": charging_power,
        "储热时长": storage_duration,
        "熔盐比热容": salt_specific_heat,
        "熔盐温差": salt_temp_delta,
    }
    for name, value in parameters.items():
        if not isfinite(value):
            raise ValueError(f"{name}必须是有限数值")

    if charging_power < 0:
        raise ValueError("充热功率不能为负数")
    if storage_duration < 0:
        raise ValueError("储热时长不能为负数")
    if salt_specific_heat <= 0:
        raise ValueError("熔盐比热容必须大于零")
    if salt_temp_delta <= 0:
        raise ValueError("熔盐温差必须大于零")

    storage_energy_kj = charging_power * storage_duration * 3600
    energy_per_kg = salt_specific_heat * salt_temp_delta
    return float(storage_energy_kj / energy_per_kg / 1000)
