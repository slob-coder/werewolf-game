"""Global exception handler for server-side error tracking."""

import traceback
from datetime import datetime
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import async_session_factory
from app.models.server_exception import ServerException


async def log_exception(
    exception_type: str,
    exception_message: str,
    exception_traceback: str | None = None,
    request_path: str | None = None,
    request_method: str | None = None,
    request_params: dict | None = None,
    room_id: str | None = None,
    game_id: str | None = None,
    context: dict | None = None,
) -> None:
    """
    Log an exception to the database for later analysis.
    
    This function is designed to be non-blocking and safe to call
    from exception handlers. Database errors are caught and ignored
    to prevent exception loops.
    """
    try:
        async with async_session_factory() as session:
            exception_record = ServerException(
                exception_type=exception_type,
                exception_message=exception_message,
                exception_traceback=exception_traceback,
                request_path=request_path,
                request_method=request_method,
                request_params=request_params,
                room_id=room_id,
                game_id=game_id,
                context=context,
            )
            session.add(exception_record)
            await session.commit()
    except Exception:
        # Silently ignore logging errors to prevent exception loops
        # In production, you might want to log to stderr or a file
        pass


def extract_request_info(request: Request) -> dict[str, Any]:
    """Extract relevant information from a request for logging."""
    info = {
        "path": str(request.url.path),
        "method": request.method,
    }
    
    # Try to extract query params
    try:
        query_params = dict(request.query_params)
        if query_params:
            info["query_params"] = query_params
    except Exception:
        pass
    
    # Try to extract path params
    try:
        path_params = request.path_params
        if path_params:
            info["path_params"] = path_params
    except Exception:
        pass
    
    # Try to extract room_id and game_id from path params
    if "room_id" in request.path_params:
        info["room_id"] = request.path_params["room_id"]
    if "game_id" in request.path_params:
        info["game_id"] = request.path_params["game_id"]
    
    return info


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler that logs all unhandled exceptions.
    
    This handler:
    1. Extracts request context
    2. Logs the exception to the database
    3. Returns a generic error response
    """
    # Extract request info
    request_info = extract_request_info(request)
    
    # Get exception details
    exception_type = type(exc).__name__
    exception_message = str(exc) or f"No message for {exception_type}"
    exception_traceback = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    
    # Log to database (async, non-blocking)
    await log_exception(
        exception_type=exception_type,
        exception_message=exception_message,
        exception_traceback=exception_traceback,
        request_path=request_info.get("path"),
        request_method=request_info.get("method"),
        request_params={
            k: v for k, v in request_info.items()
            if k in ["query_params", "path_params"]
        } or None,
        room_id=request_info.get("room_id"),
        game_id=request_info.get("game_id"),
    )
    
    # Return error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_type": exception_type,
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handler for HTTP exceptions (4xx, 5xx).
    
    Only logs 5xx errors (server errors) to avoid noise from 4xx (client errors).
    """
    # Extract request info
    request_info = extract_request_info(request)
    
    # Only log server errors (5xx)
    if exc.status_code >= 500:
        exception_traceback = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        
        await log_exception(
            exception_type=type(exc).__name__,
            exception_message=exc.detail or f"HTTP {exc.status_code}",
            exception_traceback=exception_traceback,
            request_path=request_info.get("path"),
            request_method=request_info.get("method"),
            request_params={
                k: v for k, v in request_info.items()
                if k in ["query_params", "path_params"]
            } or None,
            room_id=request_info.get("room_id"),
            game_id=request_info.get("game_id"),
        )
    
    # Return HTTP error response
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for request validation errors.
    
    These are client errors (4xx), so we don't log them to the database.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handler for SQLAlchemy database errors.
    
    These are always logged as they indicate potential data integrity issues.
    """
    # Extract request info
    request_info = extract_request_info(request)
    
    # Get exception details
    exception_traceback = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    
    await log_exception(
        exception_type=type(exc).__name__,
        exception_message=str(exc) or "Database error",
        exception_traceback=exception_traceback,
        request_path=request_info.get("path"),
        request_method=request_info.get("method"),
        request_params={
            k: v for k, v in request_info.items()
            if k in ["query_params", "path_params"]
        } or None,
        room_id=request_info.get("room_id"),
        game_id=request_info.get("game_id"),
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error",
            "error_type": type(exc).__name__,
        },
    )
