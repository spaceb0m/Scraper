# Analyzer Pipeline + History Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace history row-click with folder/analyze icons, add `partial` job status, and build a complete analysis pipeline (`src/analyzer/`) that reads a scraped CSV, filters brand names, fingerprints business websites for ecommerce platforms, and exports a two-sheet XLSX.

**Architecture:** The analyzer mirrors the existing CLI pattern — a subprocess launched by FastAPI, streaming logs via SSE to a new `static/analyze.html` page. `src/analyzer/cli.py` reads the CSV, applies brand filtering from `config/excluded_brands.json`, uses `aiohttp` to fetch websites, `fingerprint.py` to detect platforms, and `openpyxl` to write the XLSX. A separate `analyze_jobs` dict tracks analysis state in the server.

**Tech Stack:** Python 3.9, FastAPI, aiohttp, openpyxl, existing SSE/subprocess pattern from server.py

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `requirements.txt` | Add aiohttp, openpyxl |
| Modify | `static/index.html` | Replace row-click with folder + analyze icons; add `partial` status label |
| Modify | `server.py` | Add `partial` status logic; add analyzer routes |
| Create | `config/excluded_brands.json` | Persistent brand exclusion list |
| Create | `src/analyzer/__init__.py` | Empty package marker |
| Create | `src/analyzer/brand_filter.py` | `load_brands`, `is_excluded` |
| Create | `src/analyzer/fingerprint.py` | `fetch_page`, `detect_platform` |
| Create | `src/analyzer/cli.py` | Analysis subprocess entry point |
| Create | `static/analyze.html` | Analysis UI with SSE log, brand editor, download |
| Create | `tests/test_brand_filter.py` | Pure unit tests for brand_filter |
| Create | `tests/test_fingerprint.py` | Pure unit tests for detect_platform |
| Modify | `CLAUDE.md` | Bump version to 0.4, document analyzer |
| Modify | `.claude/TODO.md` | Add Fase 6 and Fase 7 to roadmap |

---

## Task 1: Add dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**

Replace the file contents with:

```
playwright>=1.50.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
python-multipart>=0.0.12
shapely>=2.0.0
aiohttp>=3.9.0
openpyxl>=3.1.0
```

- [ ] **Step 2: Install new dependencies**

```bash
pip install aiohttp openpyxl
```

Expected: packages install without errors.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add aiohttp and openpyxl dependencies"
```

---

## Task 2: Fix history icons in index.html

**Files:**
- Modify: `static/index.html`

Currently each history row has a `click` handler that opens/downloads. Replace this with two explicit icon buttons per row, and add the `partial` status.

- [ ] **Step 1: Add `partial` to STATUS_LABELS**

Find this block in `static/index.html`:

```js
const STATUS_LABELS = {
  done:    '<span style="color:#34d399">✓ Completado</span>',
  stopped: '<span style="color:#fdba74">■ Detenido</span>',
  error:   '<span style="color:#f87171">✗ Error</span>',
  running: '<span style="color:#60a5fa">● Ejecutando…</span>',
};
```

Replace with:

```js
const STATUS_LABELS = {
  done:    '<span style="color:#34d399">✓ Completado</span>',
  stopped: '<span style="color:#fdba74">■ Detenido</span>',
  partial: '<span style="color:#f59e0b">⚠ Parcial</span>',
  error:   '<span style="color:#f87171">✗ Error</span>',
  running: '<span style="color:#60a5fa">● Ejecutando…</span>',
};
```

- [ ] **Step 2: Add "Acciones" column header to the history table**

Find:
```html
          <th style="text-align:right; padding:0.4rem 0.5rem; font-weight:600;">Válidos</th>
```

Replace with:
```html
          <th style="text-align:right; padding:0.4rem 0.5rem; font-weight:600;">Válidos</th>
          <th style="text-align:center; padding:0.4rem 0.5rem; font-weight:600;">Acciones</th>
