import random

DEFAULT_PROFILE_MIX = "temperature_sensor:20,door_sensor:10,energy_meter:10,pressure_sensor:10,motion_sensor:10,hvac_controller:10,water_meter:10,air_quality:5,vibration_sensor:10,gps_tracker:5"

SENSOR_PROFILES = [
    {
        "name": "temperature_sensor",
        "telemetry_interval_seconds": 30,
        "heartbeat_interval_seconds": 10,
        "failure_probability": 0.002,
        "battery_powered": True,
        "metrics": {
            "temp_c": {"min": 15.0, "max": 40.0, "unit": "C", "kind": "float", "drift": 0.25},
            "humidity_pct": {"min": 20.0, "max": 80.0, "unit": "%", "kind": "float", "drift": 1.0},
        },
    },
    {
        "name": "door_sensor",
        "telemetry_interval_seconds": 60,
        "heartbeat_interval_seconds": 20,
        "failure_probability": 0.003,
        "battery_powered": True,
        "metrics": {
            "door_open": {"min": 0, "max": 1, "unit": "bool", "kind": "bool", "flip_chance": 0.08},
            "open_count": {"min": 0, "max": 100000, "unit": "count", "kind": "counter", "step_min": 0, "step_max": 3},
        },
    },
    {
        "name": "energy_meter",
        "telemetry_interval_seconds": 10,
        "heartbeat_interval_seconds": 10,
        "failure_probability": 0.001,
        "battery_powered": False,
        "metrics": {
            "power_kw": {"min": 0.0, "max": 50.0, "unit": "kW", "kind": "float", "drift": 1.5},
            "energy_kwh": {"min": 0.0, "max": 100000.0, "unit": "kWh", "kind": "counter", "step_min": 0.1, "step_max": 2.5},
            "voltage_v": {"min": 110.0, "max": 130.0, "unit": "V", "kind": "float", "drift": 0.5},
        },
    },
    {
        "name": "pressure_sensor",
        "telemetry_interval_seconds": 15,
        "heartbeat_interval_seconds": 15,
        "failure_probability": 0.002,
        "battery_powered": True,
        "metrics": {
            "pressure_psi": {"min": 0.0, "max": 150.0, "unit": "psi", "kind": "float", "drift": 1.0},
            "temp_c": {"min": 10.0, "max": 60.0, "unit": "C", "kind": "float", "drift": 0.5},
        },
    },
    {
        "name": "motion_sensor",
        "telemetry_interval_seconds": 5,
        "heartbeat_interval_seconds": 10,
        "failure_probability": 0.004,
        "battery_powered": True,
        "metrics": {
            "motion_detected": {"min": 0, "max": 1, "unit": "bool", "kind": "bool", "flip_chance": 0.2},
            "motion_events": {"min": 0, "max": 100000, "unit": "count", "kind": "counter", "step_min": 0, "step_max": 4},
        },
    },
    {
        "name": "hvac_controller",
        "telemetry_interval_seconds": 30,
        "heartbeat_interval_seconds": 10,
        "failure_probability": 0.002,
        "battery_powered": False,
        "metrics": {
            "temp_setpoint": {"min": 18.0, "max": 28.0, "unit": "C", "kind": "float", "drift": 0.1},
            "temp_actual": {"min": 16.0, "max": 32.0, "unit": "C", "kind": "float", "drift": 0.3},
            "fan_speed": {"min": 0, "max": 3, "unit": "level", "kind": "int", "drift": 1},
            "mode": {"min": 0, "max": 0, "unit": "enum", "kind": "enum", "values": ["off", "cool", "heat", "auto"], "change_chance": 0.02},
        },
    },
    {
        "name": "water_meter",
        "telemetry_interval_seconds": 60,
        "heartbeat_interval_seconds": 20,
        "failure_probability": 0.002,
        "battery_powered": True,
        "metrics": {
            "flow_lpm": {"min": 0.0, "max": 100.0, "unit": "L/min", "kind": "float", "drift": 2.0},
            "total_liters": {"min": 0.0, "max": 1000000.0, "unit": "L", "kind": "counter", "step_min": 0.0, "step_max": 50.0},
        },
    },
    {
        "name": "air_quality",
        "telemetry_interval_seconds": 30,
        "heartbeat_interval_seconds": 10,
        "failure_probability": 0.002,
        "battery_powered": True,
        "metrics": {
            "co2_ppm": {"min": 400.0, "max": 2000.0, "unit": "ppm", "kind": "float", "drift": 25.0},
            "pm25_ugm3": {"min": 0.0, "max": 500.0, "unit": "ug/m3", "kind": "float", "drift": 5.0},
            "voc_ppb": {"min": 0.0, "max": 1200.0, "unit": "ppb", "kind": "float", "drift": 15.0},
        },
    },
    {
        "name": "vibration_sensor",
        "telemetry_interval_seconds": 5,
        "heartbeat_interval_seconds": 10,
        "failure_probability": 0.003,
        "battery_powered": True,
        "metrics": {
            "vibration_g": {"min": 0.0, "max": 10.0, "unit": "g", "kind": "float", "drift": 0.3},
            "frequency_hz": {"min": 0.0, "max": 500.0, "unit": "Hz", "kind": "float", "drift": 10.0},
        },
    },
    {
        "name": "gps_tracker",
        "telemetry_interval_seconds": 10,
        "heartbeat_interval_seconds": 10,
        "failure_probability": 0.003,
        "battery_powered": True,
        "metrics": {
            "latitude": {"min": -90.0, "max": 90.0, "unit": "deg", "kind": "geo_lat", "drift": 0.0005},
            "longitude": {"min": -180.0, "max": 180.0, "unit": "deg", "kind": "geo_lon", "drift": 0.0005},
            "speed_kmh": {"min": 0.0, "max": 120.0, "unit": "km/h", "kind": "float", "drift": 3.0},
            "heading": {"min": 0.0, "max": 359.0, "unit": "deg", "kind": "float", "drift": 10.0},
        },
    },
]


def pick_profile_by_mix(mix, rng):
    total = sum(weight for _, weight in mix)
    if total <= 0:
        return SENSOR_PROFILES[0]
    roll = rng.uniform(0, total)
    for profile, weight in mix:
        if roll <= weight:
            return profile
        roll -= weight
    return mix[-1][0]


def parse_profile_mix(mix_str):
    if not mix_str:
        mix_str = DEFAULT_PROFILE_MIX
    by_name = {p["name"]: p for p in SENSOR_PROFILES}
    items = []
    for part in mix_str.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            continue
        name, weight = part.split(":", 1)
        name = name.strip()
        if name in by_name:
            try:
                weight_val = float(weight.strip())
            except ValueError:
                weight_val = 0.0
            items.append((by_name[name], weight_val))
    if not items:
        return [(SENSOR_PROFILES[0], 1.0)]
    return items
