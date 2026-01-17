# Implementation Plan: Get Work Package Tool

**Branch**: `001-get-work-package` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-get-work-package/spec.md`

## Summary

Add a `get_work_package` MCP tool that retrieves complete details of a specific work package by ID from OpenProject. The tool will follow existing patterns in `mcp_server.py`, use the shared `OpenProjectClient`, and return structured JSON with all work package fields including status, assignee, dates, and timestamps.

## Technical Context

**Language/Version**: Python 3.8+ (3.11 recommended)
**Primary Dependencies**: FastMCP >= 0.9.0, httpx, Pydantic
**Storage**: N/A (read-only from OpenProject API)
**Testing**: pytest with async support
**Target Platform**: Linux server (Docker container)
**Project Type**: Single project
**Performance Goals**: < 2 seconds response time per request (per SC-001)
**Constraints**: Must use existing async client, follow HAL+JSON parsing patterns
**Scale/Scope**: Single work package retrieval per request

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Test-First Development | ✅ PASS | Tests will be written before implementation |
| II. Async-First Architecture | ✅ PASS | Will use existing async OpenProjectClient |
| III. API Contract Compliance | ✅ PASS | Will parse HAL+JSON response via existing patterns |
| IV. Simplicity and YAGNI | ✅ PASS | Single-purpose tool, no new abstractions |
| V. Observability | ✅ PASS | Will use existing logging utilities |

**All gates pass. No violations to justify.**

## Project Structure

### Documentation (this feature)

```text
specs/001-get-work-package/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── get_work_package.json
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── mcp_server.py        # Add get_work_package tool function
├── openproject_client.py # Add get_work_package_by_id method
├── models.py            # WorkPackage model already exists
└── utils/logging.py     # Existing logging utilities

tests/
├── test_api_compliance.py   # Add contract tests for get_work_package
└── test_integration.py      # Add integration tests
```

**Structure Decision**: Using existing single project structure. No new directories needed - feature adds methods to existing modules following established patterns.

## Complexity Tracking

> No violations - section not required.
