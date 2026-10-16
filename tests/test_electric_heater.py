from heatcalc.electric_heater import ElectricHeaterStrategy

heater = ElectricHeaterStrategy(
    electrical_efficiency=0.985,
    heat_exchange_efficiency=0.99,
    storage_efficiency=0.99,
    salt_specific_heat=1.5,
    salt_temp_delta=240
)

water_to_steam = heater.water_to_steam_power(
    steam_pressure=1.5, steam_temp=200,
    feedwater_pressure=0.1, feedwater_temp=20,
    mass_flow=100 * 1000 / 3600  # 假设100 t/h换算成kg/s
)
print(f"水变蒸汽功率: {water_to_steam:.2f} kW")

sgs_input = heater.sgs_input_power(water_to_steam)
print(f"SGS入口功率: {sgs_input:.2f} kW")

charging_power = heater.charging_thermal_power(sgs_input)
print(f"充热端功率: {charging_power:.2f} kW")

elec_power = heater.electrical_power(charging_power)
print(f"电加热器输入功率: {elec_power:.2f} kW")

print(heater.calculate_cost_from_steam(
    steam_pressure=1.5, steam_temp=200,
    feedwater_pressure=0.1, feedwater_temp=20,
    mass_flow=100 * 1000 / 3600,
    operating_hours=8,
    electricity_price=0.35
))

print(heater.calculate_salt_mass(
    charging_power, 8
))