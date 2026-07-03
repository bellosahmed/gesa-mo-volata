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
        model_path = os.environ.get("GESA_MODEL")
        if not model_path:
            raise RuntimeError(
                "GESA_MODEL environment variable is not set; point it at a .gguf model file"
            )
        _model = LlamaModel(model_path)
    return _model

@app.get("/")
def index():
    return FileResponse(os.path.join(_STATIC, "index.html"))

@app.post("/plan")
def plan(req: PlanReq):
    return run(req.request, _get_model(), lang=req.lang)
