"""Results persistence. SQLite now; point DATABASE_URL at Postgres later.

The schema is intentionally minimal: one row per annotated variant, tagged with
the upload batch it came from.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, create_engine, distinct, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .config import get_settings
from .models import (
    Annotation,
    RecentVariant,
    SignificanceBucket,
    StatsMetrics,
)


class Base(DeclarativeBase):
    pass


class AnnotationRecord(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String, index=True)
    chrom: Mapped[str] = mapped_column(String)
    pos: Mapped[int] = mapped_column(Integer)
    ref: Mapped[str] = mapped_column(String)
    alt: Mapped[str] = mapped_column(String)
    gene: Mapped[str | None] = mapped_column(String, nullable=True)
    variant: Mapped[str | None] = mapped_column(String, nullable=True)
    significance: Mapped[str | None] = mapped_column(String, nullable=True)
    disease: Mapped[str | None] = mapped_column(String, nullable=True)
    clinvar_id: Mapped[str | None] = mapped_column(String, nullable=True)
    matched: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


_settings = get_settings()
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
engine = create_engine(_settings.database_url, connect_args=_connect_args)


def init_db() -> None:
    # Ensure the SQLite parent directory exists for file-based URLs.
    if _settings.database_url.startswith("sqlite:///"):
        from pathlib import Path

        Path(_settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get_stats() -> tuple[StatsMetrics, list[SignificanceBucket], list[RecentVariant]]:
    """Aggregate dashboard stats from the annotations table."""
    with Session(engine) as session:
        total = session.scalar(select(func.count()).select_from(AnnotationRecord)) or 0
        batches = session.scalar(select(func.count(distinct(AnnotationRecord.batch_id)))) or 0
        matched = session.scalar(
            select(func.count()).select_from(AnnotationRecord).where(AnnotationRecord.matched == 1)
        ) or 0
        pathogenic = session.scalar(
            select(func.count())
            .select_from(AnnotationRecord)
            .where(AnnotationRecord.significance.like("%athogenic%"))
        ) or 0

        metrics = StatsMetrics(
            total_annotations=total,
            total_batches=batches,
            matched_count=matched,
            pathogenic_count=pathogenic,
            match_rate=(matched / total) if total else 0.0,
        )

        sig_rows = session.execute(
            select(AnnotationRecord.significance, func.count())
            .where(AnnotationRecord.matched == 1)
            .group_by(AnnotationRecord.significance)
            .order_by(func.count().desc())
        ).all()
        significance = [
            SignificanceBucket(label=label or "Unknown", count=count) for label, count in sig_rows
        ]

        recent_rows = session.scalars(
            select(AnnotationRecord).order_by(AnnotationRecord.id.desc()).limit(12)
        ).all()
        recent = [
            RecentVariant(
                chrom=r.chrom,
                pos=r.pos,
                ref=r.ref,
                alt=r.alt,
                gene=r.gene,
                variant=r.variant,
                significance=r.significance,
                matched=bool(r.matched),
                created_at=r.created_at.isoformat(),
            )
            for r in recent_rows
        ]

    return metrics, significance, recent


def save_annotations(batch_id: str, annotations: list[Annotation]) -> None:
    with Session(engine) as session:
        session.add_all(
            AnnotationRecord(
                batch_id=batch_id,
                chrom=a.chrom,
                pos=a.pos,
                ref=a.ref,
                alt=a.alt,
                gene=a.gene,
                variant=a.variant,
                significance=a.significance,
                disease=a.disease,
                clinvar_id=a.clinvar_id,
                matched=1 if a.matched else 0,
            )
            for a in annotations
        )
        session.commit()
