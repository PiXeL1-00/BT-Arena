"""Quick DB diagnostic."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

async def main():
    from app.infra.db.session import async_session_factory
    from sqlalchemy import text
    
    lines = []
    async with async_session_factory() as session:
        # Run status counts
        rows = (await session.execute(text(
            "SELECT status, COUNT(*) FROM runs WHERE created_at >= CURRENT_DATE GROUP BY status"
        ))).all()
        lines.append("=== Today's Runs by Status ===")
        for r in rows:
            lines.append(f"  {r[0]}: {r[1]}")
        
        # Results by model
        rows = (await session.execute(text(
            "SELECT r.model_key, COUNT(*) "
            "FROM run_results r JOIN runs ru ON ru.run_id = r.run_id "
            "WHERE ru.created_at >= CURRENT_DATE "
            "GROUP BY r.model_key ORDER BY r.model_key"
        ))).all()
        lines.append("\n=== Today's Result Count by Model ===")
        for r in rows:
            lines.append(f"  {r[0]}: {r[1]} results")
        
        # Critical failures today
        rows = (await session.execute(text(
            "SELECT r.model_key, r.case_id, r.critical_fail_reason "
            "FROM run_results r JOIN runs ru ON ru.run_id = r.run_id "
            "WHERE ru.created_at >= CURRENT_DATE AND r.critical_fail_reason IS NOT NULL "
            "ORDER BY ru.created_at DESC LIMIT 15"
        ))).all()
        lines.append("\n=== Today's Critical Failures ===")
        if not rows:
            lines.append("  (none)")
        for r in rows:
            reason = str(r[2])[:100] if r[2] else ""
            lines.append(f"  {r[0]:40s}  case={r[1]}  reason={reason}")
        
        # Last 20 runs
        rows = (await session.execute(text(
            "SELECT dataset_id, case_id, status, created_at "
            "FROM runs ORDER BY created_at DESC LIMIT 20"
        ))).all()
        lines.append("\n=== Last 20 Runs ===")
        for r in rows:
            lines.append(f"  {str(r[3])[11:19]}  {r[2]:10s}  {r[0]:25s}  {r[1]}")

    txt = "\n".join(lines)
    Path("scripts/_db_output.txt").write_text(txt, encoding="utf-8")
    print(txt)

asyncio.run(main())
