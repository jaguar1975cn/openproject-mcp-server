# Feature Specification: Add Status Parameter to Update Work Package

**Feature Branch**: `002-update-work-package-status`
**Created**: 2026-01-18
**Status**: Draft
**Input**: User description: "Improve `update_work_package`, add parameter `status`"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Update Work Package Status (Priority: P1)

As an AI assistant user interacting with OpenProject through the MCP server, I want to update a work package's status (e.g., from "New" to "In Progress" or "Closed") so that I can manage work package lifecycle without leaving the AI interface.

**Why this priority**: Status is the most frequently updated attribute during work package lifecycle management. Users need to mark tasks as started, in progress, blocked, or completed. This is the core value of the enhancement.

**Independent Test**: Can be fully tested by calling `update_work_package` with only the `status` parameter and verifying the work package status changes in OpenProject.

**Acceptance Scenarios**:

1. **Given** a work package exists with ID 123 and current status "New", **When** I call `update_work_package(work_package_id=123, status="In Progress")`, **Then** the work package status is updated to "In Progress" and the response confirms success with the new status.

2. **Given** a work package exists with ID 456, **When** I call `update_work_package(work_package_id=456, status="Closed")`, **Then** the work package status is updated to "Closed" and the response shows `is_closed: true`.

3. **Given** a work package exists with ID 789, **When** I call `update_work_package(work_package_id=789, subject="New Title", status="In Progress")`, **Then** both the subject and status are updated successfully in a single operation.

---

### User Story 2 - Validate Status Before Update (Priority: P2)

As an AI assistant user, I want the system to validate that the status I provide is a valid OpenProject status name so that I receive clear error messages if I use an invalid status.

**Why this priority**: Input validation prevents confusing errors from the OpenProject API and provides a better user experience with actionable error messages.

**Independent Test**: Can be tested by attempting to set an invalid status name and verifying a clear error message is returned.

**Acceptance Scenarios**:

1. **Given** a work package exists with ID 123, **When** I call `update_work_package(work_package_id=123, status="InvalidStatusName")`, **Then** I receive an error response indicating the status is not valid and listing available statuses.

2. **Given** I want to know what statuses are available, **When** the status validation fails, **Then** the error message includes a list of valid status names.

---

### User Story 3 - Status Update in Response (Priority: P3)

As an AI assistant user, I want the response from `update_work_package` to include the updated status information so that I can confirm the change was applied correctly.

**Why this priority**: Confirmation of changes is important for user confidence but is less critical than the core functionality.

**Independent Test**: Can be tested by performing any status update and verifying the response includes the new status name.

**Acceptance Scenarios**:

1. **Given** a successful status update, **When** I receive the response, **Then** the response includes `status` field showing the new status name.

2. **Given** a successful status update, **When** I receive the response, **Then** the response includes metadata about the status such as whether it is a closed status.

---

### Edge Cases

- What happens when the work package ID does not exist? System returns a clear "work package not found" error.
- What happens when the status name has different casing (e.g., "in progress" vs "In Progress")? System performs case-insensitive matching.
- What happens when the work package is in a read-only status and cannot be updated? System returns the API error explaining the constraint.
- What happens when the status parameter is empty string? System ignores the status update (same as not providing it).
- What happens when the user provides a status ID instead of status name? System accepts both status ID (integer) and status name (string).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an optional `status` parameter in the `update_work_package` function that allows users to specify the desired work package status.

- **FR-002**: System MUST support status specification by either status name (string) or status ID (integer) for flexibility.

- **FR-003**: System MUST perform case-insensitive matching when a status name string is provided.

- **FR-004**: System MUST return a clear error message when an invalid status is provided, including a list of valid status names.

- **FR-005**: System MUST include the updated status information in the successful response, including the status name and whether it is a closed status.

- **FR-006**: System MUST allow the status parameter to be combined with other update parameters (subject, description, dates, etc.) in a single call.

- **FR-007**: System MUST treat an empty string or null status parameter the same as not providing it (no status change).

### Key Entities

- **Status**: Represents a work package status in OpenProject. Has attributes: id (integer), name (string), is_closed (boolean), is_default (boolean), position (integer).
- **Work Package**: The entity being updated. Has a current status that can be changed to any valid status defined in the OpenProject instance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can update work package status in a single API call without needing to know the status ID upfront.

- **SC-002**: Status updates complete successfully with the same response time as other work package updates (no noticeable delay).

- **SC-003**: Invalid status names result in helpful error messages that enable users to self-correct within one retry.

- **SC-004**: 100% of valid OpenProject statuses can be set through the new parameter.

- **SC-005**: Existing `update_work_package` calls without the status parameter continue to work unchanged (backward compatibility).

## Assumptions

- OpenProject instances have at least one status configured (standard OpenProject installations include default statuses like "New", "In Progress", "Closed").
- The OpenProject API supports updating work package status via the same PATCH endpoint used for other work package updates.
- Status names are unique within an OpenProject instance (OpenProject enforces this by default).
- The MCP server already has access to fetch available statuses via the existing `get_work_package_statuses` function.
