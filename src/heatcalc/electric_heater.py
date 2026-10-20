from math import isfinite

from heatcalc.strategy import HeatSourceStrategy


class ElectricHeaterStrategy(HeatSourceStrategy):
    """组织电加热器从蒸汽需求到购电成本，以及从成本到流量的完整流程。"""

    def __init__(
        self,
        electrical_efficiency: float,
        heat_exchange_efficiency: float,
        storage_efficiency: float,
        salt_specific_heat: float,
        salt_temp_delta: float,
    ):
        """
            :param electrical_efficiency: 电热效率
            :param heat_exchange_efficiency: 换热效率
            :param storage_efficiency: 储热效率
            :param salt_specific_heat: 熔盐比热容
            :param salt_temp_delta: 熔盐温差
        """
        super().__init__(
            heat_exchange_efficiency,
            storage_efficiency,
            salt_specific_heat,
            salt_temp_delta,
        )
        self.electrical_efficiency = electrical_efficiency

    def electrical_power(self, charging_power: float) -> float:
        """
            电加热器：充热端热功率转换为电功率

            :param charging_power: 充热端热功率 (kW)
            :return: 电加热器输入功率 (kW)
        """
        return charging_power / self.electrical_efficiency

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
        """根据蒸汽需求，逐级计算电加热器的输入功率和购电成本。

        :param steam_pressure: 蒸汽压力 (MPa)
        :param steam_temp: 蒸汽温度 (°C)
        :param feedwater_pressure: 给水压力 (MPa)
        :param feedwater_temp: 给水温度 (°C)
        :param mass_flow: 蒸汽质量流量 (kg/s)
        :param operating_hours: 谷电充热时长 (h)，必须大于零
        :param electricity_price: 电价 (元/kWh)，允许为零
        :param steam_supply_hours: 供汽时长 (h)，必须大于零
        :return: 各阶段功率 (kW)、总供热量和耗电量 (kWh)、购电成本 (元)
        :raises ValueError: 参数或设备效率无效，或制汽焓差不为正
        """
        parameters = {
            "蒸汽质量流量": mass_flow,
            "谷电充热时长": operating_hours,
            "供汽时长": steam_supply_hours,
            "电价": electricity_price,
        }
        for name, value in parameters.items():
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name}必须是大于等于零的有限数值")
        if operating_hours <= 0:
            raise ValueError("谷电充热时长必须大于零")
        if steam_supply_hours <= 0:
            raise ValueError("供汽时长必须大于零")
        self._validate_efficiencies()

        # 1. 蒸汽需求 → 制汽热功率，单位 kW
        water_to_steam_power = self.water_to_steam_power(
            steam_pressure, steam_temp, feedwater_pressure, feedwater_temp,
            mass_flow,
        )
        # 2. 制汽热功率 → SGS 入口功率，单位 kW
        sgs_input_power = self.sgs_input_power(water_to_steam_power)
        # 3. 考虑储热损失，得到供汽时段所需的热功率，单位 kW
        supply_thermal_power = self.charging_thermal_power(sgs_input_power)
        # 4. 热功率 × 供汽时长 → 总需热量，单位 kWh
        heat_energy = supply_thermal_power * steam_supply_hours
        # 5. 总需热量 ÷ 谷电时长 → 所需充热功率，单位 kW
        charging_power = heat_energy / operating_hours
        # 6. 充热功率 → 电功率，单位 kW
        electrical_power = self.electrical_power(charging_power)
        # 7. 电功率 → 耗电量，单位 kWh
        electricity_consumption = electrical_power * operating_hours
        # 8. 耗电量 → 购电成本，单位元
        electricity_cost = electricity_consumption * electricity_price

        return {
            "water_to_steam_power": float(water_to_steam_power),
            "sgs_input_power": float(sgs_input_power),
            "charging_power": float(charging_power),
            "electrical_power": float(electrical_power),
            "heat_energy": float(heat_energy),
            "electricity_consumption": float(electricity_consumption),
            "electricity_cost": float(electricity_cost),
        }

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
        """根据购电成本，逐级反算电加热器能够供给的蒸汽质量流量。

        充热功率按谷电充热时长折算，供汽功率按供汽时长折算。

        :param steam_pressure: 蒸汽压力 (MPa)
        :param steam_temp: 蒸汽温度 (°C)
        :param feedwater_pressure: 给水压力 (MPa)
        :param feedwater_temp: 给水温度 (°C)
        :param operating_hours: 谷电充热时长 (h)，必须大于零
        :param electricity_price: 电价 (元/kWh)，必须大于零
        :param electricity_cost: 购电成本 (元)，允许为零
        :param steam_supply_hours: 供汽时长 (h)，必须大于零
        :return: 各阶段功率 (kW)、总供热量和耗电量 (kWh)、购电成本 (元)
                 和蒸汽质量流量 mass_flow (kg/s)
        :raises ValueError: 参数或设备效率无效，或制汽焓差不为正
        """
        parameters = {
            "谷电充热时长": operating_hours,
            "供汽时长": steam_supply_hours,
            "电价": electricity_price,
            "购电成本": electricity_cost,
        }
        for name, value in parameters.items():
            if not isfinite(value):
                raise ValueError(f"{name}必须是有限数值")

        if electricity_cost < 0:
            raise ValueError("购电成本不能为负数")
        if electricity_price <= 0:
            raise ValueError("电价必须大于零")
        if operating_hours <= 0:
            raise ValueError("谷电充热时长必须大于零")
        if steam_supply_hours <= 0:
            raise ValueError("供汽时长必须大于零")
        self._validate_efficiencies()

        # 1. 购电成本 → 耗电量，单位 kWh
        electricity_consumption = electricity_cost / electricity_price
        # 2. 耗电量 → 电功率，单位 kW
        electrical_power = electricity_consumption / operating_hours
        # 3. 电功率 → 电加热器输出的充热功率，单位 kW
        charging_power = electrical_power * self.electrical_efficiency
        # 4. 充热功率 × 谷电时长 → 总供热量，单位 kWh
        heat_energy = charging_power * operating_hours
        # 5. 总供热量 ÷ 供汽时长 → 供汽时段所需的热功率，单位 kW
        supply_thermal_power = heat_energy / steam_supply_hours
        # 6. 考虑储热损失 → SGS 入口功率，单位 kW
        sgs_input_power = supply_thermal_power * self.storage_efficiency
        # 7. SGS 入口功率 → 制汽热功率，单位 kW
        water_to_steam_power = sgs_input_power * self.heat_exchange_efficiency

        # 8. 根据蒸汽和给水工况计算比焓差，单位 kJ/kg
        enthalpy_diff = self.specific_enthalpy_difference(
            steam_pressure, steam_temp, feedwater_pressure, feedwater_temp
        )

        # 9. 制汽热功率 ÷ 比焓差 → 蒸汽质量流量，单位 kg/s
        mass_flow = water_to_steam_power / enthalpy_diff

        return {
            "water_to_steam_power": float(water_to_steam_power),
            "sgs_input_power": float(sgs_input_power),
            "charging_power": float(charging_power),
            "electrical_power": float(electrical_power),
            "heat_energy": float(heat_energy),
            "electricity_consumption": float(electricity_consumption),
            "electricity_cost": float(electricity_cost),
            "mass_flow": float(mass_flow),
        }

    def _validate_efficiencies(self) -> None:
        """统一检查电加热器正反算使用的三项效率。"""
        efficiencies = {
            "电热效率": self.electrical_efficiency,
            "储热效率": self.storage_efficiency,
            "换热效率": self.heat_exchange_efficiency,
        }
        for name, efficiency in efficiencies.items():
            if not isfinite(efficiency) or not 0 < efficiency <= 1:
                raise ValueError(f"{name}必须大于零且不超过 1")
