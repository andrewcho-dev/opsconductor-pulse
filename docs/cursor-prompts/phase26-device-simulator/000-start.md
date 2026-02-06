# Phase 26: Device Simulator

## Overview

Create a device simulator that continuously sends telemetry data via MQTT or HTTP, so the system always has fresh data for demos.

## Why

- Static seed data gets stale and falls outside display time windows
- Need real-time data flow for testing alerts, charts, and dashboards
- Simulates actual IoT devices for demos

## What We'll Build

A Python script that:
- Simulates N devices across multiple tenants/sites
- Sends heartbeat every 30 seconds
- Sends telemetry every 60 seconds with realistic metrics
- Runs continuously in Docker
- Metrics vary realistically (battery drains, temp fluctuates, etc.)

## Execute Prompts In Order

1. `001-simulator-script.md` — Create the simulator
2. `002-wire-compose.md` — Add to docker-compose

## Files

| File | Role |
|------|------|
| `scripts/device_simulator.py` | NEW — Simulator script |
| `compose/docker-compose.yml` | Add simulator service |

## Start Now

Read and execute `001-simulator-script.md`.
