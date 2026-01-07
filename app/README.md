# Neural Style Transfer FastAPI App

A FastAPI web app for neural style transfer. It defaults to a fast feed‑forward style model (one pre‑trained .pth per style) for sub‑30s CPU inference on small VPSes. If no fast model is available, it falls back to an iterative VGG19 optimization with a tiny step budget.

## Features
- Upload content image (style image optional).
- CPU‑friendly fast feed‑forward inference using pre‑trained models in `app/models`.
- Enforced upload size limit (configurable).
- Optional iterative fallback (reduced steps) when fast model is missing.

## Tech Stack
- Python, FastAPI, Uvicorn
- PyTorch + TorchVision (VGG19 features)
- Frontend: vanilla HTML/CSS/JS

## Setup (Local)
```bash
python -m venv .venv
source .venv/bin/activate  # (macOS/Linux)
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If running on a CPU-only VPS you may want to install the CPU wheels for torch explicitly (see https://pytorch.org for the right command). The pinned versions here target recent PyTorch.

Place one or more fast style model weights (`*.pth`) in `app/models/`. Example names: `mosaic.pth`. Set `ST_DEFAULT_STYLE_NAME` to the model name without extension.

## Run (Dev)
```bash
uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```
Open: http://localhost:8000

## Production Suggestions
Use `gunicorn` with Uvicorn workers behind Nginx:
```bash
pip install gunicorn
GUNICORN_CMD_ARGS="--timeout 180" gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:8000 src.server:app
```
Add Nginx reverse proxy for TLS and static caching.

### Caddy Reverse Proxy Under a Subpath (/ml)
If you serve multiple apps on one domain and want this app at `https://apps.example.com/ml/`:

1. Run the app on an internal port (e.g. 8006):
```bash
BASE_PATH=/ml GUNICORN_CMD_ARGS="--timeout 300" gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 127.0.0.1:8006 src.server:app
```

2. In your Caddyfile:
```
apps.example.com {
	handle /ml/* {
		uri strip_prefix /ml
		reverse_proxy 127.0.0.1:8006 {
			header_up X-Forwarded-Prefix /ml
		}
	}
}
```

3. All internal links/scripts are generated using BASE_PATH so the form posts to `/ml/stylize` and static assets load from `/ml/static/style.css`.

Note: If you use `systemd`, set `Environment=BASE_PATH=/ml` in the service file.

## Docker
Build:
```bash
docker build -t style-transfer-app:latest .
```

Run (root path):
```bash
docker run --rm -p 8000:8000 style-transfer-app:latest
```

Run under a base path (/ml):
```bash
docker run --rm -e BASE_PATH=/ml -p 8000:8000 style-transfer-app:latest
```

Bind a host volume for uploads (optional temporary files):
```bash
docker run --rm -p 8000:8000 -v "$PWD/uploads":/app/uploads style-transfer-app:latest
```

Pre-pulling VGG19 weights occurs at build; to disable remove the corresponding RUN line in `Dockerfile`.

This image supports fast feed‑forward models out of the box via `app/models/*.pth`.

## Environment Variables
- `ST_DEFAULT_STYLE_NAME`: Name of the fast style model (e.g., `mosaic`). If unset, first available model is used. If no model is found, iterative fallback is used.
- `ST_MAX_UPLOAD_MB`: Max per‑file upload size in MB (default `5`).
- `ST_FAST_MAX_SIDE`: Max longer side (pixels) for fast inference resize (default `720`). Lower for smaller VPS (e.g., `640`).
- `ST_WORKERS`: Background job workers (default `1`). Keep `1` for 1 GB RAM VPS.
- `BASE_PATH`: Serve under a subpath when behind a reverse proxy (e.g., `/ml`).

## Notes
- On a 1 GB CPU‑only VPS, use fast models with `ST_FAST_MAX_SIDE=640..720` to keep inference well under 30 seconds.
- The iterative fallback is intentionally limited (low steps) and only used when no fast model is available.

## License
MIT (add a LICENSE file if you want explicit licensing).
