# src/gesa/model.py
import os
from typing import Protocol

class ModelClient(Protocol):
    def complete(self, prompt: str, grammar: str | None = None, max_tokens: int = 256) -> str: ...

class LlamaModel:
    def __init__(self, model_path: str, n_ctx: int = 2048):
        from llama_cpp import Llama
        self._llm = Llama(model_path=model_path, n_ctx=n_ctx,
                          n_threads=os.cpu_count(), n_gpu_layers=0, verbose=False)

    def complete(self, prompt: str, grammar: str | None = None, max_tokens: int = 256) -> str:
        from llama_cpp import LlamaGrammar
        g = LlamaGrammar.from_string(grammar) if grammar else None
        out = self._llm(prompt, grammar=g, max_tokens=max_tokens, temperature=0.2)
        return out["choices"][0]["text"]
