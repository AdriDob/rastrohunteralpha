import requests


class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host

    def predict(self, model: str, prompt: str, max_tokens: int = 512):
        """Simple wrapper to call Ollama local API. Requires Ollama corriendo localmente."""
        url = f"{self.host}/api/generate"
        payload = {"model": model, "prompt": prompt, "max_tokens": max_tokens}
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
