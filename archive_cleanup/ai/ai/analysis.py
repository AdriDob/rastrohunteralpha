from typing import Any

from ai.ollama_client import OllamaClient
from ai.prompts.analysis_prompt import endpoint_analysis_prompt


class AIAnalyzer:
    def __init__(self, host: str | None = None):
        self.client = OllamaClient(host=host) if host else OllamaClient()

    def analyze_endpoint(
        self, path: str, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = endpoint_analysis_prompt(path=path, method=method, params=params)
        result = self.client.predict(model="llama2", prompt=prompt, max_tokens=300)
        return {"summary": result}
