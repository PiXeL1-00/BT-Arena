"""Check analytics endpoints and look for Gemini/Grok bridge issues."""
import httpx
import json

BASE = "http://localhost:8000"

# Summary
r = httpx.get(f"{BASE}/galileo/models/summary", params={"window": 30}, timeout=10)
data = r.json()
models = data.get("models", [])
print(f"=== Summary ({r.status_code}) ===")
print(f"Models in analytics DB: {len(models)}")
for m in models:
    avg = m.get("all_time_avg")
    avg_str = f"{avg:.1f}" if avg is not None else "N/A"
    print(f"  {m.get('provider','?')}/{m.get('model_name','?')}: "
          f"avg={avg_str} runs={m.get('all_time_runs',0)} active={m.get('is_active')}")

# Trend
r2 = httpx.get(f"{BASE}/galileo/models/trend", params={"window": 30}, timeout=10)
trend = r2.json()
print(f"\n=== Trend ({r2.status_code}) ===")
for s in trend.get("series", []):
    print(f"  llm_id={s.get('llm_id')}: {len(s.get('buckets',[]))} buckets")

# Distribution
r3 = httpx.get(f"{BASE}/galileo/models/distribution", params={"window": 30}, timeout=10)
dist = r3.json()
print(f"\n=== Distribution ({r3.status_code}) ===")
for item in dist.get("items", []):
    print(f"  bin={item.get('bin_label','?')}: n={item.get('n',0)}")

print("\n=== All endpoints working ===")
