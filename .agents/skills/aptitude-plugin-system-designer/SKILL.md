---
name: aptitude-plugin-system-designer
description: Design Aptitude’s plugin architecture with explicit stage-based pluggy hooks and safe isolation from core orchestration. Use when defining hook specs, plugin lifecycle stages, and deterministic plugin execution.
---
# Aptitude Plugin System Designer

## Purpose
Design and implement the Aptitude client plugin architecture inspired by extensible build/package systems such as Maven.

## Responsibilities
- Define plugin hook points.
- Keep plugins isolated from core orchestration logic.
- Support built-in and future third-party plugins.
- Ensure plugins can inspect plans and results safely.

## Technical Rules
- Use pluggy.
- Hooks must be explicit and stage-based.
- Plugins should not directly mutate unrelated internal state.
- Prefer structured inputs/outputs over side-effect-heavy hooks.

## Required Hook Stages
- pre_resolve
- post_resolve
- pre_install
- post_install
- pre_activate
- emit_report

## Example Plugin Types
- token cost analyzer
- security scan plugin
- compatibility validator
- score enricher
- manifest linter

## Definition of Done
Plugin work is complete only if:
- hook specs are clear
- at least one example plugin exists
- plugin execution is deterministic
- plugin errors are surfaced safely