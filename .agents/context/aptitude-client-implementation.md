# Aptitude Client Implementation Guide

## Project Summary
Aptitude is a package manager for AI skills, inspired by pip, npm, and Maven.
Instead of traditional software libraries, it manages AI skills as versioned, reusable, dependency-aware artifacts.

## Engineering Goal
Build the first version of the Aptitude Client as a modular Python system that can:
- search skills
- inspect skills
- resolve dependencies
- install skills
- prepare for plugin-based pipeline extensions

## Architecture Constraints
- Python only
- Typer for CLI
- Pydantic for models
- httpx for registry communication
- resolvelib for dependency/version resolution
- networkx for dependency graph construction and analysis
- pluggy for plugin hooks
- thin CLI, core logic in services/modules
- implement one phase at a time
- do not implement future phases unless explicitly requested

## Project Structure
aptitude_client/
    cli/
    core/
        resolver/
        registry/
        installer/
        graph/
    models/
    plugins/
    cache/
    utils/

## Skill Manifest Schema
Fields:
- name
- version
- description
- author
- license
- dependencies
- runtime
- metrics
- security_score
- stars
- downloads

## Phase Plan

### Phase 1
Create project structure and CLI bootstrap.

### Phase 2
Implement Pydantic models, including SkillManifest and supporting models.

### Phase 3
Implement registry client with:
- GET /skills
- GET /skills/{name}
- GET /skills/{name}/{version}

### Phase 4
Implement dependency resolution using resolvelib and dependency graph construction using networkx.

### Phase 5
Implement installer:
- download skill artifacts
- verify metadata
- store in local cache at ~/.aptitude/skills

### Phase 6
Implement plugin system using pluggy with hooks:
- pre_resolve
- post_resolve
- pre_install
- post_install

### Phase 7
Implement example plugins:
- token_cost_plugin
- security_scan_plugin

### Phase 8
Implement logging and resolution reporting.

## Delivery Format
For each requested phase:
1. implement only that phase
2. list created/modified files
3. explain responsibilities
4. state what is intentionally not implemented yet
5. recommend the next phase