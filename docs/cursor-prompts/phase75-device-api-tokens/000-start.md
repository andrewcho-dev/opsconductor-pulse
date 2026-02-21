# Phase 75 — Device API Token Management

## Overview
Allow tenant users to list, revoke, and rotate the MQTT credentials (api tokens) for their provisioned devices. Credentials are already generated at provision time; this phase adds management endpoints and a UI panel on the Device Detail page.

## Execution Order
1. 001-migration.md — migration 064: device_api_tokens table
2. 002-backend.md — GET/DELETE/POST endpoints
3. 003-frontend.md — DeviceApiTokensPanel component
4. 004-unit-tests.md — 5 unit tests
5. 005-verify.md — pytest + build checklist
