# Changelog

All notable changes to SpecPilot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-09-06

### Added
- Interactive REPL shell (`specpilot shell`) powered by `prompt_toolkit` and `rich`.
- Active specification session state (`SessionState`) for switching specs via `/use <location>` and inspecting metadata via `/api`.
- Interactive slash commands: `/help`, `/use`, `/api`, `/tools [tag]`, `/inspect <tool>`, `/call <tool> [json]`, `/history`, `/verbose [on|off]`, `/clear`, `/exit`.
- Dynamic autocompletion (`SpecPilotCompleter`) for slash commands, tags, and registered tool names.
- Automatic secret redaction for session history ensuring API keys and tokens are never stored.
- Verbose mode toggling to output spec, tool count, and HTTP execution metrics without exposing credentials.

## [0.2.0] - 2026-09-06

### Added
- Model Context Protocol (`mcp`) SDK integration for dynamically hosting and executing API tools.
- `ToolConverter` for converting normalized OpenAPI operations into typed MCP tools with clean, deterministic snake_case naming and collision resolution.
- Automatic JSON Schema generation for tool inputs, unifying path, query, header parameters, and JSON request bodies.
- `MCPToolRegistry` for managing converted tools and binding them to MCP server instances.
- `ToolExecutor` HTTP execution engine featuring URL path parameter substitution, query formatting, header mapping, body serialization, and sensitive header redaction.
- CLI inspection & execution commands: `specpilot tools <location>`, `specpilot inspect <tool-name> <location>`, and `specpilot call <tool-name> <location> --json '{...}'`.

## [0.1.0] - 2026-09-06

### Added
- Core `src/specpilot` package structure and console script entrypoint `specpilot`.
- Specification loader supporting local JSON/YAML files and remote HTTP/HTTPS URLs with timeout handling.
- OpenAPI 3.x parser normalizing operations, paths, HTTP methods, parameters, request bodies, responses, servers, tags, and security metadata.
- JSON Pointer reference resolver (`RefResolver`) for local `$ref` pointers (e.g. `#/components/schemas/...`).
- CLI inspection commands: `specpilot import <location>` and `specpilot endpoints <location>`.
- Automated test suite covering loading, reference resolution, parsing, and CLI workflows.
