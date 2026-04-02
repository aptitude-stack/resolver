"""Typed metadata for the Aptitude CLI surface."""

from __future__ import annotations

from dataclasses import dataclass

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.text import Text


@dataclass(frozen=True)
class CliTheme:
    """Visual tokens for the wizard-first CLI."""

    text_primary: str = "bold white"
    text_body: str = "white"
    text_muted: str = "grey70"
    text_subtle: str = "grey50"
    text_detail: str = "grey82"
    border_primary: str = "grey27"
    border_secondary: str = "grey35"
    accent: str = "#8fa3ad"


@dataclass(frozen=True)
class OptionSurface:
    """One documented CLI flag."""

    key: str
    signature: str
    brief: str
    help_text: str


@dataclass(frozen=True)
class OptionGroup:
    """One group of options used in help output."""

    title: str
    option_keys: tuple[str, ...]
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommandSurface:
    """One documented CLI command."""

    name: str
    audience: str
    summary: str
    usage: str
    description: str | None = None
    flow_title: str | None = None
    flow_steps: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    option_groups: tuple[OptionGroup, ...] = ()
    note_lines: tuple[str, ...] = ()


THEME = CliTheme()
HORIZONTAL_SEPARATOR = "─" * 140

OPTIONS = {
    "version_select": OptionSurface(
        key="version_select",
        signature="--version TEXT",
        brief="optional exact immutable version",
        help_text=(
            "Optional exact immutable version. When omitted, the client selects "
            "a version deterministically."
        ),
    ),
    "select_slug": OptionSurface(
        key="select_slug",
        signature="--select-slug TEXT",
        brief="bypasses ambiguity by choosing one discovered candidate",
        help_text="Explicitly pick one discovered slug without prompting.",
    ),
    "prefer": OptionSurface(
        key="prefer",
        signature="--prefer TEXT",
        brief="ranks legal candidates with balanced, low-cost, or high-trust",
        help_text=(
            "Selection profile for choosing among legal candidates: balanced, "
            "low-cost, or high-trust."
        ),
    ),
    "interaction_mode": OptionSurface(
        key="interaction_mode",
        signature="--interaction-mode TEXT",
        brief="controls root ambiguity: auto, always, or never",
        help_text="How root ambiguity should be handled: auto, always, or never.",
    ),
    "allow_trust": OptionSurface(
        key="allow_trust",
        signature="--allow-trust TEXT",
        brief="restricts allowed trust tiers for fresh planning",
        help_text="Comma-separated allowed trust tiers for fresh planning.",
    ),
    "allow_lifecycle": OptionSurface(
        key="allow_lifecycle",
        signature="--allow-lifecycle TEXT",
        brief="restricts allowed lifecycle statuses for fresh planning",
        help_text=("Comma-separated allowed lifecycle statuses for fresh planning."),
    ),
    "max_tokens": OptionSurface(
        key="max_tokens",
        signature="--max-tokens INTEGER",
        brief="rejects skills above a token ceiling",
        help_text="Reject candidates and resolved graphs above this token ceiling.",
    ),
    "max_content_size": OptionSurface(
        key="max_content_size",
        signature="--max-content-size INTEGER",
        brief="rejects skills above a content-size ceiling",
        help_text=(
            "Reject candidates and resolved graphs above this content-size "
            "ceiling in bytes."
        ),
    ),
    "install_target": OptionSurface(
        key="install_target",
        signature="--target PATH",
        brief="materialization target directory",
        help_text="Local directory where the resolved graph should be materialized.",
    ),
    "install_json": OptionSurface(
        key="install_json",
        signature="--json",
        brief="structured machine-readable result",
        help_text="Print the structured JSON install result for automation and CI.",
    ),
    "sync_target": OptionSurface(
        key="sync_target",
        signature="--target PATH",
        brief="materialization target directory",
        help_text="Local directory where the locked system should be materialized.",
    ),
    "sync_json": OptionSurface(
        key="sync_json",
        signature="--json",
        brief="structured machine-readable result",
        help_text="Print the structured JSON sync result for automation and CI.",
    ),
    "lock": OptionSurface(
        key="lock",
        signature="--lock PATH",
        brief="path to an existing resolver lockfile",
        help_text="Path to an existing resolver lockfile.",
    ),
    "root_version": OptionSurface(
        key="root_version",
        signature="--version",
        brief="show the installed Aptitude version",
        help_text="Show the Aptitude version and exit.",
    ),
    "help": OptionSurface(
        key="help",
        signature="--help",
        brief="show help and exit",
        help_text="Show this message and exit.",
    ),
    "install_completion": OptionSurface(
        key="install_completion",
        signature="--install-completion",
        brief="install shell completion for the current shell",
        help_text="Install completion for the current shell.",
    ),
    "show_completion": OptionSurface(
        key="show_completion",
        signature="--show-completion",
        brief="print shell completion for manual install/customization",
        help_text=(
            "Show completion for the current shell, to copy it or customize "
            "the installation."
        ),
    ),
}

