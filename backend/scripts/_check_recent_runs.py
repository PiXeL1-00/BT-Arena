"""Quick diagnostic: check recent runs from the Galileo API."""
import httpx

BASE = "http://localhost:8000"

# Get recent runs via galileo summary
print("=== 7-day Model Summary ===")
r = httpx.get(f"{BASE}/galileo/models/summary", params={"window": 7}, timeout=15)
data = r.json()
for m in data.get("models", []):
    print(f"  {m.get('display_name', m.get('model_name', '?')):40s}  avg={m.get('window_avg')}  runs={m.get('window_runs')}")

# Check today's runs specifically
print("\n=== Today's runs (via galileo trend, 1-day window) ===")
r = httpx.get(f"{BASE}/galileo/models/trend", params={"window": 1, "bucket": 1}, timeout=15)
data = r.json()
for series in data.get("series", []):
    llm_id = series["llm_id"]
    buckets = series.get("buckets", [])
    for b in buckets:
        print(f"  {llm_id:40s}  date={b.get('bucket')}  avg={b.get('score_avg')}  n={b.get('n')}")

# List all models from registry
print("\n=== Registered Models ===")
r = httpx.get(f"{BASE}/models/registry", timeout=5)
models = r.json().get("models", [])
for m in models:
    print(f"  {m['id']:40s}  label={m.get('label')}")
print(f"  Total: {len(models)} models")
