# Tasks: Get Work Package Tool

**Input**: Design documents from `/specs/001-get-work-package/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: REQUIRED per Constitution Principle I (Test-First Development - NON-NEGOTIABLE)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below match existing project structure from plan.md

---

## Phase 1: Setup

**Purpose**: Verify prerequisites and environment readiness

- [x] T001 Verify OpenProjectClient.get_work_package_by_id() exists in src/openproject_client.py
- [x] T002 Verify WorkPackage model exists in src/models.py
- [x] T003 [P] Verify test fixtures exist in tests/conftest.py for async testing

**Checkpoint**: Environment verified - implementation can begin

---

## Phase 2: Foundational

**Purpose**: No blocking prerequisites needed - client method already exists

> **Note**: The `get_work_package_by_id` method already exists in `src/openproject_client.py:256-259`.
> No foundational work required.

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Retrieve Work Package Details (Priority: P1)

**Goal**: Enable users to retrieve complete details of any work package by ID

**Independent Test**: Request a known work package ID and verify all expected fields are returned with correct values

### Tests for User Story 1 (TDD - Write First, Must Fail)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Contract test for get_work_package success case in tests/test_api_compliance.py
- [x] T005 [P] [US1] Contract test for get_work_package response field mapping in tests/test_api_compliance.py

### Implementation for User Story 1

- [x] T006 [US1] Add get_work_package MCP tool function in src/mcp_server.py with input validation (work_package_id > 0)
- [x] T007 [US1] Implement HAL+JSON response parsing to extract all fields per data-model.md in src/mcp_server.py
- [x] T008 [US1] Add structured logging for get_work_package operations in src/mcp_server.py

**Checkpoint**: User Story 1 complete - can retrieve any valid work package with all fields

---

## Phase 4: User Story 2 - Handle Invalid Work Package ID (Priority: P2)

**Goal**: Provide clear error messages for invalid requests (not found, invalid ID, permission denied)

**Independent Test**: Request non-existent work package ID and verify appropriate error message

### Tests for User Story 2 (TDD - Write First, Must Fail)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US2] Contract test for work package not found (404) error in tests/test_api_compliance.py
- [x] T010 [P] [US2] Contract test for invalid ID validation error in tests/test_api_compliance.py

### Implementation for User Story 2

- [x] T011 [US2] Add error handling for 404 Not Found responses in src/mcp_server.py
- [x] T012 [US2] Add error handling for 403 Permission Denied responses in src/mcp_server.py
- [x] T013 [US2] Add error handling for API connection failures in src/mcp_server.py

**Checkpoint**: User Story 2 complete - all error cases return actionable messages

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [x] T014 Run all tests to verify both user stories work correctly
- [ ] T015 [P] Run quickstart.md verification steps manually
- [x] T016 [P] Verify tool appears in MCP server tool list

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify environment first
- **Foundational (Phase 2)**: Depends on Setup - already complete (no work needed)
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 (error handling builds on success case)
- **Polish (Phase 5)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 - implements core retrieval functionality
- **User Story 2 (P2)**: Depends on User Story 1 - adds error handling to existing implementation

### Within Each User Story (TDD Order)

1. Tests MUST be written and FAIL before implementation
2. Implementation MUST satisfy failing tests
3. Refactor only after tests pass
4. Story complete before moving to next priority

### Parallel Opportunities

```bash
# Phase 1 - All verification tasks can run in parallel:
T001, T002, T003

# User Story 1 - Tests can run in parallel:
T004, T005

# User Story 2 - Tests can run in parallel:
T009, T010

# Phase 5 - Polish tasks can run in parallel:
T015, T016
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup verification
2. Complete Phase 2: Foundational (already done - no tasks)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test retrieval with real work package ID
5. Deploy/demo if ready - basic functionality works

### Full Implementation

1. Complete MVP (User Story 1)
2. Add User Story 2 (error handling)
3. Complete Polish phase
4. All acceptance scenarios verified

---

## Notes

- [P] tasks = different files or parallel-safe operations
- [Story] label maps task to specific user story
- Client method `get_work_package_by_id` already exists - no new client code needed
- WorkPackage model already exists - no model changes needed
- Follow existing patterns in mcp_server.py (see create_work_package, get_work_packages)
- Tests are REQUIRED per Constitution Principle I
