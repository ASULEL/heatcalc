from heatcalc.strategy import HeatSourceStrategy


class ElectricHeaterStrategy(HeatSourceStrategy):
    def __init__(self,
                 electrical_efficiency: float,
                 # 电热效率
                 heat_exchange_efficiency: float,
                 storage_efficiency: float,
                 salt_specific_heat: float,
                 salt_temp_delta: float):
        """
            :param electrical_efficiency: 电热效率
            :param heat_exchange_efficiency: 换热效率
            :param storage_efficiency: 储热效率
            :param salt_specific_heat: 熔盐比热容
            :param salt_temp_delta: 熔盐温差
        """
        super().__init__(heat_exchange_efficiency,
                         storage_efficiency,
                         salt_specific_heat,
                         salt_temp_delta)
        self.electrical_efficiency = electrical_efficiency

    def electrical_power(self,charging_power:float):
        """
            电加热器：充热端热功率转换为电功率

            :param charging_power: 充热端热功率 (kW)
            :return: 电加热器输入功率 (kW)
        """
        return charging_power / self.electrical_efficiency
