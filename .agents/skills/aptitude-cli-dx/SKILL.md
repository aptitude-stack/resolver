---
name: aptitude-cli-dx
description: Design and refine Aptitude CLI UX for clear commands, readable output, and recoverable error flows. Use when shaping command names, flags, terminal messaging, and install/resolve/inspect usability.
---

# Aptitude CLI DX

## Purpose
Design the Aptitude CLI experience to be intuitive, explainable, and consistent.

## Responsibilities
- Shape commands and flags.
- Improve discoverability and output readability.
- Ensure install/resolve/inspect flows are understandable.
- Keep command naming consistent with package-manager conventions.

## Core Commands
- apt search <query>
- apt inspect <skill>
- apt resolve <skill>
- apt install <skill>
- apt list
- apt remove <skill>

## UX Rules
- Prefer clear, short command names.
- Provide helpful error messages.
- Show resolution plans before destructive actions when appropriate.
- Keep output structured and readable.

## Definition of Done
CLI design work is complete only if:
- commands are consistent
- outputs are understandable
- errors help the user recover