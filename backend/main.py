import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from errors import AppError
from routers import actions, chat, conversations, data

app = FastAPI(title="SeatScope AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings()["origins"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
for router in (data.router, conversations.router, chat.router, actions.router):
    app.include_router(router)


@app.exception_handler(AppError)
async def app_error(_request: Request, error: AppError):
    return JSONResponse(status_code=error.status_code, content={"detail": error.message})


@app.exception_handler(Exception)
async def unexpected_error(_request: Request, error: Exception):
    logging.exception("Unhandled API error", exc_info=error)
    return JSONResponse(status_code=503, content={"detail": "서비스 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요"})


@app.get("/", tags=["health"])
def health():
    return {"service": "SeatScope AI", "status": "ok"}
