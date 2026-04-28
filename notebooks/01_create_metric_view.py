# Databricks notebook source
# MAGIC %md
# MAGIC # Step 1 — Create the demo Metric View
# MAGIC
# MAGIC Builds `<catalog>.<schema>.<metric_view>` over `samples.tpch.orders`.
# MAGIC The widgets default to `main / osi_demo / orders_mv`.
# MAGIC Override them at the top of the notebook to match your workspace.

# COMMAND ----------

dbutils.widgets.text("catalog",     "main",      "Catalog")
dbutils.widgets.text("schema",      "osi_demo",  "Schema")
dbutils.widgets.text("metric_view", "orders_mv", "Metric view name")

CATALOG     = dbutils.widgets.get("catalog")
SCHEMA      = dbutils.widgets.get("schema")
METRIC_VIEW = dbutils.widgets.get("metric_view")
FQN         = f"{CATALOG}.{SCHEMA}.{METRIC_VIEW}"
print(f"Will create: {FQN}")

# COMMAND ----------

# Schema (catalog must already exist; create it via UI/SQL if not)
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA} "
          f"COMMENT 'OSI ↔ Gemini hackathon demo'")

# COMMAND ----------

# The current Databricks Metric View YAML schema accepts name/expr/window on
# columns and measures. Richer agent metadata (synonyms, display names,
# descriptions) lives in osi_bridge/agent_metadata.yaml and is merged by the
# exporter when producing OSI v1.0 YAML.
ddl = f"""
CREATE OR REPLACE VIEW {FQN}
  WITH METRICS
  LANGUAGE YAML
  COMMENT 'Sales orders semantic model — OSI demo'
AS $$
version: 0.1
source: samples.tpch.orders

dimensions:
  - name: order_priority
    expr: o_orderpriority
  - name: order_status
    expr: o_orderstatus
  - name: clerk
    expr: o_clerk
  - name: order_date
    expr: o_orderdate

measures:
  - name: total_revenue
    expr: SUM(o_totalprice)
  - name: order_count
    expr: COUNT(*)
  - name: avg_order_value
    expr: AVG(o_totalprice)
$$
"""
spark.sql(ddl)
print(f"Created metric view {FQN}")

# COMMAND ----------

# Sanity check
display(spark.sql(f"""
    SELECT MEASURE(total_revenue) AS revenue,
           MEASURE(order_count)   AS orders,
           order_priority
    FROM {FQN}
    WHERE order_date >= DATE '1998-01-01'
    GROUP BY order_priority
    ORDER BY revenue DESC
"""))