```

- [ ] **Step 3: Replace `makeHistoryRow` with icon-based version**

Find and replace the entire `makeHistoryRow` function:

```js
function makeHistoryRow(entry) {
  const tr = document.createElement('tr');
  tr.style.borderTop = '1px solid #2d3148';
  tr.dataset.jobId = entry.job_id;
  tr.addEventListener('mouseenter', () => tr.style.background = '#161926');
  tr.addEventListener('mouseleave', () => tr.style.background = '');

  const canAnalyze = (entry.valid_count ?? 0) > 0;

  const folderBtn = `<button onclick="event.stopPropagation(); handleFolder('${entry.job_id}')"
    title="Abrir carpeta / Descargar CSV"
    style="background:none; border:none; cursor:pointer; font-size:1.1rem; padding:0 0.3rem; opacity:0.8;"
    onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.8">📁</button>`;

  const analyzeBtn = canAnalyze
    ? `<button onclick="event.stopPropagation(); window.location='/analyze/${entry.job_id}'"
        title="Analizar resultados"
        style="background:none; border:none; cursor:pointer; font-size:1.1rem; padding:0 0.3rem; opacity:0.8;"
        onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.8">🔍</button>`
    : `<button disabled title="Sin resultados para analizar"
        style="background:none; border:none; font-size:1.1rem; padding:0 0.3rem; opacity:0.3; cursor:not-allowed;">🔍</button>`;

  tr.innerHTML = `
    <td style="padding:0.45rem 0.5rem; color:#64748b">${formatTime(entry.started_at)}</td>
    <td style="padding:0.45rem 0.5rem">${entry.city}</td>
    <td style="padding:0.45rem 0.5rem">${entry.category}</td>
    <td class="status-cell" style="padding:0.45rem 0.5rem">${STATUS_LABELS[entry.status] || entry.status}</td>
    <td class="valid-cell" style="padding:0.45rem 0.5rem; text-align:right; color:#f8fafc; font-weight:600">${entry.valid_count ?? '—'}</td>
    <td style="padding:0.45rem 0.5rem; text-align:center; white-space:nowrap">${folderBtn}${analyzeBtn}</td>
  `;
  return tr;
}
```

- [ ] **Step 4: Add `handleFolder` function** (before `makeHistoryRow`)

```js
function handleFolder(jobId) {
  if (isLocal) {
    fetch(`/open-folder/${jobId}`, { method: 'POST' });
  } else {
    window.location = `/download/${jobId}`;
  }
}
```

- [ ] **Step 5: Verify the server is running and reload**

```bash
uvicorn server:app --reload
```

Open http://localhost:8000. The history section (if entries exist) should show 📁 and 🔍 icons instead of clickable rows.

- [ ] **Step 6: Commit**

```bash
git add static/index.html
git commit -m "feat: replace history row-click with folder and analyze icons"
```

---

## Task 3: Add `partial` status to server.py

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Update the status assignment in `run()`**

Find this block inside the `run()` async function in `server.py`:

```python
        await proc.wait()
        if jobs[job_id]["status"] != "stopped":
            jobs[job_id]["status"] = "done" if proc.returncode == 0 else "error"
        _save_history()
```

Replace with:

```python
        await proc.wait()
        if jobs[job_id]["status"] != "stopped":
            if proc.returncode == 0:
                jobs[job_id]["status"] = "done"
            elif jobs[job_id].get("valid_count", 0) > 0:
                jobs[job_id]["status"] = "partial"
            else:
                jobs[job_id]["status"] = "error"
        _save_history()
```

- [ ] **Step 2: Update `setStatus` in index.html to handle `partial`**

Find in `static/index.html`:

```js
      badge.textContent =
        status === 'running' ? '● Ejecutando…' :
        status === 'done'    ? '✓ Completado'  :
        status === 'stopped' ? '■ Detenido'    : '✗ Error';
```

Replace with:

```js
      badge.textContent =
        status === 'running' ? '● Ejecutando…' :
        status === 'done'    ? '✓ Completado'  :
        status === 'stopped' ? '■ Detenido'    :
        status === 'partial' ? '⚠ Parcial'     : '✗ Error';
