"""Isolated execution of an approved existing Python interface, without HTTP sockets."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode

from .gateway import contract


async def dispatch(envelope, app=None, *, raise_app_exceptions=False):
    import httpx

    rule = contract(envelope["method"], envelope["path"])
    if rule is None:
        raise ValueError("Unapproved route")
    if envelope["path"] in {
        "intelligence/devigged-odds",
        "intelligence/ev-bets",
        "intelligence/arbitrage",
    }:
        from .intelligence_views import read

        return await asyncio.to_thread(read, envelope)
    if envelope["path"] == "intelligence/refresh":
        await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "etl.compute_intelligence"],
            check=True,
            timeout=210,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return {
            "status": 200,
            "body": {
                "success": True,
                "message": "Intelligence data refreshed successfully",
            },
        }
    if app is None:
        from api.main import app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=app, raise_app_exceptions=raise_app_exceptions
        ),
        base_url="http://private-pipeline",
    ) as client:
        response = await client.request(
            envelope["method"],
            "/api/v1/"
            + envelope["path"]
            + (
                "?" + urlencode([tuple(pair) for pair in envelope["query"]])
                if envelope["query"]
                else ""
            ),
            content=b""
            if envelope["body"] is None
            else json.dumps(envelope["body"], allow_nan=False).encode(),
            headers={
                "Content-Type": "application/json",
                "X-Internal-Token": os.getenv("PIPELINE_INTERNAL_TOKEN", ""),
            },
        )
        if response.status_code >= 500 or len(response.content) > 8 * 1024 * 1024:
            raise ValueError("Unpublishable upstream response")
        return {"status": response.status_code, "body": response.json()}


if __name__ == "__main__":
    envelope = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = asyncio.run(dispatch(envelope))
    Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False), encoding="utf-8")
