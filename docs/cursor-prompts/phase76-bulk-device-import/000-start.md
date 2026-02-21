# Phase 76 — Bulk Device CSV Import

## Overview
Allow tenant users to upload a CSV file to import multiple devices at once. The backend parses the CSV, validates rows, and provisions each device. The frontend provides a file picker, column preview, and per-row result display.

## Execution Order
1. 001-backend.md — POST /customer/devices/import endpoint
2. 002-frontend.md — BulkImportPage + ImportResultsTable
3. 003-unit-tests.md — 5 unit tests
4. 004-verify.md — checklist
