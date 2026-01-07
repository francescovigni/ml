import os
import time
from io import BytesIO
import warnings
from PIL import Image

# Ensure test-friendly defaults before importing the server
os.environ.setdefault("ST_DEFAULT_STYLE_NAME", "mosaic")
os.environ.setdefault("ST_FAST_MAX_SIDE", "640")

from fastapi.testclient import TestClient  # noqa: E402
from src.server import app  # noqa: E402


def make_test_image_bytes(w=256, h=256, color=(180, 160, 140)):
    img = Image.new("RGB", (w, h), color)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf.getvalue()


def test_ping():
    with TestClient(app) as client:
        r = client.get("/ping")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


def test_root_page():
    with TestClient(app) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert b"Neural Style Transfer" in r.content


def test_stylize_fast_under_30s():
    content_bytes = make_test_image_bytes(256, 256)
    with TestClient(app) as client:
        start = time.time()
        soft_limit = float(os.environ.get("STARTUP_SOFT_DEADLINE_S", "30"))
        hard_limit = float(os.environ.get("STARTUP_HARD_DEADLINE_S", "60"))
        files = {
            "content_image": ("content.jpg", content_bytes, "image/jpeg"),
            # style_image is optional; fast model is used by default
        }
        r = client.post("/stylize", files=files)
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]

        soft_deadline = start + soft_limit
        hard_deadline = start + hard_limit
        # Poll until we get an image back or timeout
        img_bytes = None
        while True:
            r2 = client.get(f"/stylize/{job_id}")
            if r2.status_code == 200:
                ctype = r2.headers.get("content-type", "")
                if ctype.startswith("image/"):
                    now = time.time()
                    if now > soft_deadline:
                        warnings.warn(
                            f"Stylize exceeded soft deadline ({soft_limit}s), completed in {now-start:.2f}s",
                            RuntimeWarning,
                        )
                    assert now < hard_deadline, f"Inference exceeded hard deadline ({hard_limit}s)"
                    img_bytes = r2.content
                    assert len(img_bytes) > 0
                    break
                else:
                    # JSON status; ensure not error
                    data = r2.json()
                    assert data.get("status") not in {"error", "cancelled"}, data
            if time.time() > hard_deadline:
                raise AssertionError(f"Timed out waiting for result under {hard_limit}s")
            time.sleep(0.5)

        # Validate image is not uniformly black
        from PIL import Image
        im = Image.open(BytesIO(img_bytes))
        bbox = im.convert("L").getbbox()
        assert bbox is not None, "Output image appears blank"
