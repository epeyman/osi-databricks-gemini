# Databricks notebook source
# MAGIC %md
# MAGIC # Step 2 — Export Metric View to OSI v1.0 YAML
# MAGIC
# MAGIC Reads `${catalog}.${schema}.${metric_view}`, parses its embedded YAML body,
# MAGIC and emits an OSI v1.0 model file to your workspace home directory.

# COMMAND ----------

# MAGIC %pip install -q pyyaml

# COMMAND ----------

import json
import os
import yaml
from pyspark.sql import SparkSession

dbutils.widgets.text("catalog",     "main",      "Catalog")
dbutils.widgets.text("schema",      "osi_demo",  "Schema")
dbutils.widgets.text("metric_view", "orders_mv", "Metric view name")
dbutils.widgets.text("output_dir",  "",          "Output dir (blank = your workspace home /osi-demo)")

CATALOG     = dbutils.widgets.get("catalog")
SCHEMA      = dbutils.widgets.get("schema")
METRIC_VIEW = dbutils.widgets.get("metric_view")
FQN         = f"{CATALOG}.{SCHEMA}.{METRIC_VIEW}"

spark = SparkSession.builder.getOrCreate()

USER  = spark.sql("SELECT current_user()").collect()[0][0]
out_dir = dbutils.widgets.get("output_dir") or f"/Workspace/Users/{USER}/osi-demo"
OUTPUT_PATH = f"{out_dir}/model.osi.yaml"

print(f"FQN:    {FQN}")
print(f"Output: {OUTPUT_PATH}")

# COMMAND ----------

def fetch_metric_view_yaml(fqn: str) -> dict:
    rows = spark.sql(f"DESCRIBE TABLE EXTENDED {fqn} AS JSON").collect()
    payload = json.loads(rows[0][0])
    view_text = payload.get("view_text") or payload.get("View Text")
    if not view_text:
        raise RuntimeError(f"No view_text in DESCRIBE for {fqn}")
    return yaml.safe_load(view_text)

mv = fetch_metric_view_yaml(FQN)
print(json.dumps(mv, indent=2)[:600], "...")

# COMMAND ----------

def db_to_osi(mv: dict, fqn: str) -> dict:
    name = fqn.split(".")[-1]
    return {
        "version": "1.0",
        "semantic_model": [{
            "name": name,
            "description": mv.get("comment", "Databricks Metric View"),
            "ai_context": {
                "instructions": (
                    f"Semantic model exported from Databricks Metric View {fqn}. "
                    "Use the metrics defined here for any quantitative question."
                )
            },
            "datasets": [{
                "name": name,
                "source": mv["source"],
                "fields": [
                    {
                        "name": d["name"],
                        "expression": [{"dialect": "Databricks", "sql": d["expr"]}],
                        "dimension": {"is_time": False},
                        "ai_context": {"display_name": d["name"]},
                    }
                    for d in mv.get("dimensions", [])
                ],
            }],
            "metrics": [
                {
                    "name": m["name"],
                    "expression": [{"dialect": "Databricks", "sql": m["expr"]}],
                    "ai_context": {"display_name": m["name"]},
                }
                for m in mv.get("measures", [])
            ],
            "custom_extensions": {
                "databricks": {
                    "metric_view_fqn": fqn,
                    "query_pattern": (
                        "SELECT MEASURE(<metric>), <dims> FROM <fqn> "
                        "WHERE <filters> GROUP BY <dims>"
                    ),
                }
            },
        }],
    }

osi = db_to_osi(mv, FQN)
print(yaml.safe_dump(osi, sort_keys=False)[:800], "...")

# COMMAND ----------

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w") as f:
    yaml.safe_dump(osi, f, sort_keys=False)
print(f"Wrote OSI YAML to {OUTPUT_PATH}")
