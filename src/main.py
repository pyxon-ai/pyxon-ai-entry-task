from fastapi import FastAPI
from routes.base import base_router
from routes.chunk import chunk_router
from routes.search import search_router
from routes.evaluate import evaluate_router

app = FastAPI()
app.include_router(base_router)
app.include_router(chunk_router)
app.include_router(search_router)
app.include_router(evaluate_router)