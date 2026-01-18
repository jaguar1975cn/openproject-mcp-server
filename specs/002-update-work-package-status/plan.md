# Implementation Plan: Add Status Parameter to Update Work Package

**Branch**: `002-update-work-package-status` | **Date**: 2026-01-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-update-work-package-status/spec.md`

## Summary

Enhance the `update_work_package` MCP tool to accept an optional `status` parameter, enabling AI assistants to change work package status (e.g., "New" → "In Progress" → "Closed") via the OpenProject API. The implementation will support both status names (case-insensitive) and status IDs, with validation against available statuses and clear error messaging.

## Technical Context

**Language/Version**: Python 3.8+ (3.11 recommended)
**Primary Dependencies**: FastMCP >= 0.9.0, httpx (async HTTP client), Pydantic (validation)
**Storage**: N/A (stateless, uses OpenProject API)
**Testing**: pytest with async support
**Target Platform**: Linux server (Docker deployment on port 39127)
**Project Type**: Single project (MCP server)
**Performance Goals**: Same response time as existing `update_work_package` calls
**Constraints**: Must be backward compatible with existing API calls
**Scale/Scope**: Single function enhancement, minimal code changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Test-First Development | ✅ WILL COMPLY | Tests will be written before implementation |
| II. Async-First Architecture | ✅ COMPLIANT | Uses existing async httpx client |
| III. API Contract Compliance | ✅ WILL COMPLY | Uses OpenProject v3 HAL+JSON format for status links |
| IV. Simplicity and YAGNI | ✅ COMPLIANT | Minimal addition to existing function |
| V. Observability | ✅ WILL COMPLY | Will use existing logging patterns |

**Gate Result**: PASS - All principles satisfied, no violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/002-update-work-package-status/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── mcp_server.py        # UPDATE: Add status parameter to update_work_package
├── openproject_client.py # EXISTING: Already has get_work_package_statuses
├── models.py            # EXISTING: May need status validation helper
├── config.py            # NO CHANGE
├── handlers/            # NO CHANGE
└── utils/
    ├── logging.py       # NO CHANGE
    └── validation.py    # POSSIBLE: Add status validation helper

tests/
├── test_integration.py  # UPDATE: Add status update integration tests
├── test_api_compliance.py # UPDATE: Add status parameter contract tests
└── unit/                # NEW: Add status resolution unit tests (if needed)
```

**Structure Decision**: Single project structure. Changes are localized to `src/mcp_server.py` (add status parameter) with potential helper in `src/utils/validation.py` (status name resolution). Tests added to existing test files.

## Complexity Tracking

> No violations to justify - implementation follows all constitution principles.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
