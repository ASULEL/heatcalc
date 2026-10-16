from abc import ABC,abstractmethod
from iapws import IAPWS97, IAPWS95


class HeatSourceStrategy(ABC):

    def __init__(self,
                 heat_exchange_efficiency: float,  # 换热效率
                 storage_efficiency: float,  # 储热效率
                 salt_specific_heat: float,  # 熔盐比热容
                 salt_temp_delta: float  # 熔盐温差
                 ):
        """
        :param heat_exchange_efficiency:
        :param storage_efficiency:
        :param salt_specific_heat:
        :param salt_temp_delta:
        """
        self.heat_exchange_efficiency = heat_exchange_efficiency
        self.storage_efficiency = storage_efficiency
        self.salt_specific_heat = salt_specific_heat
        self.salt_temp_delta = salt_temp_delta

    def water_to_steam_power(self,
                            steam_pressure: float,# MPa
                            steam_temp: float,  # °C
                            feedwater_pressure: float,  # MPa
                            feedwater_temp: float,  # °C
                            mass_flow: float  # kg/s（标准SI单位）
                            ) -> float:
        """
        计算水变成蒸汽需要的热功率

        注意：所有参数必须使用SI单位

        :param steam_pressure: 蒸汽压力 (MPa)
        :param steam_temp: 蒸汽温度 (°C)
        :param feedwater_pressure: 给水压力 (MPa)
        :param feedwater_temp: 给水温度 (°C)
        :param mass_flow: 质量流量 (kg/s)  ← 注意单位
        :return: 热功率 (kW)
        """
        # 1.蒸汽焓值
        steam_state = IAPWS95(P=steam_pressure,T=steam_temp + 273.15)
        h_steam = steam_state.h
        # 2.给水焓值
        feedwater_state = IAPWS95(P=feedwater_pressure,T=feedwater_temp + 273.15)
        h_feedwater = feedwater_state.h
        # 3.计算焓差
        enthalpy_diff = h_steam - h_feedwater
        # 4.计算热功率
        thermal_power_kw = enthalpy_diff * mass_flow
        return thermal_power_kw

    def sgs_input_power(self,water_to_steam_power: float)->float:
        """
        :param water_to_steam_power: 水变蒸汽的功率
        :return:
        """
        return water_to_steam_power / self.heat_exchange_efficiency

    def  charging_thermal_power(self,sgs_input_power:float):
        """
            计算充热端热功率（热源需要输出多少热量充入储热系统）

            :param sgs_input_power: SGS入口需要的功率 (kW)
            :return: 充热端热功率 (kW)
        """
        return sgs_input_power / self.storage_efficiency

    @abstractmethod
    def electrical_power(self,charging_power:float):
        """
             将充热端热功率转换为电功率（子类必须实现）
             电加热器：用效率计算
             热泵：用COP计算

             :param charging_power: 充热端热功率 (kW)
             :return: 所需电功率 (kW)
        """
        ...




    def calculate_cost_from_steam(self,
                                  steam_pressure: float,  # MPa
                                  steam_temp: float,  # °C
                                  feedwater_pressure: float,  # MPa
                                  feedwater_temp: float,  # °C
                                  mass_flow: float,
                                  operating_hours: float,
                                  electricity_price: float
                                  ) -> float:
        """
              从蒸汽参数一路计算到购电成本

              :param steam_pressure: 蒸汽压力 (MPa)
              :param steam_temp: 蒸汽温度 (°C)
              :param feedwater_pressure: 给水压力 (MPa)
              :param feedwater_temp: 给水温度 (°C)
              :param mass_flow: 质量流量 (kg/s)
              :param operating_hours: 运行时长 (h)
              :param electricity_price: 电价 (元/kWh)
              :return: 购电成本 (元)
        """
        w2s = self.water_to_steam_power(steam_pressure,
                                  steam_temp,
                                  feedwater_pressure,
                                  feedwater_temp,
                                  mass_flow)
        sgs_in = self.sgs_input_power(w2s)
        charging = self.charging_thermal_power(sgs_in)
        elec = self.electrical_power(charging)
        return {
            'water_to_steam_power': float(w2s),
            'sgs_input_power': float(sgs_in),
            'charging_power': float(charging),
            'electrical_power': float(elec),
            'electricity_consumption': float(elec * operating_hours),
            'electricity_cost': float(elec * operating_hours * electricity_price)
        }

    def calculate_salt_mass(self, charging_power: float, storage_duration: float) -> float:
        """
        计算所需熔盐储量

        :param charging_power: 充热端热功率 (kW)
        :param storage_duration: 储热时长 (h)
        :return: 熔盐质量 (吨)
        """
        # 你的实现
        return charging_power * storage_duration * 3600 / (self.salt_specific_heat * self.salt_temp_delta) / 1000