PLANNING_OPTION_KEYS = (
    "version_select",
    "select_slug",
    "prefer",
    "interaction_mode",
    "allow_trust",
    "allow_lifecycle",
    "max_tokens",
    "max_content_size",
)

COMMANDS = {
    "install": CommandSurface(
        name="install",
        audience="public",
        summary="fresh planning from a query and local materialization",
        usage='aptitude install "query"',
        description="Install a skill query into a local demo workspace.",
        flow_title="Fresh planning flow",
        flow_steps=(
            "discovery",
            "resolver",
            "governance",
            "lockfile",
            "execution",
        ),
        examples=(
            'aptitude install "Postman Primary Skill"',
            'aptitude install "Postman" --interaction-mode always',
            'aptitude install "Postman Primary Skill" --prefer low-cost',
            'aptitude install "Postman Primary Skill" --json',
        ),
        option_groups=(
            OptionGroup(
                title="Selection behavior",
                option_keys=("select_slug", "prefer", "interaction_mode"),
            ),
            OptionGroup(
                title="Policy behavior",
                option_keys=(
                    "allow_trust",
                    "allow_lifecycle",
                    "max_tokens",
                    "max_content_size",
                ),
            ),
            OptionGroup(
                title="Output behavior",
                option_keys=("install_target", "install_json"),
                lines=(
                    "default   human-friendly install summary",
                    "--json    structured machine-readable result",
                ),
            ),
        ),
    ),
    "sync": CommandSurface(
        name="sync",
        audience="public",
        summary="replay and materialize from an existing lockfile",
        usage="aptitude sync --lock aptitude.lock.json",
        description="Materialize a locked system from an existing lockfile.",
        flow_title="Lock replay path",
        flow_steps=(
            "lock parse + replay",
            "execution planning",
            "materialization",
        ),
        examples=(
            "aptitude sync --lock aptitude.lock.json",
            "aptitude sync --lock aptitude.lock.json --target demo_postman",
            "aptitude sync --lock aptitude.lock.json --json",
        ),
        note_lines=(
            "uses the existing lockfile as the source of truth",
            "does not call discovery or resolver",
            "rebuilds the local workspace from locked data only",
        ),
    ),
    "manifest": CommandSurface(
        name="manifest",
        audience="public",
        summary="inspect the complete Aptitude CLI capability map",
        usage="aptitude manifest",
        description="Show the complete Aptitude CLI capability map.",
        note_lines=(
            "shows public commands, advanced/internal commands, and global/framework flags",
            "lists every supported command and flag the app exposes",
        ),
    ),
    "resolve": CommandSurface(
        name="resolve",
        audience="advanced/internal",
        summary="preview/debug fresh planning without materialization",
        usage='aptitude resolve "query"',
        description="Resolve a skill query and print a stable JSON result.",
        flow_title="Fresh planning flow",
        flow_steps=(
            "discovery",
            "resolver",
            "governance",
            "lockfile",
            "execution planning",
        ),
        examples=(
            'aptitude resolve "Postman Primary Skill"',
            'aptitude resolve "Postman" --interaction-mode never',
            'aptitude resolve "Postman Primary Skill" --prefer high-trust',
            'aptitude resolve "Postman Primary Skill" --allow-trust verified,internal',
        ),
        note_lines=(
            "This is the hidden preview/debug surface. It follows the same planning path as install,",
            "but stops after planning and prints the result instead of materializing it.",
        ),
    ),
}


def _render_brief(signature: str, brief: str) -> str:
    return f"{signature:<22} {brief}"


def build_root_help() -> str:
    """Render the root help summary from the catalog."""

    public_commands = (
        COMMANDS["install"],
        COMMANDS["sync"],
        COMMANDS["manifest"],
    )
    lines = [
        "Aptitude.",
        "",
        "Deterministic resolver for discovering, resolving, locking, and materializing AI skills.",
        "",
        "Public commands:",
    ]
    lines.extend(
        f"  {command.name:<8} {command.summary}" for command in public_commands
    )
    lines.extend(
        [
            "",
            "Required environment:",
            "  APTITUDE_SERVER_BASE_URL   registry base URL",
            "  APTITUDE_READ_TOKEN        registry read token",
            "",
            "Examples:",
            '  aptitude install "Postman Primary Skill"',
            '  aptitude install "Postman" --interaction-mode always',
            '  aptitude install "Postman Primary Skill" --prefer low-cost',
            "  aptitude sync --lock aptitude.lock.json",
            "  aptitude manifest",
            "",
            "Use `install --help` or `sync --help` for command-specific options, or `manifest` for the full surface.",
        ]
    )
    return "\n".join(lines)


