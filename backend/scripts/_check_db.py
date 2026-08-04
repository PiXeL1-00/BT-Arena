"""Quick DB diagnostic: check today's runs directly."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

async def main():
    from app.infra.db.session import async_session_factory
    from sqlalchemy import text
    
    async with async_session_factory() as session:
        # Count today's runs by status
        result = await session.execute(text("""
            SELECT status, COUNT(*) as cnt
            FROM runs 
            WHERE created_at >= CURRENT_DATE
            GROUP BY status
            ORDER BY status
        """))
        print("=== Today's Runs by Status ===")
        for row in result:
            print(f"  {row[0]:15s}  count={row[1]}")
        
        # Count today's results by model
        result = await session.execute(text("""
            SELECT r.model_key, 
                   COUNT(*) as total,
                   SUM(CASE WHEN r.passed THEN 1 ELSE 0 END) as passed,
                   AVG(r.score) as avg_score,
                   COUNT(CASE WHEN r.critical_fail_reason IS NOT NULL THEN 1 END) as failures
            FROM run_results r
            JOIN runs ru ON ru.run_id = r.run_id
            WHERE ru.created_at >= CURRENT_DATE
            GROUP BY r.model_key
            ORDER BY r.model_key
        """))
        print("\n=== Today's Results by Model ===")
        for row in result:
            print(f"  {row[0]:40s}  total={row[1]}  passed={row[2]}  avg={row[3]:.1f}  fails={row[4]}")
        
        # Show the most recent 20 runs
        result = await session.execute(text("""
            SELECT run_id, dataset_id, case_id, status, models_json::text, 
                   created_at, finished_at
            FROM runs
            ORDER BY created_at DESC
            LIMIT 20
        """))
        print("\n=== Last 20 Runs ===")
        for row in result:
            duration = ""
            if row[5] and row[6]:
                d = (row[6] - row[5]).total_seconds()
                duration = f" ({d:.0f}s)"
            print(f"  {str(row[5])[11:19]}  {row[3]:10s}  {row[1]:25s}  {row[2]:6s}  {row[4][:60]}{duration}")

asyncio.run(main())
