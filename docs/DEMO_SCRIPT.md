# 5-minute hackathon demo script

In this script, `<FQN>` means `<OSI_CATALOG>.<OSI_SCHEMA>.<OSI_METRIC_VIEW>` from your `.env`.

| t | Action | Talking point |
|---|--------|---------------|
| 0:00 | Open Catalog Explorer → `<FQN>` | "This is the canonical semantic model in Unity Catalog." |
| 0:30 | Run `python -m osi_bridge.exporter --fqn <FQN> --out examples/model.osi.yaml` | "Same definition, exported as OSI v1.0 YAML — vendor-neutral." |
| 1:00 | Open `examples/model.osi.yaml` and highlight `metrics`, `datasets`, `ai_context` | "OSI is the contract every vendor agrees to." |
| 1:30 | `python -m osi_bridge.server --osi-model examples/model.osi.yaml` — show "Loaded N metrics" | "The bridge replaces Cube — about 250 lines, no caching layer to maintain." |
| 2:00 | `python examples/gemini_client.py "What was revenue by priority last year?"` | "Gemini calls list_metrics → query_metric directly. No Cube." |
| 3:00 | Repeat with: "Which priority grew fastest in revenue across the last 3 years?" | "Gemini handles multi-step reasoning over the same OSI model." |
| 4:00 | Swap to a Dremio-exported `model.osi.yaml`, restart bridge, re-ask | "Same agent. Different vendor. **OSI worked.**" |
| 5:00 | Wrap | "Customer keeps governance in Databricks UC, picks any agent framework, swaps any vendor." |