def build_command_help(command_name: str) -> str:
    """Render one command help description from the catalog."""

    command = COMMANDS[command_name]
    lines = [command.description or (command.summary.capitalize() + ".")]

    if command.flow_title is not None:
        lines.extend(
            [
                "",
                f"{command.flow_title}:",
                f"  {' -> '.join(command.flow_steps)}",
            ]
        )

    if command.examples:
        lines.extend(["", "Common examples:"])
        lines.extend(f"  {example}" for example in command.examples)

    for option_group in command.option_groups:
        lines.extend(["", f"{option_group.title}:"])
        if option_group.option_keys:
            lines.extend(
                f"  {_render_brief(OPTIONS[key].signature, OPTIONS[key].brief)}"
                for key in option_group.option_keys
            )
        lines.extend(f"  {line}" for line in option_group.lines)

    if command.note_lines:
        title = "Behavior" if command_name == "sync" else None
        if title is not None:
            lines.extend(["", f"{title}:"])
        else:
            lines.append("")
        lines.extend(f"  {line}" for line in command.note_lines)

    return "\n".join(lines)


def build_manifest_text() -> str:
    """Render the human-readable capability map."""

    public_commands = (
        COMMANDS["install"],
        COMMANDS["sync"],
        COMMANDS["manifest"],
    )
    advanced_commands = (COMMANDS["resolve"],)
    global_flags = (
        OPTIONS["root_version"],
        OPTIONS["help"],
        OPTIONS["install_completion"],
        OPTIONS["show_completion"],
    )

    lines = [
        "Aptitude CLI capability map.",
        HORIZONTAL_SEPARATOR,
        "",
        "Public Commands",
        HORIZONTAL_SEPARATOR,
    ]
    for command in public_commands:
        lines.append(f"  {command.name:<8} {command.usage}")
        lines.append(f"           {command.summary}")
        option_keys = _manifest_option_keys(command.name)
        if option_keys:
            lines.append(
                "           flags: "
                + ", ".join(OPTIONS[key].signature for key in option_keys)
            )
    lines.extend(
        ["", HORIZONTAL_SEPARATOR, "Advanced/Internal Commands", HORIZONTAL_SEPARATOR]
    )
    for command in advanced_commands:
        lines.append(f"  {command.name:<8} {command.usage}")
        lines.append(f"           {command.summary}")
        lines.append(
            "           flags: "
            + ", ".join(
                OPTIONS[key].signature for key in _manifest_option_keys(command.name)
            )
        )
    lines.extend(
        ["", HORIZONTAL_SEPARATOR, "Global / Framework Flags", HORIZONTAL_SEPARATOR]
    )
    lines.extend(f"  {option.signature:<22} {option.brief}" for option in global_flags)
    return "\n".join(lines)


def render_wizard_manifest_panel() -> Panel:
    """Render the compact wizard-facing capability summary."""

    install_option_signatures = (
        "--prefer balanced|low-cost|high-trust  --interaction-mode auto|always|never",
        "--select-slug slug  --allow-trust a,b  --allow-lifecycle a,b",
        "--max-tokens N  --max-content-size N  --target PATH  --json",
    )
    body = Group(
        Text("Public commands", style=THEME.text_subtle),
        Text('install  aptitude install "query" [flags]', style=THEME.text_primary),
        *[
            Text(f"  {line}", style=THEME.text_muted)
            for line in install_option_signatures
        ],
        Text(
            "sync     aptitude sync --lock aptitude.lock.json [--target PATH] [--json]",
            style=THEME.text_primary,
        ),
        Text(
            "manifest aptitude manifest",
            style=THEME.text_primary,
        ),
        Text(""),
        Text("Advanced/internal", style=THEME.text_subtle),
        Text(
            'resolve  aptitude resolve "query" [planning flags]',
            style=THEME.text_primary,
        ),
        Text(
            "  Advanced/internal preview flow. Plans only and prints stable JSON.",
            style=THEME.text_muted,
        ),
        Text(""),
        Text("Global / framework", style=THEME.text_subtle),
        Text(
            "--version",
            style=THEME.text_primary,
        ),
        Text(
            "--install-completion",
            style=THEME.text_primary,
        ),
        Text(
            "--show-completion",
            style=THEME.text_primary,
        ),
        Text(
            "  Shell/version helpers exposed by the Typer app runtime.",
            style=THEME.text_muted,
        ),
    )
    return Panel(
        body,
        title="Capability Map",
        border_style=THEME.border_primary,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def _manifest_option_keys(command_name: str) -> tuple[str, ...]:
    if command_name == "install":
        return PLANNING_OPTION_KEYS + ("install_target", "install_json")
    if command_name == "sync":
        return ("lock", "sync_target", "sync_json")
    if command_name == "resolve":
        return PLANNING_OPTION_KEYS
    return ()
