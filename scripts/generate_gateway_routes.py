"""Freeze reviewed gateway routes from source; new routes require a manifest update."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READ_POST = {
    "sport-models/preview",
    "fpl/team/evaluate",
    "parlay/enrich",
    "smart-assistant",
}
ADMIN_GET = {"predictions/backtest", "predictions/validate-data"}
WRITES = {
    "intelligence/devig",
    "intelligence/ev",
    "intelligence/ev/batch",
    "intelligence/arbitrage/scan",
}


def routes():
    result = []
    for path in sorted((ROOT / "pipeline/api/routers").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        prefix = ""
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and getattr(node.value.func, "id", None) == "APIRouter"
            ):
                prefix = next(
                    (
                        ast.literal_eval(k.value)
                        for k in node.value.keywords
                        if k.arg == "prefix"
                    ),
                    "",
                )
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(
                    decorator.func, ast.Attribute
                ):
                    continue
                method = decorator.func.attr.upper()
                if (
                    method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}
                    or not decorator.args
                ):
                    continue
                route = (prefix + ast.literal_eval(decorator.args[0])).strip("/")
                admin = route in ADMIN_GET or (
                    method != "GET" and route not in READ_POST and route not in WRITES
                )
                result.append(
                    {
                        "method": method,
                        "path": route,
                        "admin": admin,
                        "side_effect": admin or route in WRITES,
                        "ttl_seconds": 30
                        if route in {"best-value-bets", "suggested-parlays", "ai-picks"}
                        else 300,
                    }
                )
    result.append(
        {
            "method": "POST",
            "path": "intelligence/refresh",
            "admin": True,
            "side_effect": True,
            "ttl_seconds": 300,
        }
    )
    for path in (
        "intelligence/devigged-odds",
        "intelligence/ev-bets",
        "intelligence/arbitrage",
    ):
        result.append(
            {
                "method": "GET",
                "path": path,
                "admin": False,
                "side_effect": False,
                "ttl_seconds": 30,
            }
        )
    return sorted(result, key=lambda item: (item["path"], item["method"]))


if __name__ == "__main__":
    payload = json.dumps(routes(), indent=2) + "\n"
    for target in (
        ROOT / "pipeline/sync/gateway_routes.json",
        ROOT / "backend/contracts/gateway_routes.json",
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
