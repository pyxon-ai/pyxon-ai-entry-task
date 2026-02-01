from fastapi import FastAPI
from routes import base, chunk

app = FastAPI()
app.include_router(base.base_router)
app.include_router(chunk.chunk_router)