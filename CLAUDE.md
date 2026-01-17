# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastMCP-powered server enabling AI assistants to interact with OpenProject installations. Provides project management functionality including user management, work package dependencies for Gantt charts, and dynamic configuration loading.

## Common Commands

### Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-test.txt  # For testing
```

### Running the Server
```bash
python3 scripts/run_server.py           # Local development
./scripts/deploy.sh deploy 39127        # Docker deployment (recommended port)
```

### Testing
```bash
python3 scripts/test_mvp.py             # Quick MVP validation
python3 tests/run_tests.py              # Run all tests
python3 -m pytest tests/test_api_compliance.py -v  # Specific test file
python3 -m pytest --cov=src tests/      # With coverage
```

### Docker Management
```bash
./scripts/deploy.sh logs                # View container logs
./scripts/deploy.sh status              # Check status
./scripts/deploy.sh stop                # Stop container
./scripts/deploy.sh clean               # Remove container and image
```

## Architecture

### Core Components

- **`src/mcp_server.py`** - FastMCP application with all MCP tools (main entry point)
- **`src/openproject_client.py`** - Async OpenProject API client using httpx
- **`src/config.py`** - Settings management from environment variables
- **`src/models.py`** - Pydantic data models (Project, WorkPackage, etc.)

### Key Patterns

- **Async-first**: All I/O operations use asyncio
- **Single client instance**: Shared `OpenProjectClient` across app
- **Pydantic validation**: All inputs validated with data models
- **5-minute TTL cache**: For configuration data (types, statuses, priorities)
- **HAL+JSON parsing**: Custom error handling for OpenProject API responses

### Directory Structure

```
src/
├── mcp_server.py              # FastMCP tools and server
├── openproject_client.py      # API client
├── config.py                  # Environment settings
├── models.py                  # Pydantic models
├── handlers/resources.py      # MCP resources
└── utils/                     # Logging, validation utilities
scripts/
├── run_server.py              # Server startup
├── test_mvp.py                # MVP validation
├── deploy.sh                  # Docker deployment
└── run_http_server_with_status.py  # Docker CMD entry point
```

## Environment Configuration

Required in `.env`:
```env
OPENPROJECT_URL=http://localhost:8080
OPENPROJECT_API_KEY=your_40_character_api_key
MCP_HOST=localhost            # Use 0.0.0.0 for Docker
MCP_PORT=8080
MCP_LOG_LEVEL=INFO
```

## Key Technical Details

- **OpenProject API**: v3, HAL+JSON format, Basic Auth with API keys
- **Python**: 3.8+ required, 3.11 used in Docker
- **FastMCP**: >=0.9.0 for MCP implementation
- **Port 39127**: Recommended MCP port (Docker maps 39127:8080)
- **Python 3.9 compatible version**: `src/mcp_server_compatible.py`

## MCP Integration

Two integration methods for Claude Desktop:

1. **Local Python**: Configure `claude_desktop_config.json` to run `scripts/run_server.py`
2. **Docker SSE**: Use `http://localhost:39127/sse` transport URL

## Active Technologies
- Python 3.8+ (3.11 recommended) + FastMCP >= 0.9.0, httpx, Pydantic (001-get-work-package)
- N/A (read-only from OpenProject API) (001-get-work-package)

## Recent Changes
- 001-get-work-package: Added Python 3.8+ (3.11 recommended) + FastMCP >= 0.9.0, httpx, Pydantic
