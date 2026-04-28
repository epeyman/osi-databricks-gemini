# OSI ↔ Databricks ↔ Gemini Prototype

A working prototype that lets **Google Gemini** consume a **Databricks Unity Catalog Metric View** as an **Open Semantic Interchange (OSI v1.0)** model — without Cube in the middle.

```
Gemini (Databricks-hosted, OpenAI-compatible endpoint)
    │
    ▼  MCP / SSE
OSI Bridge (this repo, ~250 LOC Python)
    │
    ▼  databricks-sql-connector
Databricks SQL Warehouse
    └── Unity Catalog Metric View   ← source of truth
```

The bridge exports a Databricks Metric View to OSI v1.0 YAML and exposes three MCP tools (`list_metrics`, `list_dimensions`, `query_metric`) that Gemini calls automatically via a manual tool-calling loop.

## What's in this repo

| Path | Purpose |
|------|---------|
| `notebooks/01_create_metric_view.py` | Creates the demo Metric View on `samples.tpch.orders` (widget-driven) |
| `notebooks/02_export_to_osi.py` | Reads the Metric View and writes `model.osi.yaml` (widget-driven) |
| `notebooks/03_test_queries.py` | Sanity-check `MEASURE()` queries (widget-driven) |
| `osi_bridge/server.py` | The MCP server Gemini connects to |
| `osi_bridge/exporter.py` | Standalone Databricks Metric View → OSI YAML converter |
| `osi_bridge/translator.py` | OSI metric request → Databricks SQL with `MEASURE()` |
| `osi_bridge/agent_metadata.yaml` | Synonyms/display-names merged into the OSI export |
| `examples/gemini_client.py` | Minimal Gemini client (Databricks-hosted, MCP loop) |
| `examples/model.osi.yaml` | Sample OSI YAML output |
| `docs/ARCHITECTURE.md` | Diagrams and component responsibilities |
| `docs/DEMO_SCRIPT.md` | The 5-minute hackathon demo |
| `deploy/upload_to_workspace.sh` | Pushes notebooks into your Databricks workspace |

## Prerequisites

- Python 3.11+ (`python3 --version`)
- A Databricks workspace with Unity Catalog and a SQL warehouse
- The Databricks CLI configured with a profile pointing at your workspace
- Access to **Databricks Foundation Model APIs** (Gemini 2.5 Flash or Pro). No Google API key required.

## Step-by-step guide

### 1. Clone and install

```bash
git clone https://github.com/<your-fork>/osi-databricks-gemini.git
cd osi-databricks-gemini
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Authenticate to your Databricks workspace

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile <your-profile>
databricks current-user me --profile <your-profile>   # verify
```

### 3. Edit `.env`

Set at minimum:

| Variable | What to put |
|----------|-------------|
| `DATABRICKS_PROFILE` | the CLI profile name from step 2 |
| `DATABRICKS_HOST` | `https://<your-workspace>.cloud.databricks.com` |
| `DATABRICKS_HTTP_PATH` | the SQL warehouse path (`Compute → SQL Warehouses → your warehouse → Connection details → HTTP path`) |
| `DATABRICKS_TOKEN` | a PAT (`User Settings → Developer → Access tokens`) or any OAuth Bearer token |
| `OSI_CATALOG` | a catalog you have CREATE access to. Often `main`; on FEVM workspaces typically `<workspace>_catalog` |
| `OSI_SCHEMA` | default `osi_demo` is fine |
| `OSI_METRIC_VIEW` | default `orders_mv` is fine |
| `GEMINI_MODEL` | `databricks-gemini-2-5-flash` or `databricks-gemini-2-5-pro` |

### 4. Push notebooks to your workspace

```bash
bash deploy/upload_to_workspace.sh
```
Uploads the three notebooks to `/Users/<you>/osi-demo/`.

### 5. Create the Metric View

Open `01_create_metric_view` in your workspace and attach it to a serverless or all-purpose cluster. Set the widgets at the top to match your `OSI_CATALOG` / `OSI_SCHEMA` / `OSI_METRIC_VIEW`, then **Run All**. You should see five rows in the sanity query at the bottom (revenue by `order_priority`).

### 6. Export to OSI YAML

Two paths — pick one.

**6a. From your laptop (recommended for the bridge demo):**
```bash
python -m osi_bridge.exporter \
  --fqn "$OSI_CATALOG.$OSI_SCHEMA.$OSI_METRIC_VIEW" \
  --out examples/model.osi.yaml
```

**6b. From the workspace notebook:** open `02_export_to_osi`, set the widgets, **Run All**. Output lands at `/Workspace/Users/<you>/osi-demo/model.osi.yaml`.

### 7. Start the OSI Bridge MCP server

```bash
python -m osi_bridge.server --osi-model examples/model.osi.yaml
```
You should see:
```
[OSI Bridge] Loaded N metrics from examples/model.osi.yaml
[OSI Bridge] MCP server listening on http://localhost:8000/sse
```

### 8. Run the Gemini client

In another terminal (with `.venv` activated):
```bash
python examples/gemini_client.py "What was total revenue by order priority?"
```
You'll see the MCP tool calls Gemini issues, then a natural-language answer with concrete numbers.

### 9. (Stretch) Multi-vendor demo

Swap `examples/model.osi.yaml` for a Dremio- or Strategy-exported OSI YAML (with that vendor's `custom_extensions.<vendor>` block populated and the bridge's `query_metric` adapted) and re-run step 8. The agent answers identically. **OSI is the contract.**

## Architecture and demo script

- `docs/ARCHITECTURE.md` — components, why no Cube, vendor-swap pattern.
- `docs/DEMO_SCRIPT.md` — the five-minute panel walkthrough.

## Is the OSI Bridge a Cube replacement?

No. It is deliberately the minimum viable OSI translation layer. Side by side:

| Capability | Cube | OSI Bridge (this repo) |
|------------|------|------------------------|
| Hold the semantic model | Cube's own YAML/JS | OSI v1.0 (open standard) |
| Translate semantic model → SQL | yes | yes |
| Query API for downstream consumers | REST + GraphQL + SQL wire + MDX | MCP only (3 tools) |
| Caching / pre-aggregations | yes (Cube Store) | no — delegated to UC Metric View materialisation |
| Row-level security / RBAC | yes (context-based) | no — delegated to Unity Catalog |
| Multi-database connectors | 30+ sources | Databricks only |
| Multi-tenancy, JWT auth | yes | no |
| Playground / admin UI | yes (Cube Cloud) | no |
| Lines of code | hundreds of thousands | ~250 |

The substantive shift: with Cube, **Cube was the contract**. With this approach, **OSI YAML is the contract** — vendor-neutral, jointly owned by the OSI working group. Swap the Bridge for any other OSI-aware MCP server, or swap Databricks for Dremio / Strategy, and the agent works unchanged.

If your roadmap needs the other 95% of Cube (pre-aggs, multi-source joins, BI wire protocols, admin UI), grow the Bridge selectively or pick an OSI-compliant commercial product to play that middleware role — keeping OSI as the contract either way.

## Security notes for forks

- `.env` is gitignored; never commit real tokens.
- The `agent_metadata.yaml` is the demo's metadata — replace with your own for your domain.
- The bridge has no auth on the MCP endpoint by default — bind it to `localhost` (`OSI_BRIDGE_HOST=127.0.0.1`) for any non-demo usage, or front it with mTLS / an API key check.

## License

Apache 2.0.
