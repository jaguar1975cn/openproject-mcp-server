<!--
==========================================================================
SYNC IMPACT REPORT
==========================================================================
Version change: 0.0.0 → 1.0.0 (Initial constitution)
Bump rationale: MAJOR - Initial adoption of project governance

Modified principles: N/A (initial creation)

Added sections:
- Core Principles (5 principles)
- Technical Standards
- Development Workflow
- Governance

Removed sections: None

Templates requiring updates:
- .specify/templates/plan-template.md ✅ (Constitution Check section compatible)
- .specify/templates/spec-template.md ✅ (Requirements section compatible)
- .specify/templates/tasks-template.md ✅ (Test-first workflow compatible)
- .specify/templates/checklist-template.md ✅ (No updates needed)
- .specify/templates/agent-file-template.md ✅ (No updates needed)

Follow-up TODOs: None
==========================================================================
-->

# OpenProject MCP Server Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

All new functionality MUST follow test-driven development practices:

- Tests MUST be written before implementation code
- Tests MUST fail before implementation begins (red phase)
- Implementation MUST only satisfy failing tests (green phase)
- Refactoring MUST occur only after tests pass (refactor phase)
- Integration tests MUST cover: API endpoint contracts, OpenProject API interactions, MCP tool responses

**Rationale**: Test-first development ensures code correctness, documents expected behavior, and prevents regression. For an MCP server interfacing with external APIs, contract verification is essential.

### II. Async-First Architecture

All I/O operations MUST use asyncio patterns:

- HTTP client operations MUST be async (httpx AsyncClient)
- A single shared client instance MUST be used across the application
- Resource cleanup MUST use proper async context managers
- Blocking operations MUST NOT be introduced in async code paths

**Rationale**: The MCP server handles concurrent requests to OpenProject. Async patterns maximize throughput and prevent resource exhaustion under load.

### III. API Contract Compliance

All OpenProject API interactions MUST follow contract-first principles:

- HAL+JSON response format MUST be correctly parsed and handled
- API error responses MUST be transformed into actionable MCP errors
- Pydantic models MUST validate all inputs and outputs
- Breaking API changes MUST be versioned and documented

**Rationale**: OpenProject uses HAL+JSON format with specific conventions. Strict contract compliance ensures reliable integration and meaningful error messages for AI assistants.

### IV. Simplicity and YAGNI

All implementations MUST follow minimal complexity principles:

- Features MUST NOT be added until explicitly required
- Abstractions MUST NOT be created for single-use cases
- Configuration MUST use sensible defaults with optional overrides
- Dependencies MUST be justified before addition

**Rationale**: An MCP server should be lightweight and maintainable. Over-engineering increases maintenance burden and deployment complexity.

### V. Observability

All operations MUST be observable and debuggable:

- Structured JSON logging MUST be used for all significant operations
- API requests and responses MUST be logged at DEBUG level
- Errors MUST include context sufficient for diagnosis
- Performance metrics (cache hits, API latency) SHOULD be tracked

**Rationale**: When AI assistants use MCP tools, operators need visibility into what operations are being performed and why failures occur.

## Technical Standards

### Technology Stack

- **Language**: Python 3.8+ (3.11 recommended for production)
- **Framework**: FastMCP >= 0.9.0
- **HTTP Client**: httpx with async support
- **Validation**: Pydantic data models
- **Logging**: Structured JSON format

### API Requirements

- OpenProject API v3 with HAL+JSON format
- Basic Auth using API keys (40-character tokens)
- 5-minute TTL cache for configuration data (types, statuses, priorities)
- Pagination support for large result sets

### Docker Deployment

- Port 39127 is the recommended MCP server port
- Container MUST use 0.0.0.0 for MCP_HOST binding
- Environment variables MUST NOT contain hardcoded credentials
- Health checks MUST be implemented for production deployments

## Development Workflow

### Code Review Requirements

All changes MUST be reviewed for:

1. **Principle compliance**: Does this change follow constitution principles?
2. **Test coverage**: Are tests present and do they fail before implementation?
3. **API contract**: Do changes maintain OpenProject API compatibility?
4. **Error handling**: Are errors actionable and properly logged?

### Quality Gates

- All tests MUST pass before merge
- New code MUST have corresponding test coverage
- Linting and formatting MUST pass (configured tools)
- No security vulnerabilities in dependencies

### Testing Hierarchy

1. **Contract tests**: Verify MCP tool inputs/outputs match specifications
2. **Integration tests**: Verify OpenProject API interactions
3. **Unit tests**: Verify isolated business logic

## Governance

This constitution supersedes all other development practices for this project.

### Amendment Process

1. Proposed amendments MUST be documented with rationale
2. Amendments MUST include migration plan for affected code
3. Version MUST be incremented according to semantic versioning:
   - MAJOR: Principle removal or incompatible redefinition
   - MINOR: New principle or materially expanded guidance
   - PATCH: Clarifications, wording, or non-semantic refinements

### Compliance Review

- All pull requests MUST verify compliance with active principles
- Complexity additions MUST be justified in PR description
- Principle violations MUST be flagged and resolved before merge

### Runtime Guidance

For day-to-day development guidance, refer to `CLAUDE.md` at the repository root.

**Version**: 1.0.0 | **Ratified**: 2026-01-17 | **Last Amended**: 2026-01-17
