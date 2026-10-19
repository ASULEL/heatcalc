from abc import ABC, abstractmethod
from math import isfinite

from iapws import IAPWS95

from heatcalc import salt_storage


class HeatSourceStrategy(ABC):
    """规定热源的正反算接口，并提供共用的蒸汽和储热计算。"""

    def __init__(
        self,
        heat_exchange_efficiency: float,
        storage_efficiency: float,
        salt_specific_heat: float,
        salt_temp_delta: float,
    ) -> None:
        """
        :param heat_exchange_efficiency: 换热效率
        :param storage_efficiency: 储热效率
        :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
        :param salt_temp_delta: 熔盐温差 (K)
        """
        self.heat_exchange_efficiency = heat_exchange_efficiency
        self.storage_efficiency = storage_efficiency
        self.salt_specific_heat = salt_specific_heat
        self.salt_temp_delta = salt_temp_delta

    @abstractmethod
    def calculate_cost_from_steam(
        self,
        steam_pressure: float,
        steam_temp: float,
        feedwater_pressure: float,
        feedwater_temp: float,
        mass_flow: float,
        operating_hours: float,
        electricity_price: float,
        steam_supply_hours: float,
    ) -> dict[str, float]:
        """根据蒸汽需求返回各阶段功率 (kW)、电量 (kWh) 和购电成本 (元)。"""
        ...

    @abstractmethod
    def calculate_mass_flow_from_cost(
        self,
        steam_pressure: float,
        steam_temp: float,
        feedwater_pressure: float,
        feedwater_temp: float,
        operating_hours: float,
        electricity_price: float,
        electricity_cost: float,
        steam_supply_hours: float,
    ) -> dict[str, float]:
        """根据购电成本返回各阶段结果和蒸汽质量流量 mass_flow (kg/s)。"""
        ...

    def specific_enthalpy_difference(
        self,
        steam_pressure: float,
        steam_temp: float,
        feedwater_pressure: float,
        feedwater_temp: float,
    ) -> float:
        """根据压力 (MPa)、温度 (°C)，计算制汽比焓差 (kJ/kg)。"""
        parameters = {
            "蒸汽压力": steam_pressure,
            "蒸汽温度": steam_temp,
            "给水压力": feedwater_pressure,
            "给水温度": feedwater_temp,
        }
        for name, value in parameters.items():
            if not isfinite(value):
                raise ValueError(f"{name}必须是有限数值")

        if steam_pressure <= 0 or feedwater_pressure <= 0:
            raise ValueError("蒸汽压力和给水压力必须大于零")
        if steam_temp <= -273.15 or feedwater_temp <= -273.15:
            raise ValueError("蒸汽温度和给水温度必须高于绝对零度")

        steam_state = IAPWS95(P=steam_pressure, T=steam_temp + 273.15)
        feedwater_state = IAPWS95(
            P=feedwater_pressure, T=feedwater_temp + 273.15
        )
        enthalpy_diff = steam_state.h - feedwater_state.h
        if not isfinite(enthalpy_diff) or enthalpy_diff <= 0:
            raise ValueError("蒸汽焓必须大于给水焓，才能计算制汽流量")
        return float(enthalpy_diff)

    def water_to_steam_power(
        self,
        steam_pressure: float,
        steam_temp: float,
        feedwater_pressure: float,
        feedwater_temp: float,
        mass_flow: float,
    ) -> float:
        """
        计算水变成蒸汽需要的热功率

        :param steam_pressure: 蒸汽压力 (MPa)
        :param steam_temp: 蒸汽温度 (°C)
        :param feedwater_pressure: 给水压力 (MPa)
        :param feedwater_temp: 给水温度 (°C)
        :param mass_flow: 质量流量 (kg/s)
        :return: 热功率 (kW)
        """
        enthalpy_diff = self.specific_enthalpy_difference(
            steam_pressure, steam_temp, feedwater_pressure, feedwater_temp
        )
        return enthalpy_diff * mass_flow

    def sgs_input_power(self, water_to_steam_power: float) -> float:
        """将制汽热功率转换为 SGS 入口功率，单位均为 kW。"""
        return water_to_steam_power / self.heat_exchange_efficiency

    def charging_thermal_power(self, sgs_input_power: float) -> float:
        """将 SGS 入口功率转换为充热端热功率，单位均为 kW。"""
        return sgs_input_power / self.storage_efficiency

    def calculate_salt_mass(self, charging_power: float, storage_duration: float) -> float:
        """
        计算所需熔盐储量

        :param charging_power: 充热端热功率 (kW)
        :param storage_duration: 储热时长 (h)
        :return: 熔盐质量 (吨)
        """
        return salt_storage.calculate_salt_mass(
            charging_power=charging_power,
            storage_duration=storage_duration,
            salt_specific_heat=self.salt_specific_heat,
            salt_temp_delta=self.salt_temp_delta,
        )
