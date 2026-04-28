# Architecture

```
┌─────────────────────────────────────────────────┐
│  Gemini (databricks-gemini-2-5-flash, OpenAI    │
│  compatible endpoint on Databricks)             │
│  — receives natural-language questions          │
│  — runs an MCP tool-calling loop                │
└──────────────────┬──────────────────────────────┘
                   │ MCP / SSE
                   ▼
┌─────────────────────────────────────────────────┐
│  OSI Bridge (this repo)                         │
│  ─ server.py        FastMCP server              │
│  ─ translator.py    OSI request → SQL           │
│  ─ exporter.py      Metric View → OSI YAML      │
│  Tools: list_metrics, list_dimensions,          │
│         query_metric                            │
└──────────────────┬──────────────────────────────┘
                   │ databricks-sql-connector
                   ▼
┌─────────────────────────────────────────────────┐
│  Databricks SQL Warehouse                       │
│   └── Unity Catalog Metric View                 │
│       <catalog>.<schema>.<metric_view>          │
│       (source of truth, OSI-aligned)            │
└─────────────────────────────────────────────────┘
```

## Component responsibilities

| Component | Owns |
|-----------|------|
| Metric View | Canonical metric definitions, governance, security |
| Exporter | One-way Metric View YAML → OSI v1.0 YAML |
| Bridge | Holds the OSI model in memory, translates and executes |
| Gemini | NL understanding, tool selection, answer synthesis |

## Why no Cube

Cube did three jobs: model store, query API, and cache. The bridge replaces the first two; Databricks Metric View materialisation (Preview) replaces the third.

## Vendor swap

The bridge is bound to an OSI YAML file, not to Databricks. To demo vendor-neutrality, point `--osi-model` at a Dremio- or Strategy-exported file and (with the matching `custom_extensions.<vendor>` block populated and the bridge's `query_metric` adapted) the same agent works against a different backend.
