"""Archive measured gateway samples; never converts local results to hosted claims."""

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".release/gateway-verification"
OUTPUT = ROOT / "stages/03-build/output/durable-gateway-20261027"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    for name in ("performance-baseline.json", "performance.json"):
        source = SOURCE / name
        value = json.loads(source.read_text(encoding="utf-8"))
        value.update(
            recorded_at_utc=datetime.fromtimestamp(
                source.stat().st_mtime, UTC
            ).isoformat(),
            rust_profile="debug",
            http_workers_per_process=1,
            database_pool_max_per_process=3,
            client="Python urllib; HTTP and JSON parsing included",
        )
        (OUTPUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        records.append(value)
    marker = "## Local gateway measurements — 2026-10-27"
    document = ROOT / "docs/performance-report.md"
    content = document.read_text(encoding="utf-8").split(marker)[0].rstrip()
    content = content.replace(
        "| API p50/p95/p99 | Not measured | Not measured | Representative auth/read endpoint workload, concurrency, sample count, error rate and dataset size |",
        "| API p50/p95/p99 | Local debug baseline | Local debug repeat | See dated measurements below; release/hosted results remain pending |",
    )
    content = content.replace(
        "| Query latency / plans | Not measured | Not measured | Read-only EXPLAIN (ANALYZE, BUFFERS), warm/cold distinction and actual row counts |",
        "| Query latency / plans | Local point lookup | Local actual reader query | Raw EXPLAIN (ANALYZE, BUFFERS) included in dated evidence; hosted plans pending |",
    )
    lines = [
        marker,
        "",
        "Windows loopback PostgreSQL; 1,000 captured local fixture rows and synthetic contract quotes.",
        "Rust debug binaries, one HTTP worker and at most three database connections per API process.",
        "The worker was stopped during cached reads. Source data was read only; test accounts and",
        "publications existed in a newly created disposable database. No Neon or Vercel load ran.",
        "",
        "| Run | API processes | Concurrency | Samples | Errors | p50 ms | p95 ms | p99 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, record in zip(("Queue-path baseline", "Cached-read repeat"), records):
        for row in record["workloads"]:
            lines.append(
                f"| {label} | {row['api_processes']} | {row['concurrency']} | {row['samples']} | {row['errors']} | {row['p50_ms']:.2f} | {row['p95_ms']:.2f} | {row['p99_ms']:.2f} |"
            )
    lines.extend(
        [
            "",
            "The repeat uses a single approved-source SELECT for completed reads, avoiding the",
            "queue transaction and stream lock. These runs were not a controlled host-load experiment;",
            "other verification work ran concurrently and latency varied. No reliable speedup, release",
            "latency budget or production throughput is inferred. Percentiles use nearest rank; the",
            "40-sample p99 is its maximum. Samples are stored sorted, with query plans and role-test results.",
            "",
            "The baseline plan measures the publication point lookup. The repeat plan measures the",
            "actual cache reader with enabled-source, completed-state and freshness predicates.",
            "",
            "[Repeated samples and query plan](../stages/03-build/output/durable-gateway-20261027/performance.json),",
            "[baseline samples](../stages/03-build/output/durable-gateway-20261027/performance-baseline.json).",
            "Vercel cold starts, verified Neon TLS/role transport, release-build concurrency and full",
            "ingestion/inference/simulation throughput are separate unmeasured rollout gates.",
        ]
    )
    document.write_text(content + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "archived": str(OUTPUT),
                "samples_per_run": sum(r["samples"] for r in records[-1]["workloads"]),
            }
        )
    )


if __name__ == "__main__":
    main()
