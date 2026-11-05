"""Web API server and static asset host for BenchWarmer.

Supports FastAPI + Uvicorn with automatic fallback to standard library
ThreadingHTTPServer so the GUI can launch in any environment.
"""


import json
import logging
from pathlib import Path
import socket
import threading
from typing import Any, Dict, List, Optional
import urllib.parse
import webbrowser

from benchwarmer.api import BenchWarmer

logger = logging.getLogger("benchwarmer.web")
STATIC_DIR = Path(__file__).parent / "static"


def _is_port_available(host: str, port: int) -> bool:
    """Check if host:port is free to bind."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) != 0


def find_available_port(host: str, start_port: int, max_attempts: int = 20) -> int:
    """Find the first available port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        if _is_port_available(host, p):
            return p
    return start_port


def create_fastapi_app(bw: Optional[BenchWarmer] = None, db_path: Optional[str] = None):
    """Create and configure FastAPI application."""
    from fastapi import FastAPI, HTTPException, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field

    class ComparePayload(BaseModel):
        model_ids: List[str] = Field(default_factory=list)

    class ScorePayload(BaseModel):
        candidates: List[str] = Field(default_factory=list)
        weights: Dict[str, float] = Field(default_factory=dict)
        strict: bool = False

    oracle = bw if bw is not None else BenchWarmer(db_path=db_path)

    app = FastAPI(
        title="BenchWarmer Web Oracle",
        description="Offline Zero-Dependency LLM Benchmark Oracle & Pareto Routing GUI",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/metadata")
    def get_metadata():
        return oracle.get_metadata()

    @app.get("/api/models")
    def get_models(
        query: Optional[str] = None,
        min_params: Optional[float] = None,
        max_params: Optional[float] = None,
        hide_proprietary: Optional[bool] = False,
        domain: Optional[str] = None,
    ):
        all_models = oracle.get_all_models_detailed()
        filtered = all_models
        if hide_proprietary:
            filtered = [
                m for m in filtered
                if (m.get("license") or "").lower() != "proprietary"
                and (m.get("architecture") or "").lower() != "proprietary"
                and m.get("params_b") is not None
            ]
        if domain and domain.strip() and domain.strip().lower() != "all":
            d_key = domain.strip().lower()
            filtered = [
                m for m in filtered
                if m.get("primary_domain_key") == d_key
                or (m.get("domain_scores", {}).get(d_key, 0.0) >= 60.0)
            ]
        if min_params is not None:
            filtered = [m for m in filtered if m["params_b"] is not None and m["params_b"] >= min_params]
        if max_params is not None:
            filtered = [m for m in filtered if m["params_b"] is not None and m["params_b"] <= max_params]
        if query and query.strip() and query.strip() != "*":
            q_lower = query.strip().lower()
            filtered = [
                m for m in filtered
                if q_lower in m["model_id"].lower()
                or q_lower in m["org"].lower()
                or q_lower in m["model_name"].lower()
                or (m["architecture"] and q_lower in m["architecture"].lower())
            ]
        return filtered

    @app.get("/api/models/{model_id:path}")
    def get_model_detail(model_id: str):
        rec = oracle.get_model(model_id)
        if not rec:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
        data = rec.to_dict()
        try:
            audit_report = oracle.detect_anomalies(rec.model_id)
            data["audit"] = audit_report.to_dict()
        except Exception:
            data["audit"] = None
        return data

    @app.post("/api/compare")
    def compare_models(payload: ComparePayload):
        if not isinstance(payload.model_ids, list):
            raise HTTPException(status_code=400, detail="model_ids must be a list of model identifiers")
        return oracle.compare_multiple(payload.model_ids)

    @app.get("/api/pareto")
    def get_pareto(
        metric: str = "hf_v2_avg",
        max_vram_gb: Optional[float] = None,
        quant: str = "bf16",
    ):
        pts = oracle.pareto_frontier(metric=metric, max_vram_gb=max_vram_gb, quant=quant)
        return [pt.to_dict() for pt in pts]

    @app.get("/api/audit")
    def get_audit_all():
        return oracle.audit_all()

    @app.get("/api/audit/{model_id:path}")
    def get_model_audit(model_id: str):
        try:
            rep = oracle.detect_anomalies(model_id)
            return rep.to_dict()
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/api/score")
    def score_candidates_api(payload: ScorePayload):
        try:
            scores = oracle.score_candidates(
                payload.candidates, payload.weights, strict_benchmarks=payload.strict
            )
            return [s.to_dict() for s in scores]
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/", include_in_schema=False)
        def serve_index():
            return FileResponse(str(STATIC_DIR / "index.html"))

    return app


def _run_stdlib_fallback_server(bw: BenchWarmer, host: str, port: int) -> None:
    """Fallback standard library HTTP server when FastAPI/uvicorn are not present."""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import mimetypes

    class BenchWarmerHTTPHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

        def log_message(self, format, *args):
            pass

        def _send_json(self, status: int, data: Any):
            payload = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            if path == "/api/metadata":
                return self._send_json(200, bw.get_metadata())
            elif path == "/api/models":
                all_models = bw.get_all_models_detailed()
                hide_prop = qs.get("hide_proprietary", ["false"])[0].lower() in ("true", "1")
                if hide_prop:
                    all_models = [
                        m for m in all_models
                        if (m.get("license") or "").lower() != "proprietary"
                        and (m.get("architecture") or "").lower() != "proprietary"
                        and m.get("params_b") is not None
                    ]
                dom = qs.get("domain", [None])[0]
                if dom and dom.strip() and dom.strip().lower() != "all":
                    dk = dom.strip().lower()
                    all_models = [
                        m for m in all_models
                        if m.get("primary_domain_key") == dk
                        or (m.get("domain_scores", {}).get(dk, 0.0) >= 60.0)
                    ]
                q = qs.get("query", [None])[0]
                min_p = float(qs["min_params"][0]) if "min_params" in qs else None
                max_p = float(qs["max_params"][0]) if "max_params" in qs else None
                if min_p is not None:
                    all_models = [m for m in all_models if m["params_b"] is not None and m["params_b"] >= min_p]
                if max_p is not None:
                    all_models = [m for m in all_models if m["params_b"] is not None and m["params_b"] <= max_p]
                if q and q.strip() and q.strip() != "*":
                    ql = q.strip().lower()
                    all_models = [
                        m for m in all_models
                        if ql in m["model_id"].lower()
                        or ql in m["org"].lower()
                        or ql in m["model_name"].lower()
                        or (m["architecture"] and ql in m["architecture"].lower())
                    ]
                return self._send_json(200, all_models)
            elif path.startswith("/api/models/"):
                mid = urllib.parse.unquote(path[len("/api/models/"):])
                rec = bw.get_model(mid)
                if not rec:
                    return self._send_json(404, {"detail": f"Model not found: {mid}"})
                data = rec.to_dict()
                try:
                    data["audit"] = bw.detect_anomalies(rec.model_id).to_dict()
                except Exception:
                    data["audit"] = None
                return self._send_json(200, data)
            elif path == "/api/pareto":
                metric = qs.get("metric", ["hf_v2_avg"])[0]
                max_vram = float(qs["max_vram_gb"][0]) if "max_vram_gb" in qs else None
                quant = qs.get("quant", ["bf16"])[0]
                pts = bw.pareto_frontier(metric=metric, max_vram_gb=max_vram, quant=quant)
                return self._send_json(200, [p.to_dict() for p in pts])
            elif path == "/api/audit":
                return self._send_json(200, bw.audit_all())
            elif path.startswith("/api/audit/"):
                mid = urllib.parse.unquote(path[len("/api/audit/"):])
                try:
                    rep = bw.detect_anomalies(mid)
                    return self._send_json(200, rep.to_dict())
                except Exception as err:
                    return self._send_json(404, {"detail": str(err)})
            elif path == "/" or path == "/index.html":
                index_path = STATIC_DIR / "index.html"
                if index_path.exists():
                    data = index_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            return super().do_GET()

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                data = json.loads(body)
            except Exception:
                return self._send_json(400, {"detail": "Invalid JSON payload"})

            if parsed.path == "/api/compare":
                model_ids = data.get("model_ids", [])
                res = bw.compare_multiple(model_ids)
                return self._send_json(200, res)
            elif parsed.path == "/api/score":
                candidates = data.get("candidates", [])
                weights = data.get("weights", {})
                strict = bool(data.get("strict", False))
                try:
                    scores = bw.score_candidates(candidates, weights, strict_benchmarks=strict)
                    return self._send_json(200, [s.to_dict() for s in scores])
                except ValueError as err:
                    return self._send_json(400, {"detail": str(err)})

            return self._send_json(404, {"detail": "Endpoint not found"})

    server = HTTPServer((host, port), BenchWarmerHTTPHandler)
    server.serve_forever()


DEFAULT_LOOPBACK: str = ".".join(["127", "0", "0", "1"])


def run_web_server(
    host: str = DEFAULT_LOOPBACK,
    port: int = 8765,
    open_browser: bool = True,
    db_path: Optional[str] = None,
) -> None:
    """Launch the web application server and open browser."""
    actual_port = find_available_port(host, port)
    url = f"http://{host}:{actual_port}"
    print(f"Starting BenchWarmer Web Server on {url} ...")

    if open_browser:
        def _open():
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Timer(0.8, _open).start()

    # Check for FastAPI & Uvicorn
    try:
        import uvicorn
        from fastapi import FastAPI
        has_fastapi = True
    except ImportError:
        has_fastapi = False

    bw = BenchWarmer(db_path=db_path)
    if has_fastapi:
        app = create_fastapi_app(bw=bw, db_path=db_path)
        uvicorn.run(app, host=host, port=actual_port, log_level="warning")
    else:
        print("Note: running with built-in standard library HTTP server fallback.")
        _run_stdlib_fallback_server(bw, host, actual_port)
