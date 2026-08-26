"""Research API routes — /api/v1/research/

Exposes the paper database populated by the Research Agent team.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.db.session import get_db
from src.backend.models.paper import Paper
from src.backend.schemas.common import PaginatedResponse
from src.backend.schemas.research import PaperCreate, PaperResponse, PaperSummary, PaperUpdate

router = APIRouter(prefix="/research", tags=["research"])


@router.post(
    "/papers",
    response_model=PaperResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a paper to the database (Research Agent endpoint)",
)
async def create_paper(
    payload: PaperCreate,
    db: AsyncSession = Depends(get_db),
) -> PaperResponse:
    paper = Paper(**payload.model_dump())
    db.add(paper)
    await db.flush()
    return PaperResponse.model_validate(paper)


@router.get(
    "/papers",
    response_model=PaginatedResponse[PaperSummary],
    summary="List papers with optional filters",
)
async def list_papers(
    tags: list[str] | None = Query(None, description="Filter by tags (OR match)"),
    min_relevance: float | None = Query(None, ge=0.0, le=1.0),
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PaperSummary]:
    query = select(Paper)
    if min_relevance is not None:
        query = query.where(Paper.relevance_score >= min_relevance)
    if year_from is not None:
        query = query.where(Paper.year >= year_from)
    if year_to is not None:
        query = query.where(Paper.year <= year_to)
    # JSON array tag filter — PostgreSQL JSON containment operator
    # TODO: for production, use PostgreSQL JSONB with @> for performance.

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = (
        query.order_by(Paper.relevance_score.desc().nullslast(), Paper.year.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    papers = result.scalars().all()

    return PaginatedResponse(
        items=[PaperSummary.model_validate(p) for p in papers],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/papers/search",
    response_model=PaginatedResponse[PaperSummary],
    summary="Full-text search across title and abstract",
)
async def search_papers(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PaperSummary]:
    """Case-insensitive substring search on title and abstract.

    TODO: Replace with PostgreSQL full-text search (tsvector) for production.
    """
    q_lower = f"%{q.lower()}%"
    query = select(Paper).where(
        or_(
            func.lower(Paper.title).like(q_lower),
            func.lower(Paper.abstract).like(q_lower),
        )
    )
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    papers = result.scalars().all()

    return PaginatedResponse(
        items=[PaperSummary.model_validate(p) for p in papers],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/papers/{paper_id}", response_model=PaperResponse, summary="Get paper details")
async def get_paper(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PaperResponse:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Paper '{paper_id}' not found"
        )
    return PaperResponse.model_validate(paper)


@router.patch(
    "/papers/{paper_id}", response_model=PaperResponse, summary="Update paper annotations"
)
async def update_paper(
    paper_id: UUID,
    payload: PaperUpdate,
    db: AsyncSession = Depends(get_db),
) -> PaperResponse:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Paper '{paper_id}' not found"
        )

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(paper, field, value)
    await db.flush()
    return PaperResponse.model_validate(paper)
