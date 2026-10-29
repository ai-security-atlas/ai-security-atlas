"""A small httpx client for victim-api."""

import httpx
import numpy as np


class BudgetExceeded(Exception):
    """HTTP 429: the key's query budget would be exceeded. `.usage` holds the server's numbers."""

    def __init__(self, usage):
        super().__init__(f"query budget exceeded: {usage}")
        self.usage = usage


class VictimClient:
    def __init__(self, base_url, key, timeout=30.0):
        self.http = httpx.Client(base_url=base_url, headers={"X-API-Key": key}, timeout=timeout)
        self.key = key

    def info(self):
        return self._json(self.http.get("/v1/model"))

    def usage(self):
        return self._json(self.http.get("/v1/usage"))

    def predict(self, X, detail="label", k=3):
        X = np.asarray(X, dtype=np.float64)
        return self._json(self.http.post("/v1/predict", json={"inputs": X.tolist(), "detail": detail, "k": k}))

    def predict_all(self, X, detail="label", k=3, batch=50):
        """Query X in batches; stop at the first 429. Returns (results, served detail, BudgetExceeded or None)."""
        results, served = [], None
        for i in range(0, len(X), batch):
            try:
                r = self.predict(X[i:i + batch], detail, k)
            except BudgetExceeded as e:
                return results, served, e
            results += r["results"]
            served = r["detail"]
        return results, served, None

    @staticmethod
    def _json(resp):
        if resp.status_code == 429:
            raise BudgetExceeded(resp.json().get("usage"))
        resp.raise_for_status()
        return resp.json()
