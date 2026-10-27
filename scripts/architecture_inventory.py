"""Generate source inventories without importing applications or reading secrets."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def generate() -> None:
    lines = [
        "# API and source inventory",
        "",
        "Generated from the working tree by `py -3 scripts/architecture_inventory.py`.",
        "This is static registration evidence, not proof of reachable deployed routes.",
        "Rust paths below are registration fragments: compose scopes from `main.rs`",
        "and the domain configure functions. Commented-out routes are excluded.",
        "",
        "## Rust registration sites",
        "",
        "| File:line | Registration |",
        "|---|---|",
    ]
    rust_paths = sorted((ROOT / "backend/src").rglob("*.rs"))
    for path in rust_paths:
        source = path.read_text(encoding="utf-8-sig")
        # Remove line comments before collecting multiline route/scope calls.
        source = re.sub(r"//[^\n]*", lambda m: " " * len(m[0]), source)
        for match in re.finditer(
            r'(?:web::scope|\.route)\s*\(\s*"([^"]*)"(?:\s*,\s*web::(\w+)\(\)\.to\(([^)]+)\))?',
            source,
        ):
            line = source.count("\n", 0, match.start()) + 1
            method = match[2].upper() if match[2] else "SCOPE / see source"
            handler = match[3] or ""
            lines.append(
                f"| `{relative(path)}:{line}` | `{method} {match[1]} {handler}` |"
            )
    lines += [
        "",
        "## Python route declarations",
        "",
        "All domain routes receive `/api/v1` in `api/main.py`; browser access",
        "currently uses the Rust `/api/v1/pipeline` prefix.",
        "",
        "| Method | Path | Handler | Source | Classification |",
        "|---|---|---|---|---|",
    ]
    for path in sorted((ROOT / "pipeline/api/routers").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        prefix = ""
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                for keyword in node.value.keywords:
                    if keyword.arg == "prefix" and isinstance(
                        keyword.value, ast.Constant
                    ):
                        prefix = keyword.value.value
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(
                    decorator.func, ast.Attribute
                ):
                    continue
                method = decorator.func.attr
                if (
                    method not in ("get", "post", "put", "delete", "patch")
                    or not decorator.args
                ):
                    continue
                route = prefix + ast.literal_eval(decorator.args[0])
                classification = "published read / Rust migration"
                if any(
                    word in route
                    for word in (
                        "refresh",
                        "run-pipeline",
                        "update-",
                        "validate-data",
                        "backtest",
                    )
                ):
                    classification = "local operational tooling; preserve internally"
                elif method != "get" or route == "/predict-matchup":
                    classification = "request computation; port supported rules or use published outputs"
                lines.append(
                    f"| {method.upper()} | `{route}` | `{node.name}` | `{relative(path)}:{node.lineno}` | {classification} |"
                )
    lines += [
        "",
        "## Rust module / handler / middleware inventory",
        "",
        "| Source | Public functions and services |",
        "|---|---|",
    ]
    for path in rust_paths:
        source = path.read_text(encoding="utf-8-sig")
        symbols = re.findall(
            r"pub(?:\([^)]*\))?\s+(?:async\s+)?(?:fn|struct|enum|trait)\s+(\w+)", source
        )
        lines.append(
            f"| `{relative(path)}` | {', '.join(f'`{symbol}`' for symbol in symbols)} |"
        )
    (ROOT / "docs/api-inventory.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    lines = [
        "# Source schema inventory",
        "",
        "Static declarations, not a live catalog. Repeated table declarations and",
        "later ALTER statements must be interpreted in migration order.",
        "",
        "## Versioned SQL",
        "",
    ]
    paths = sorted((ROOT / "backend/migrations").glob("*.sql"))
    paths += [ROOT / "pipeline/schema.sql"] + sorted(
        (ROOT / "pipeline/migrations").glob("*.sql")
    )
    for path in paths:
        source = path.read_text(encoding="utf-8-sig")
        # Only DDL lines: deliberately exclude seed INSERTs and their payloads.
        ddl = [
            line.strip()
            for line in source.splitlines()
            if re.match(
                r"\s*(?:CREATE (?:UNIQUE )?(?:TABLE|INDEX)|ALTER TABLE|REFERENCES|FOREIGN KEY|CHECK\s*\()",
                line,
                re.IGNORECASE,
            )
        ]
        lines += [f"### `{relative(path)}`", "", "```sql", *ddl, "```", ""]
    lines += ["## Python-managed schema declarations", "", "```text"]
    for path in sorted((ROOT / "pipeline").rglob("*.py")):
        if any(
            part.startswith(".") or part in ("__pycache__", "data", "model_store")
            for part in path.relative_to(ROOT / "pipeline").parts
        ):
            continue
        source = path.read_text(encoding="utf-8-sig")
        for match in re.finditer(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z_0-9.]*)",
            source,
            re.IGNORECASE,
        ):
            lines.append(
                f"{relative(path)}:{source.count(chr(10), 0, match.start()) + 1} {match[1]}"
            )
    lines += ["```", ""]
    (ROOT / "docs/schema-inventory.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    generate()