```

Also add `partial` to the badge CSS in the `<style>` block. Find:

```css
    .status-badge.stopped  { background: #451a03; color: #fdba74; display: inline-block; }
```

Replace with:

```css
    .status-badge.stopped  { background: #451a03; color: #fdba74; display: inline-block; }
    .status-badge.partial  { background: #451a03; color: #f59e0b; display: inline-block; }
```

Also update the `done|stopped` check for the download button. Find:

```js
        if (status === 'done' || status === 'stopped') {
```

Replace with:

```js
        if (status === 'done' || status === 'stopped' || status === 'partial') {
```

- [ ] **Step 3: Commit**

```bash
git add server.py static/index.html
git commit -m "feat: add partial job status for errors with valid records"
```

---

## Task 4: Create brand filter config and module

**Files:**
- Create: `config/excluded_brands.json`
- Create: `src/analyzer/__init__.py`
- Create: `src/analyzer/brand_filter.py`
- Create: `tests/test_brand_filter.py`

- [ ] **Step 1: Create `config/excluded_brands.json`**

```json
{
  "brands": [
    "Sfera",
    "Springfield",
    "Stradivarius",
    "Pull&Bear",
    "ZARA",
    "MANGO",
    "Adolfo Dominguez",
    "BIMBA Y LOLA",
    "Roberto Verino",
    "Women's Secret",
    "Calzedonia",
    "Parfois"
  ]
}
```

- [ ] **Step 2: Create `src/analyzer/__init__.py`**

Empty file (package marker).

- [ ] **Step 3: Create `src/analyzer/brand_filter.py`**

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import List


def load_brands(path: str) -> List[str]:
    """Lee la lista de marcas excluidas desde un fichero JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [str(b) for b in data.get("brands", [])]


def is_excluded(name: str, brands: List[str]) -> bool:
    """Devuelve True si el nombre contiene alguna marca (case-insensitive, subcadena)."""
    name_lower = name.lower()
    return any(brand.lower() in name_lower for brand in brands)
```

- [ ] **Step 4: Write failing tests for brand_filter**

Create `tests/test_brand_filter.py`:

```python
import json
import pytest
from src.analyzer.brand_filter import load_brands, is_excluded


def test_is_excluded_exact_match():
    brands = ["ZARA", "MANGO"]
    assert is_excluded("ZARA", brands) is True


def test_is_excluded_substring():
    brands = ["Adolfo Dominguez"]
    assert is_excluded("Adolfo Dominguez (Santiago de Compostela)", brands) is True


def test_is_excluded_case_insensitive():
    brands = ["ZARA"]
    assert is_excluded("zara kids", brands) is True


def test_is_not_excluded():
    brands = ["ZARA", "MANGO"]
    assert is_excluded("Tienda de zapatos", brands) is False


def test_is_excluded_empty_brands():
    assert is_excluded("ZARA", []) is False


def test_load_brands(tmp_path):
    config = tmp_path / "brands.json"
    config.write_text(json.dumps({"brands": ["ZARA", "MANGO"]}), encoding="utf-8")
    brands = load_brands(str(config))
    assert brands == ["ZARA", "MANGO"]


def test_load_brands_empty_file(tmp_path):
    config = tmp_path / "brands.json"
    config.write_text(json.dumps({}), encoding="utf-8")
    assert load_brands(str(config)) == []
```

- [ ] **Step 5: Run tests and verify they pass**

```bash
pytest tests/test_brand_filter.py -v
```

Expected output: all 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add config/excluded_brands.json src/analyzer/__init__.py src/analyzer/brand_filter.py tests/test_brand_filter.py
git commit -m "feat: add brand_filter module and excluded_brands config"
```

---

## Task 5: Create fingerprint module

**Files:**
- Create: `src/analyzer/fingerprint.py`
- Create: `tests/test_fingerprint.py`

- [ ] **Step 1: Write failing tests for detect_platform**

Create `tests/test_fingerprint.py`:

```python
from src.analyzer.fingerprint import detect_platform

SHOPIFY_HTML = '<script src="https://cdn.shopify.com/s/files/1/theme.js"></script>'
WOOCOMMERCE_HTML = '<link rel="stylesheet" href="/wp-content/plugins/woocommerce/assets/css/woocommerce.css">'
PRESTASHOP_HTML = '<script>var prestashop = {};</script>'
MAGENTO_HTML = '<script type="text/x-magento-init">{"*":{"mage/cookies":{}}}</script>'
SQUARESPACE_HTML = '<link href="https://static.squarespace.com/universal/styles.css">'
WIX_HTML = '<link href="https://static.wixstatic.com/frog/main.css">'
WEBFLOW_HTML = '<script src="https://uploads-ssl.webflow.com/main.js">'
GENERIC_STORE_HTML = '<button class="add-to-cart">Añadir al carrito</button>'
GENERIC_CHECKOUT_HTML = '<a href="/checkout">Checkout</a>'
PLAIN_HTML = '<html><body><p>Bienvenido a nuestra web corporativa</p></body></html>'


def test_detect_shopify():
    is_store, platform = detect_platform(SHOPIFY_HTML)
    assert is_store is True
    assert platform == "Shopify"


def test_detect_woocommerce():
    is_store, platform = detect_platform(WOOCOMMERCE_HTML)
    assert is_store is True
    assert platform == "WooCommerce"


def test_detect_prestashop():
    is_store, platform = detect_platform(PRESTASHOP_HTML)
    assert is_store is True
    assert platform == "PrestaShop"


def test_detect_magento():
    is_store, platform = detect_platform(MAGENTO_HTML)
    assert is_store is True
    assert platform == "Magento"


def test_detect_squarespace():
    is_store, platform = detect_platform(SQUARESPACE_HTML)
    assert is_store is True
    assert platform == "Squarespace"


def test_detect_wix():
    is_store, platform = detect_platform(WIX_HTML)
    assert is_store is True
    assert platform == "Wix"


def test_detect_webflow():
    is_store, platform = detect_platform(WEBFLOW_HTML)
    assert is_store is True
    assert platform == "Webflow"


def test_detect_generic_store_add_to_cart():
    is_store, platform = detect_platform(GENERIC_STORE_HTML)
    assert is_store is True
    assert platform == "Desconocida"


def test_detect_generic_store_checkout():
    is_store, platform = detect_platform(GENERIC_CHECKOUT_HTML)
    assert is_store is True
    assert platform == "Desconocida"


def test_not_a_store():
    is_store, platform = detect_platform(PLAIN_HTML)
    assert is_store is False
    assert platform is None
```

- [ ] **Step 2: Run tests and confirm they FAIL**

```bash
pytest tests/test_fingerprint.py -v
```

Expected: errors (module not yet created).

- [ ] **Step 3: Create `src/analyzer/fingerprint.py`**

```python
from __future__ import annotations

import asyncio
import logging
from typing import Optional, Tuple

import aiohttp

LOGGER = logging.getLogger(__name__)

# Platform fingerprints: list of (platform_name, signature_substring)
_PLATFORMS = [
    ("Shopify",      "cdn.shopify.com"),
    ("WooCommerce",  "woocommerce"),
    ("PrestaShop",   "prestashop"),
    ("Magento",      "mage/"),
    ("Magento",      "Magento"),
    ("Squarespace",  "static.squarespace.com"),
    ("Wix",          "static.wixstatic.com"),
    ("Webflow",      "webflow.com"),
]

# Generic ecommerce indicators (case-insensitive)
_STORE_INDICATORS = [
    "add-to-cart",
    "addtocart",
    "/checkout",
    "/cart",
    "/carrito",
    "añadir al carrito",
    "agregar al carrito",
    "data-product-id",
]

# Domains considered "social" (not a real website)
_SOCIAL_DOMAINS = ("instagram.com", "facebook.com", "fb.com")


def is_social_url(url: str) -> bool:
    """Devuelve True si la URL es de una red social (no se analiza)."""
    return any(d in url.lower() for d in _SOCIAL_DOMAINS)


def detect_platform(html: str) -> Tuple[bool, Optional[str]]:
    """Analiza HTML para determinar si es tienda online y qué plataforma usa.

    Returns:
        (is_store, platform) where platform is None if not a store,
        the platform name if known, or "Desconocida" if store but unknown platform.
    """
    for platform_name, signature in _PLATFORMS:
        if signature in html:
            return (True, platform_name)

    html_lower = html.lower()
    for indicator in _STORE_INDICATORS:
        if indicator in html_lower:
            return (True, "Desconocida")

    return (False, None)


async def fetch_page(url: str, timeout_s: int = 10) -> Optional[str]:
    """Descarga el HTML de una URL. Devuelve None en caso de error."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GoogleMaps-Scraper-Analyzer/1.0)"}
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(url, allow_redirects=True, ssl=False) as resp:
                if resp.status >= 400:
                    LOGGER.warning("HTTP %d para %s", resp.status, url)
                    return None
                return await resp.text(errors="replace")
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Error fetching %s: %s", url, exc)
        return None
```

- [ ] **Step 4: Run tests and confirm they PASS**

```bash
pytest tests/test_fingerprint.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/analyzer/fingerprint.py tests/test_fingerprint.py
git commit -m "feat: add fingerprint module for ecommerce platform detection"
```

---

## Task 6: Create analyzer CLI

**Files:**
- Create: `src/analyzer/cli.py`

- [ ] **Step 1: Create `src/analyzer/cli.py`**

```python
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import time
from pathlib import Path
from typing import List

import openpyxl

from src.analyzer.brand_filter import is_excluded, load_brands
from src.analyzer.fingerprint import detect_platform, fetch_page, is_social_url
from src.utils.logging import setup_logging

LOGGER = logging.getLogger(__name__)

# CSV field names (must match the scraper output)
_CSV_FIELDS = [
    "nombre", "telefono", "direccion", "web",
    "rating", "categoria", "source_query", "retrieved_at_utc", "maps_url",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Google Maps Scraper — Analyzer")
    parser.add_argument("--csv-path", required=True, help="Ruta al CSV de entrada")
    parser.add_argument(
        "--brands-path",
        default="config/excluded_brands.json",
        help="Ruta al JSON de marcas excluidas",
    )
    return parser


def _derive_xlsx_path(csv_path: str) -> str:
    return str(Path(csv_path).with_suffix(".xlsx"))


def _read_csv(csv_path: str) -> List[dict]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


async def _run(args: argparse.Namespace) -> None:
    start_ts = time.perf_counter()

    brands = load_brands(args.brands_path)
    LOGGER.info("Marcas excluidas cargadas: %d", len(brands))

    rows = _read_csv(args.csv_path)
    LOGGER.info("Registros en CSV: %d", len(rows))

    xlsx_path = _derive_xlsx_path(args.csv_path)

    metrics = {"filtered": 0, "analyzed": 0, "stores": 0, "errors": 0}
    analysis_rows: List[dict] = []

    for row in rows:
        nombre = row.get("nombre", "")
        web = row.get("web", "").strip()

        if is_excluded(nombre, brands):
            metrics["filtered"] += 1
            LOGGER.info("[filtrado] %s", nombre)
            _emit_stats(metrics)
            continue

        # Determine store status
        if not web or is_social_url(web):
            es_tienda = "-"
            tecnologia = "-"
        else:
            html = await fetch_page(web)
            if html is None:
                es_tienda = "-"
                tecnologia = "-"
                metrics["errors"] += 1
            else:
                is_store, platform = detect_platform(html)
                es_tienda = "Sí" if is_store else "No"
                tecnologia = platform if platform else "-"
                if is_store:
                    metrics["stores"] += 1

        metrics["analyzed"] += 1
        analysis_rows.append({**row, "es_tienda": es_tienda, "tecnologia": tecnologia})

        LOGGER.info(
            "[analizado] %s | web=%s | tienda=%s | plataforma=%s",
            nombre, web or "(sin web)", es_tienda, tecnologia,
        )
        _emit_stats(metrics)

    # Write XLSX
    wb = openpyxl.Workbook()

    # Sheet 1: original data
    ws1 = wb.active
    ws1.title = "Datos originales"
    if rows:
        headers = list(rows[0].keys())
        ws1.append(headers)
        for row in rows:
            ws1.append([row.get(h, "") for h in headers])

    # Sheet 2: analysis results
    ws2 = wb.create_sheet("Análisis")
    if analysis_rows:
        analysis_headers = list(analysis_rows[0].keys())
        ws2.append(analysis_headers)
        for row in analysis_rows:
            ws2.append([row.get(h, "") for h in analysis_headers])

    wb.save(xlsx_path)
    LOGGER.info("XLSX guardado: %s", xlsx_path)

    elapsed = time.perf_counter() - start_ts
    LOGGER.info(
        "── Resumen análisis ──\n"
        "total=%d filtrados=%d analizados=%d tiendas=%d errores=%d elapsed_s=%.2f",
        len(rows),
        metrics["filtered"],
        metrics["analyzed"],
        metrics["stores"],
        metrics["errors"],
        elapsed,
    )
    _emit_stats(metrics)


def _emit_stats(metrics: dict) -> None:
    LOGGER.info(
        "ASTATS filtered=%d analyzed=%d stores=%d errors=%d",
        metrics["filtered"], metrics["analyzed"], metrics["stores"], metrics["errors"],
    )


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
```

Note: The analyzer emits `ASTATS` (not `STATS`) so the frontend can distinguish analyzer stats from scraper stats.

- [ ] **Step 2: Quick smoke test — verify the module is importable**

```bash
python -c "from src.analyzer.cli import build_parser; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/analyzer/cli.py
git commit -m "feat: add analyzer CLI subprocess entry point"
```

---

## Task 7: Add analyzer routes to server.py

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Add `analyze_jobs` dict and imports**

After the existing `jobs: dict[str, dict] = {}` line, add:

```python
# analyze_job_id (== scraping job_id) -> {"lines": [...], "status": "running"|"done"|"error", "proc": Process|None, "xlsx_output": str}
analyze_jobs: dict[str, dict] = {}
```

- [ ] **Step 2: Add `GET /analyze/{job_id}` route**

Add after the existing `@app.get("/")` route:

```python
@app.get("/analyze/{job_id}", response_class=HTMLResponse)
async def analyze_page(job_id: str) -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "static" / "analyze.html").read_text(encoding="utf-8"))
```

- [ ] **Step 3: Add `POST /run-analyze/{job_id}` route**

```python
@app.post("/run-analyze/{job_id}")
async def run_analyze(job_id: str) -> dict:
    job = jobs.get(job_id)
    if not job:
        return {"error": "job not found"}

    csv_output = job.get("output", "")
    if not csv_output:
        return {"error": "no output path"}

    xlsx_output = csv_output.replace(".csv", ".xlsx")
    analyze_jobs[job_id] = {
        "status": "running",
        "lines": [],
        "proc": None,
        "xlsx_output": xlsx_output,
    }

    cmd = [
        sys.executable, "-u", "-m", "src.analyzer.cli",
        "--csv-path", csv_output,
        "--brands-path", "config/excluded_brands.json",
    ]

    async def run() -> None:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(BASE_DIR),
        )
        analyze_jobs[job_id]["proc"] = proc
        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            analyze_jobs[job_id]["lines"].append(line)
        await proc.wait()
        if analyze_jobs[job_id]["status"] != "stopped":
            analyze_jobs[job_id]["status"] = "done" if proc.returncode == 0 else "error"

    asyncio.create_task(run())
    return {"job_id": job_id, "xlsx_output": xlsx_output}
```

- [ ] **Step 4: Add `GET /analyze-stream/{job_id}` route**

```python
@app.get("/analyze-stream/{job_id}")
async def analyze_stream(job_id: str) -> StreamingResponse:
    if job_id not in analyze_jobs:
        async def not_found():
            yield "data: Job de análisis no encontrado\n\nevent: done\ndata: error\n\n"
        return StreamingResponse(not_found(), media_type="text/event-stream")

    async def event_generator():
        sent = 0
        while True:
            aj = analyze_jobs[job_id]
            lines = aj["lines"]
            while sent < len(lines):
                safe = lines[sent].replace("\n", " ")
                yield f"data: {safe}\n\n"
                sent += 1
            if aj["status"] != "running":
                yield f"event: done\ndata: {aj['status']}\n\n"
                break
            await asyncio.sleep(0.15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 5: Add `GET /brands` and `POST /brands` routes**

```python
BRANDS_PATH = BASE_DIR / "config" / "excluded_brands.json"


@app.get("/brands")
async def get_brands() -> dict:
    if not BRANDS_PATH.exists():
        return {"brands": []}
    return json.loads(BRANDS_PATH.read_text(encoding="utf-8"))


@app.post("/brands")
async def save_brands(payload: dict) -> dict:
    BRANDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRANDS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"status": "ok"}
```

Note: `payload: dict` requires adding the following import if not already present: FastAPI accepts `dict` bodies when the parameter is typed as `dict` — but with Python 3.9 and FastAPI's Pydantic validation, use `from typing import Any` and type as `Any`, then cast. Replace with:

```python
from typing import Any, Optional

@app.post("/brands")
async def save_brands(payload: Any = Body(...)) -> dict:
    BRANDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRANDS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"status": "ok"}
```

Add `Body` to the FastAPI import line:
```python
from fastapi import Body, FastAPI, Form
```

- [ ] **Step 6: Add `GET /download-xlsx/{job_id}` route**

```python
@app.get("/download-xlsx/{job_id}")
async def download_xlsx(job_id: str) -> FileResponse:
    aj = analyze_jobs.get(job_id)
    if not aj:
        return FileResponse("/dev/null")
    xlsx_path = BASE_DIR / aj["xlsx_output"]
    return FileResponse(
        str(xlsx_path),
        filename=xlsx_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
```

- [ ] **Step 7: Verify server starts without errors**

```bash
uvicorn server:app --reload
```

Expected: server starts, no import errors.

- [ ] **Step 8: Commit**

```bash
git add server.py
git commit -m "feat: add analyzer server routes (run-analyze, analyze-stream, brands, download-xlsx)"
```

---

## Task 8: Create static/analyze.html

**Files:**
- Create: `static/analyze.html`

- [ ] **Step 1: Create `static/analyze.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Analyzer — Google Maps Scraper</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f1117;
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem 1rem;
    }

    .topbar {
      width: 100%;
      max-width: 720px;
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .back-link {
      color: #6366f1;
      text-decoration: none;
      font-size: 0.85rem;
      font-weight: 500;
    }
    .back-link:hover { text-decoration: underline; }

    h1 {
      font-size: 1.3rem;
      font-weight: 600;
      color: #f8fafc;
      letter-spacing: -0.02em;
    }

    .card {
      background: #1e2130;
      border: 1px solid #2d3148;
      border-radius: 12px;
      padding: 1.75rem;
      width: 100%;
      max-width: 720px;
      margin-bottom: 1.25rem;
    }

    .section-title {
      font-size: 0.7rem;
      font-weight: 700;
      color: #4b5563;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 0.75rem;
      padding-bottom: 0.4rem;
      border-bottom: 1px solid #1e293b;
    }

    .source-info {
      font-size: 0.85rem;
      color: #94a3b8;
      margin-bottom: 1rem;
    }
    .source-info span {
      color: #f8fafc;
      font-weight: 500;
      font-family: "SF Mono", "Fira Code", monospace;
      font-size: 0.8rem;
    }

    label {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      font-size: 0.8rem;
      font-weight: 500;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    textarea {
      background: #0f1117;
      border: 1px solid #2d3148;
      border-radius: 8px;
      color: #e2e8f0;
      font-family: "SF Mono", "Fira Code", monospace;
      font-size: 0.8rem;
      padding: 0.55rem 0.75rem;
      outline: none;
      transition: border-color 0.15s;
      width: 100%;
      resize: vertical;
      height: 120px;
    }
    textarea:focus { border-color: #6366f1; }

    .actions {
      display: flex;
      gap: 0.75rem;
      margin-top: 1.25rem;
      align-items: center;
      flex-wrap: wrap;
    }

    button {
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.9rem;
      font-weight: 600;
      padding: 0.6rem 1.4rem;
      transition: opacity 0.15s, background 0.15s;
    }
    button:disabled { opacity: 0.45; cursor: not-allowed; }

    #btn-save-brands { background: #2d3148; color: #94a3b8; }
    #btn-save-brands:hover { background: #374162; }
    #btn-run   { background: #6366f1; color: #fff; }
    #btn-run:not(:disabled):hover   { background: #4f46e5; }
    #btn-dl    { background: #10b981; color: #fff; display: none; }
    #btn-dl:hover { background: #059669; }

    .status-badge {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.25rem 0.65rem;
      border-radius: 99px;
      display: none;
    }
    .status-badge.running  { background: #1e3a5f; color: #60a5fa; display: inline-block; }
    .status-badge.done     { background: #064e3b; color: #34d399; display: inline-block; }
    .status-badge.error    { background: #4c1d1d; color: #f87171; display: inline-block; }

    .stats-bar {
      display: none;
      margin-top: 1.1rem;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.5rem;
    }
    .stats-bar.visible { display: grid; }
    .stat {
      background: #161926;
      border: 1px solid #2d3148;
      border-radius: 8px;
      padding: 0.55rem 0.75rem;
      text-align: center;
    }
    .stat-value { font-size: 1.3rem; font-weight: 700; color: #f8fafc; display: block; }
    .stat-label { font-size: 0.65rem; color: #4b5563; text-transform: uppercase; letter-spacing: 0.05em; }

    .log-wrapper {
      margin-top: 1.25rem;
      background: #0a0c12;
      border: 1px solid #1e2130;
      border-radius: 10px;
      overflow: hidden;
    }
    .log-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem 0.85rem;
      background: #111827;
      border-bottom: 1px solid #1e2130;
      font-size: 0.75rem;
      color: #6b7280;
    }
    #log {
      font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
      font-size: 0.78rem;
      line-height: 1.6;
      padding: 0.85rem 1rem;
      height: 380px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .line { padding: 1px 0; }
    .line.INFO    { color: #94a3b8; }
    .line.WARNING { color: #f59e0b; }
    .line.ERROR   { color: #f87171; }
    .line.SUCCESS { color: #34d399; font-weight: 600; }

    #log::-webkit-scrollbar { width: 6px; }
    #log::-webkit-scrollbar-track { background: transparent; }
    #log::-webkit-scrollbar-thumb { background: #2d3148; border-radius: 3px; }

    .save-indicator {
      font-size: 0.75rem;
      color: #34d399;
      display: none;
      margin-left: 0.5rem;
    }
  </style>
</head>
<body>
  <div class="topbar">
    <a href="/" class="back-link">← Volver</a>
    <h1>Analizador de resultados</h1>
  </div>

  <div class="card">
    <div class="section-title">Origen</div>
    <div class="source-info">Fichero CSV: <span id="csv-source">—</span></div>

    <div class="section-title" style="margin-top:1.25rem;">Marcas excluidas</div>
    <label>
      Una marca por línea (case-insensitive, se excluyen negocios cuyo nombre contenga la marca)
      <textarea id="brands-area" placeholder="Cargando…"></textarea>
    </label>
    <div style="display:flex; align-items:center; margin-top:0.6rem;">
      <button id="btn-save-brands">Guardar marcas</button>
      <span class="save-indicator" id="save-ok">✓ Guardado</span>
    </div>

    <div class="actions">
      <button id="btn-run">▶ Iniciar análisis</button>
      <button id="btn-dl">↓ Descargar XLSX</button>
      <span class="status-badge" id="badge"></span>
    </div>

    <div class="stats-bar" id="stats-bar">
      <div class="stat">
        <span class="stat-value" id="stat-filtered">–</span>
        <span class="stat-label">Filtrados</span>
      </div>
      <div class="stat">
        <span class="stat-value" id="stat-analyzed">–</span>
        <span class="stat-label">Analizados</span>
      </div>
      <div class="stat">
        <span class="stat-value" id="stat-stores">–</span>
        <span class="stat-label">Tiendas</span>
      </div>
      <div class="stat">
        <span class="stat-value" id="stat-errors">–</span>
        <span class="stat-label">Errores</span>
      </div>
    </div>

    <div class="log-wrapper">
      <div class="log-header">
        <span>Log</span>
        <span id="line-count">0 líneas</span>
      </div>
      <div id="log"></div>
    </div>
  </div>

  <script>
    // Extract job_id from URL: /analyze/<job_id>
    const jobId = window.location.pathname.split('/').pop();

    const badge     = document.getElementById('badge');
    const btnRun    = document.getElementById('btn-run');
    const btnDl     = document.getElementById('btn-dl');
    const logEl     = document.getElementById('log');
    const lineCount = document.getElementById('line-count');
    const statsBar  = document.getElementById('stats-bar');
    const brandsArea = document.getElementById('brands-area');
    const saveOk    = document.getElementById('save-ok');
    const csvSource = document.getElementById('csv-source');

    const statFiltered  = document.getElementById('stat-filtered');
    const statAnalyzed  = document.getElementById('stat-analyzed');
    const statStores    = document.getElementById('stat-stores');
    const statErrors    = document.getElementById('stat-errors');

    let lineNum = 0;
    let es = null;

    // Load CSV source info from history
    async function loadJobInfo() {
      const res = await fetch('/history');
      const entries = await res.json();
      const entry = entries.find(e => e.job_id === jobId);
      if (entry) {
        csvSource.textContent = entry.output || '—';
      }
    }

    // Load brands
    async function loadBrands() {
      const res = await fetch('/brands');
      const data = await res.json();
      brandsArea.value = (data.brands || []).join('\n');
    }

    // Save brands
    document.getElementById('btn-save-brands').addEventListener('click', async () => {
      const brands = brandsArea.value
        .split('\n')
        .map(s => s.trim())
        .filter(s => s.length > 0);
      await fetch('/brands', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brands }),
      });
      saveOk.style.display = 'inline';
      setTimeout(() => { saveOk.style.display = 'none'; }, 2000);
    });

    function levelOf(text) {
      if (text.includes('| ERROR |'))   return 'ERROR';
      if (text.includes('| WARNING |')) return 'WARNING';
      return 'INFO';
    }

    function tryParseStats(text) {
      const m = text.match(/ASTATS filtered=(\d+)\s+analyzed=(\d+)\s+stores=(\d+)\s+errors=(\d+)/);
      if (m) {
        statFiltered.textContent = m[1];
        statAnalyzed.textContent = m[2];
        statStores.textContent   = m[3];
        statErrors.textContent   = m[4];
      }
    }

    function appendLine(text) {
      const div = document.createElement('div');
      div.className = 'line ' + levelOf(text);
      div.textContent = text;
      logEl.appendChild(div);
      lineNum++;
      lineCount.textContent = `${lineNum} línea${lineNum !== 1 ? 's' : ''}`;
      logEl.scrollTop = logEl.scrollHeight;
      tryParseStats(text);
    }

    function setStatus(status) {
      badge.className = 'status-badge ' + status;
      badge.textContent =
        status === 'running' ? '● Analizando…' :
        status === 'done'    ? '✓ Completado'  : '✗ Error';
      badge.style.display = 'inline-block';
    }

    btnRun.addEventListener('click', async () => {
      if (es) { es.close(); es = null; }
      btnRun.disabled = true;
      btnDl.style.display = 'none';
      logEl.innerHTML = '';
      lineNum = 0;
      lineCount.textContent = '0 líneas';
      [statFiltered, statAnalyzed, statStores, statErrors].forEach(el => el.textContent = '–');
      statsBar.classList.add('visible');
      setStatus('running');

      await fetch(`/run-analyze/${jobId}`, { method: 'POST' });

      es = new EventSource(`/analyze-stream/${jobId}`);
      es.onmessage = (ev) => appendLine(ev.data);

      es.addEventListener('done', (ev) => {
        es.close();
        const status = ev.data;
        setStatus(status);
        btnRun.disabled = false;
        if (status === 'done') {
          btnDl.style.display = 'inline-block';
          btnDl.onclick = () => { window.location = `/download-xlsx/${jobId}`; };
        }
      });

      es.onerror = () => {
        if (es.readyState === EventSource.CLOSED) return;
        appendLine('[error de conexión con el servidor]');
        es.close();
        btnRun.disabled = false;
        setStatus('error');
      };
    });

    loadJobInfo();
    loadBrands();
  </script>
</body>
</html>
```

- [ ] **Step 2: Navigate to `/analyze/<any_job_id>` and verify the page loads**

With the server running, open http://localhost:8000 and click 🔍 on a completed job. Verify:
- Page loads at `/analyze/<job_id>`
- CSV filename shows in the source info field
- Brands list is populated from `config/excluded_brands.json`
- "Iniciar análisis" button is present

- [ ] **Step 3: Commit**

```bash
git add static/analyze.html
git commit -m "feat: add analyze.html UI with SSE log and brand editor"
```

---

## Task 9: Update CLAUDE.md and TODO.md

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.claude/TODO.md`

- [ ] **Step 1: Update version and document analyzer in CLAUDE.md**

Update the version header at the top of `CLAUDE.md`:

```markdown
## Versión actual: 0.4
```

Update the "Estado actual" section date and add `src/analyzer/` to the file structure. Add under `### Servidor web`:

```markdown
### Analizador (Fase 6)

```bash
# Se lanza automáticamente desde la UI — /analyze/<job_id>
# También ejecutable directamente:
python -m src.analyzer.cli --csv-path out/fichero.csv
```

`src/analyzer/cli.py` lee un CSV de salida del scraper, filtra marcas (case-insensitive, subcadena), detecta tecnologías ecommerce mediante fingerprinting HTML con `aiohttp`, y genera un `.xlsx` con dos pestañas:
- **Sheet 1**: copia fiel del CSV original
- **Sheet 2**: registros no filtrados + columnas `es_tienda` y `tecnologia`
```

Add to file structure:
```
src/analyzer/
├── cli.py          # Punto de entrada del analizador
├── brand_filter.py # load_brands(), is_excluded()
└── fingerprint.py  # fetch_page(), detect_platform()

config/
└── excluded_brands.json  # Lista de marcas a excluir (editable desde UI)
```

Update dependencies section:
```
openpyxl>=3.1.0          # Generación de XLSX multi-hoja
aiohttp>=3.9.0           # Fetch de páginas web para fingerprinting
```

- [ ] **Step 2: Add Fases 6 and 7 to .claude/TODO.md**

Append to `.claude/TODO.md`:

```markdown
---

## Fase 6 — Valoraciones de Google Business (pendiente)

Para cada negocio en el CSV, scrapear sus reseñas individuales desde la ficha de Google Maps.

- Requiere navegar con Playwright a la sección de reseñas de cada negocio
- Paginar reseñas (click "Más reseñas")
- Extraer: autor, rating, fecha, texto, respuesta del negocio
- Guardar en una tercera hoja del XLSX o fichero separado

---

## Fase 7 — Consulta al Catastro (pendiente)

Para cada negocio con dirección física en España, consultar la Sede Electrónica del Catastro para obtener los metros cuadrados del inmueble.

- API pública del Catastro: `https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/`
- Geocodificar dirección → referencia catastral → datos del inmueble
- Columna adicional en Sheet 2: `metros_cuadrados`
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md .claude/TODO.md
git commit -m "docs: bump version to 0.4, document analyzer, add Fases 6-7 to roadmap"
```

---

## Self-Review Checklist

After writing this plan, checking against the spec:

- [x] History folder icon → Task 2
- [x] History analyze icon (valid_count > 0) → Task 2
- [x] `partial` status → Task 3
- [x] `config/excluded_brands.json` → Task 4
- [x] `brand_filter.py` with tests → Task 4
- [x] `fingerprint.py` with tests → Task 5
- [x] `src/analyzer/cli.py` → Task 6
- [x] Server routes (5 new routes) → Task 7
- [x] `static/analyze.html` → Task 8
- [x] `openpyxl` / `aiohttp` in requirements → Task 1
- [x] CLAUDE.md v0.4 + TODO.md Fases 6+7 → Task 9
- [x] XLSX Sheet 1 = original, Sheet 2 = analysis → Task 6
- [x] `ASTATS` format parsed by analyze.html → Tasks 6+8
- [x] Brand config editable via UI (save/load) → Tasks 7+8
- [x] Download XLSX button → Tasks 7+8
