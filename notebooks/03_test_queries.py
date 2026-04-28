# Databricks notebook source
# MAGIC %md
# MAGIC # Step 3 — Test the Metric View
# MAGIC
# MAGIC Three sanity-check queries against `<catalog>.<schema>.<metric_view>`.

# COMMAND ----------

dbutils.widgets.text("catalog",     "main",      "Catalog")
dbutils.widgets.text("schema",      "osi_demo",  "Schema")
dbutils.widgets.text("metric_view", "orders_mv", "Metric view name")

FQN = (f"{dbutils.widgets.get('catalog')}."
       f"{dbutils.widgets.get('schema')}."
       f"{dbutils.widgets.get('metric_view')}")
print(f"Querying {FQN}")

# COMMAND ----------

# Q1 — total revenue by priority
display(spark.sql(f"""
    SELECT MEASURE(total_revenue) AS revenue, order_priority
    FROM {FQN}
    GROUP BY order_priority
    ORDER BY revenue DESC
"""))

# COMMAND ----------

# Q2 — orders + AOV by year
display(spark.sql(f"""
    SELECT
      YEAR(order_date)         AS yr,
      MEASURE(order_count)     AS orders,
      MEASURE(avg_order_value) AS aov
    FROM {FQN}
    GROUP BY YEAR(order_date)
    ORDER BY yr
"""))

# COMMAND ----------

# Q3 — what Gemini would ask: revenue by priority for 1998
display(spark.sql(f"""
    SELECT MEASURE(total_revenue) AS revenue, order_priority
    FROM {FQN}
    WHERE order_date BETWEEN DATE '1998-01-01' AND DATE '1998-12-31'
    GROUP BY order_priority
    ORDER BY revenue DESC
"""))
