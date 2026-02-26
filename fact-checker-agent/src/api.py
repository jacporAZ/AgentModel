from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .agent import answer_query

app = FastAPI(title="Fact Checker Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str

@app.get("/")
def root(): 
    return {"status": "ok", "docs": "/docs", "endpoint": "/ask"}

@app.post("/ask")
def ask(req: AskRequest):
    result = answer_query(req.question)
    return result