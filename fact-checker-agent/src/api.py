from fastapi import FastAPI
from pydantic import BaseModel
from agent import answer_query

app = FastAPI(title="Fact Checker Agent API")

class AskRequest(BaseModel):
    question: str

@app.post("/ask")
def ask(req: AskRequest):
    result = answer_query(req.question)
    return result