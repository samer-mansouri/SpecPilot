# SpecPilot

SpecPilot is an interactive CLI developer tool for OpenAPI-driven API automation and inspection.

## Overview

SpecPilot parses OpenAPI 3.x specifications to discover endpoints, parameters, request/response models, and security definitions, providing CLI commands for specification analysis and inspection.

## Current Status

SpecPilot `v0.1.0` is released. OpenAPI 3.x loading, normalization, and CLI inspection commands (`import` and `endpoints`) are fully implemented and tested.

## Features

- Parse OpenAPI 3.x specifications (JSON and YAML).
- Load specifications from local file paths and remote HTTP/HTTPS URLs with timeout handling.
- Resolve local `$ref` pointers (e.g. `#/components/schemas/...`, `#/components/parameters/...`).
- Normalize operations, parameters, request bodies, responses, tags, servers, and security definitions into typed Pydantic models.
- Terminal CLI inspection via `specpilot import` and `specpilot endpoints`.
- Actionable error reporting for missing files, network failures, timeouts, malformed documents, and unresolvable references.

## Installation

Ensure Python 3.10+ and `uv` (or `pip`) are installed.

```bash
# Editable install using uv
uv pip install -e .

# Or using standard pip
pip install -e .
```

## Quick Start

```bash
# Inspect an OpenAPI specification summary
specpilot import ./tests/fixtures/sample_3_0.yaml

# List discovered endpoints and operations
specpilot endpoints ./tests/fixtures/sample_3_0.yaml
```

## CLI Usage

```bash
# Display help and available commands
specpilot --help

# Import local JSON or YAML specification
specpilot import ./openapi.json
specpilot import ./openapi.yaml

# Import remote OpenAPI specification over HTTP/HTTPS
specpilot import https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/petstore.json

# List endpoints table
specpilot endpoints ./openapi.yaml
```

## Architecture

```text
+--------------------------------------------------------+
|                      SpecPilot CLI                     |
|                (specpilot import/endpoints)            |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                    OpenAPI Loader                      |
|            (Local JSON/YAML & HTTP/HTTPS)              |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                    OpenAPI Parser                      |
|      (Normalization, Schema & $ref Resolution)         |
+--------------------------------------------------------+
```

## Supported OpenAPI Features

- OpenAPI 3.0.x and 3.1.x specifications.
- Local `$ref` pointers (e.g. `#/components/schemas/...`, `#/components/parameters/...`, `#/components/requestBodies/...`).
- Standard HTTP methods: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`, `HEAD`.

## Known Limitations

- Remote `$ref` resolution across external URLs is not yet supported (planned for future milestones).
- Dynamic MCP Tool generation and LLM execution will be introduced in Milestone 2.

## Development

Run unit tests:

```bash
uv run pytest
```

## Roadmap

- **Milestone 1**: OpenAPI Core foundation (v0.1.0)
- **Milestone 2**: Dynamic MCP Tools (v0.2.0)
- **Milestone 3**: Agentic Workflows & Multi-Step Execution (v0.3.0)
- **Milestone 4**: Safety & Human Approval (v0.4.0)
- **Milestone 5**: Contract & API Testing (v0.5.0)
- **Milestone 6**: CLI Polish & Interactive Shell (v0.6.0)
- **Milestone 7**: Production Packaging & 1.0 Release (v1.0.0)

## Version

Current version: `0.1.0`
