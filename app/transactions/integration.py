"""Glue between this feature and the main Waypoint app.

`setup_transactions(app)` is the single call app/main.py makes.  It creates the
tables, mounts the router and registers the error translations, so the feature
owns its own wiring and main.py stays a one-liner per feature.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import DEFAULT_DB_PATH, init_db
from .router import router
from .service import AccountNotFoundError, InvalidQueryError


async def _not_found(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _bad_query(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def setup_transactions(
    app: FastAPI,
    db_path: str | None = None,
    dependencies: Sequence[Any] | None = None,
) -> None:
    """Mount the transaction-history feature on an existing FastAPI app.

    dependencies: extra FastAPI dependencies applied to every history route,
    e.g. [Depends(get_current_user)] to require a signed-in user.
    """
    app.state.db_path = db_path or DEFAULT_DB_PATH
    init_db(app.state.db_path)
    app.include_router(router, dependencies=list(dependencies or []))
    app.add_exception_handler(AccountNotFoundError, _not_found)
    app.add_exception_handler(InvalidQueryError, _bad_query)


def create_app(db_path: str | None = None) -> FastAPI:
    """A minimal app with only this feature, for tests and standalone development."""
    app = FastAPI(
        title="Waypoint: Transaction History",
        version="0.1.0",
        description="Standalone run of the transaction-history feature. "
                    "In the full backend this router is mounted on app/main.py.",
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )
    setup_transactions(app, db_path=db_path)

    @app.get("/health", tags=["Health"], summary="Liveness check")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
