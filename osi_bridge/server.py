"""OSI Bridge MCP server.

Loads an OSI YAML model and exposes three MCP tools that Gemini consumes:
  - list_metrics
  - list_dimensions
  - query_metric

Backend: Databricks SQL warehouse, queried via databricks-sql-connector.
"""
from __future__ import annotations

import argparse
import os
from typing import Any

import yaml
from databricks import sql
from dotenv import load_dotenv
from fastmcp import FastMCP

from osi_bridge.translator import build_sql

load_dotenv(override=True)

mcp = FastMCP("osi-bridge")
_MODEL: dict[str, Any] = {}


def _load(path: str) -> None:
    with open(path) as f:
        _MODEL.update(yaml.safe_load(f))
    n = len(_MODEL["semantic_model"][0]["metrics"])
    print(f"[OSI Bridge] Loaded {n} metrics from {path}")


def _run_sql(sql_text: str) -> list[dict[str, Any]]:
    host = os.environ["DATABRICKS_HOST"].replace("https://", "")
    http_path = os.environ["DATABRICKS_HTTP_PATH"]
    token = os.environ["DATABRICKS_TOKEN"]
    with sql.connect(server_hostname=host, http_path=http_path, access_token=token) as c:
        with c.cursor() as cur:
            cur.execute(sql_text)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def list_metrics() -> list[dict[str, Any]]:
    """List all metrics in the OSI model with name, description, and synonyms."""
    return [
        {
            "name": m["name"],
            "description": m.get("description"),
            "synonyms": m.get("ai_context", {}).get("synonyms", []),
        }
        for m in _MODEL["semantic_model"][0]["metrics"]
    ]


@mcp.tool()
def list_dimensions(metric: str | None = None) -> list[dict[str, Any]]:
    """List dimensions available for slicing. `metric` arg currently informational only."""
    fields = _MODEL["semantic_model"][0]["datasets"][0]["fields"]
    return [
        {
            "name": f["name"],
            "is_time": f.get("dimension", {}).get("is_time", False),
            "synonyms": f.get("ai_context", {}).get("synonyms", []),
            "description": f.get("description"),
        }
        for f in fields
    ]


@mcp.tool()
def query_metric(
    metric: str,
    dimensions: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    time_grain: str | None = None,
    limit: int = 1000,
) -> dict[str, Any]:
    """
    Query a metric with optional dimensions, filters, and time grain.

    Args:
        metric: metric name from list_metrics()
        dimensions: dimension names from list_dimensions()
        filters: list of {column, op, value}
        time_grain: 'day' | 'week' | 'month' | 'quarter' | 'year'
        limit: row cap (default 1000)
    """
    sql_text = build_sql(
        osi_model=_MODEL,
        metrics=[metric],
        dimensions=dimensions or [],
        filters=filters or [],
        time_grain=time_grain,
        limit=limit,
    )
    rows = _run_sql(sql_text)
    return {"sql": sql_text, "rows": rows, "row_count": len(rows)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--osi-model", default=os.environ.get("OSI_MODEL_PATH", "examples/model.osi.yaml"))
    p.add_argument("--transport", default="sse", choices=["sse", "stdio"])
    p.add_argument("--host", default=os.environ.get("OSI_BRIDGE_HOST", "0.0.0.0"))
    p.add_argument("--port", type=int, default=int(os.environ.get("OSI_BRIDGE_PORT", 8000)))
    args = p.parse_args()

    _load(args.osi_model)
    if args.transport == "sse":
        print(f"[OSI Bridge] MCP server listening on http://{args.host}:{args.port}/sse")
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
