# SpecPilot

SpecPilot is an interactive CLI developer tool for OpenAPI-driven API automation and inspection.

## Overview

SpecPilot parses OpenAPI 3.x specifications to discover endpoints, parameters, request/response models, and security definitions, dynamically converts API operations into Model Context Protocol (MCP) tools, and provides CLI commands for inspection and tool execution.

## Current Status

SpecPilot is in active development (`v0.2.0-dev`). Specification loading, OpenAPI normalization, MCP tool generation, HTTP execution, and interactive inspection commands in `specpilot shell` are fully implemented.

## Features

- Parse OpenAPI 3.x specifications (JSON and YAML).
- Load specifications from local file paths and remote HTTP/HTTPS URLs with timeout handling.
- Resolve local `$ref` pointers (e.g. `#/components/schemas/...`, `#/components/parameters/...`).
- Normalize operations, parameters, request bodies, responses, tags, servers, and security definitions into typed Pydantic models.
- Dynamic conversion of OpenAPI operations into callable Model Context Protocol (MCP) tools.
- Automatic tool input JSON Schema generation covering path, query, header parameters, and JSON request bodies.
- HTTP tool execution engine supporting path substitution, query parameters, header mapping, body serialization, and secret redaction.
- Persistent interactive REPL shell (`specpilot shell`) supporting `/use`, `/api`, `/tools [tag]`, `/inspect <tool>`, `/call`, `/verbose`, `/history`, and `/help` with tab-autocompletion.
- Terminal CLI inspection via `specpilot import`, `specpilot endpoints`, `specpilot tools`, `specpilot inspect <tool-name>`, and `specpilot call <tool-name>`.
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

# List dynamically generated MCP tools
specpilot tools ./tests/fixtures/sample_3_0.yaml

# Inspect detailed input schema for a tool
specpilot inspect list_pets ./tests/fixtures/sample_3_0.yaml
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

# List generated MCP tools
specpilot tools ./openapi.yaml

# Inspect tool schema and metadata
specpilot inspect get_pet ./openapi.yaml

# Manually invoke an MCP tool against the target API
specpilot call list_pets ./openapi.yaml --json '{"limit": 10}'
```

## Architecture

```text
+--------------------------------------------------------+
|                      SpecPilot CLI                     |
|         (import, endpoints, tools, inspect, call)      |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                   MCP Tool Registry                    |
|        (Dynamic Tool Conversion & Schema Gen)          |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                    HTTP Tool Executor                  |
|    (Path Substitution, Query, Headers, Body, Secrets)  |
+--------------------------------------------------------+
```

## Supported OpenAPI Features

- OpenAPI 3.0.x and 3.1.x specifications.
- Local `$ref` pointers (e.g. `#/components/schemas/...`, `#/components/parameters/...`, `#/components/requestBodies/...`).
- Standard HTTP methods: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`, `HEAD`.

## Known Limitations

- Remote `$ref` resolution across external URLs is not yet supported.
- LLM autonomous tool selection and multi-step agent flows will be introduced in upcoming releases.

## Development

Run unit tests:

```bash
uv run pytest
```

## Roadmap

- **OpenAPI Core**: OpenAPI specification loading and normalization (`v0.1.0`)
- **Dynamic MCP Tools**: Dynamic OpenAPI to MCP tool conversion and HTTP execution (`v0.2.0`)
- **Agent Workflows**: Multi-step tool execution and LLM orchestration (`v0.3.0`)
- **Safety System**: Side-effect protection and human approval (`v0.4.0`)
- **Contract Testing**: API contract validation (`v0.5.0`)
- **CLI Shell**: Interactive shell (`v0.6.0`)
- **Production Release**: General availability (`v1.0.0`)

## Version

Current version: `0.2.0`
