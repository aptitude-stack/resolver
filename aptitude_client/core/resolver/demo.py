"""Minimal end-to-end resolver demo using the in-memory manifest provider."""

import argparse
import sys
from pathlib import Path

from aptitude_client.core.graph import (
    find_graph_node_by_name,
    render_dependency_tree,
    write_graph_dot,
)
from aptitude_client.core.resolver.in_memory_provider import (
    InMemoryManifestProvider,
    build_mvp_sample_manifests,
)
from aptitude_client.core.resolver.service import DependencyResolver


def run_demo(dot_out: str = "") -> None:
    """Run a tiny local resolution scenario for MVP verification."""
    _enable_utf8_output()

    provider = InMemoryManifestProvider(build_mvp_sample_manifests())
    resolver = DependencyResolver()
    root_skill = "assistant-suite"
    result = resolver.resolve_skill(skill_name=root_skill, provider=provider)
    root_node = find_graph_node_by_name(result.graph, root_skill)

    print(f"Resolve target: {root_skill}")
    print("Dependency tree:")
    if root_node is not None:
        print(render_dependency_tree(result.graph, root_node))
    else:
        print(f"{root_skill} (missing)")
    print("Install order:", [node.key for node in result.install_order])
    print("Missing dependencies:", [item.name for item in result.missing_dependencies])
    print("Cycles detected:", len(result.cycles))
    if result.notes:
        print("Notes:", result.notes)

    if dot_out and root_node is not None:
        output_path = _normalize_dot_path(dot_out)
        write_graph_dot(result.graph, output_path=output_path, root_node=root_node)
        print(f"DOT file written: {output_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local dependency resolver demo.")
    parser.add_argument(
        "--dot-out",
        default="docs/graphs/resolver-demo.dot",
        help="Output path for Graphviz DOT export. Bare filenames are placed under docs/graphs/.",
    )
    return parser.parse_args()


def _enable_utf8_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def _normalize_dot_path(dot_out: str) -> str:
    path = Path(dot_out)
    if path.parent == Path("."):
        return str(Path("docs/graphs") / path.name)
    return str(path)


if __name__ == "__main__":
    args = _parse_args()
    run_demo(dot_out=args.dot_out)
