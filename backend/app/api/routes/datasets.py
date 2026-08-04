from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.infra.db.repository import Repository

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("")
async def list_datasets(session: AsyncSession = Depends(get_session)):
    repo = Repository(session)
    rows = await repo.list_datasets()
    return [
        {
            "id": d.id,
            "version": d.version,
            "description": d.description,
            "case_count": len(d.cases) if d.cases else 0,
        }
        for d in rows
    ]


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_session),
):
    repo = Repository(session)
    ds = await repo.get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    return {
        "id": ds.id,
        "version": ds.version,
        "description": ds.description,
        "meta": ds.meta_json,
        "cases": [
            {
                "case_id": c.case_id,
                "topic": c.topic,
                "claim": c.claim,
                "pressure_score": c.pressure_score,
                "label": c.label,
                "evidence_packets": c.evidence_json,
            }
            for c in (ds.cases or [])
        ],
    }
