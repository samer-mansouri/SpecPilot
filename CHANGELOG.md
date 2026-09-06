# Changelog

All notable changes to SpecPilot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-06

### Added
- Core `src/specpilot` package structure and console script entrypoint `specpilot`.
- Specification loader supporting local JSON/YAML files and remote HTTP/HTTPS URLs with timeout handling.
- OpenAPI 3.x parser normalizing operations, paths, HTTP methods, parameters, request bodies, responses, servers, tags, and security metadata.
- JSON Pointer reference resolver (`RefResolver`) for local `$ref` pointers (e.g. `#/components/schemas/...`).
- CLI inspection commands: `specpilot import <location>` and `specpilot endpoints <location>`.
- Automated test suite covering loading, reference resolution, parsing, and CLI workflows.
