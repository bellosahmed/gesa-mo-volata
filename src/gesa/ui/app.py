# src/gesa/ui/app.py
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from gesa.orchestrator import run
from gesa.model import LlamaModel

app = FastAPI()
_STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC), name="static")
_model = None

class PlanReq(BaseModel):
    request: str
    lang: str = "en"

def _get_model():
    global _model
    if _model is None:
        _model = LlamaModel(os.environ["GESA_MODEL"])
    return _model

@app.get("/")
def index():
    return FileResponse(os.path.join(_STATIC, "index.html"))

@app.post("/plan")
def plan(req: PlanReq):
    return run(req.request, _get_model(), lang=req.lang)
