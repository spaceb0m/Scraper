# History, Auto-filenames & Adaptive Subdivision Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an adaptive subdivision toggle, auto-generated CSV filenames, and a persistent execution history to the web UI.

**Architecture:** Three independent changes — a CLI flag + form checkbox, a server-side slug generator replacing the manual output field, and a JSON-backed history store with two new endpoints and a history section in the UI.

**Tech Stack:** Python 3.9, FastAPI, asyncio, JSON (stdlib), unicodedata (stdlib), platform (stdlib), subprocess (stdlib), vanilla JS

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/cli.py` | Modify | Add `--adaptive-subdivision` bool flag |
| `server.py` | Modify | `_slugify`, `_make_output_path`, history load/save, metadata per job, `/history`, `/open-folder/{job_id}` |
| `static/index.html` | Modify | Checkbox toggle, remove output field, history section |
| `tests/test_server_utils.py` | Create | Unit tests for `_slugify`, `_make_output_path`, history endpoints |

---

## Task 1: `--adaptive-subdivision` flag in `src/cli.py`

**Files:**
- Modify: `src/cli.py`

- [ ] **Step 1: Add the argument to `build_parser`**

In `src/cli.py`, find `build_parser()` and add after the `--zones` argument:

```python
parser.add_argument(
    "--adaptive-subdivision", type=parse_bool, default=True,
    dest="adaptive_subdivision",
    help="Activar subdivisión adaptativa de sectores (default: true)",
)
```

- [ ] **Step 2: Use the flag in `_process_sector`**

In `src/cli.py`, find the line:

```python
needs_subdivision = not result.reached_end
```

Replace with:

```python
needs_subdivision = args.adaptive_subdivision and not result.reached_end
```

- [ ] **Step 3: Verify manually**

Run:
```bash
python -m src.cli --help
```
Expected: `--adaptive-subdivision` appears in the output.

- [ ] **Step 4: Commit**

```bash
git add src/cli.py
git commit -m "feat: add --adaptive-subdivision flag to cli"
```

---

## Task 2: `_slugify` and `_make_output_path` in `server.py`

**Files:**
- Modify: `server.py`
- Create: `tests/test_server_utils.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_server_utils.py`:

```python
from __future__ import annotations

import re

import pytest

from server import _make_output_path, _slugify


def test_slugify_removes_accents():
    assert _slugify("Santiago de Compostela, España") == "santiago_de_compostela_espana"


def test_slugify_lowercases():
    assert _slugify("MADRID") == "madrid"


def test_slugify_replaces_special_chars():
    assert _slugify("tiendas de ropa") == "tiendas_de_ropa"


def test_slugify_collapses_underscores():
    # comma + space → single _
    assert "__" not in _slugify("a, b")


def test_slugify_truncates_to_40():
    long_text = "a" * 60
    assert len(_slugify(long_text)) <= 40


def test_make_output_path_format():
    path = _make_output_path("Madrid, España", "restaurantes")
    assert re.match(
        r"out/madrid_espana_restaurantes_\d{8}_\d{6}\.csv", path
    ), f"Unexpected path: {path}"


def test_make_output_path_uses_out_prefix():
    path = _make_output_path("Vigo", "bares")
    assert path.startswith("out/")
    assert path.endswith(".csv")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_server_utils.py -v
```
Expected: `ImportError` or `AttributeError` — `_slugify` not defined yet.

- [ ] **Step 3: Add `_slugify` and `_make_output_path` to `server.py`**

Add these imports at the top of `server.py` (after existing imports):

```python
import json
import platform
import re
import subprocess
import unicodedata
from datetime import datetime, timezone
```

Add these functions before the `jobs` dict definition:

```python
def _slugify(text: str) -> str:
    """Convierte texto a slug ASCII seguro para nombres de fichero."""
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_text.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", lower)
    slug = slug.strip("_")
    return slug[:40]


def _make_output_path(city: str, category: str) -> str:
    """Genera una ruta única para el CSV basada en ciudad, categoría y timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"out/{_slugify(city)}_{_slugify(category)}_{ts}.csv"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_server_utils.py -v
```
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server_utils.py
git commit -m "feat: add _slugify and _make_output_path to server"
```

---

## Task 3: Job metadata and history persistence in `server.py`

**Files:**
- Modify: `server.py`
- Modify: `tests/test_server_utils.py`

- [ ] **Step 1: Add failing tests for history persistence**

Append to `tests/test_server_utils.py`:

```python
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from server import _load_history, _save_history


def test_save_and_load_history(tmp_path):
    import server
    # Backup and replace globals
    original_jobs = server.jobs.copy()
    original_path = server.HISTORY_PATH

    server.HISTORY_PATH = tmp_path / "history.json"
    server.jobs = {
        "job-1": {
            "city": "Madrid",
            "category": "bares",
            "started_at": "2026-03-25T10:00:00",
            "status": "done",
            "valid_count": 42,
            "output": "out/madrid_bares_20260325_100000.csv",
            "lines": ["log line"],
            "proc": None,
        }
    }

    _save_history()
    assert server.HISTORY_PATH.exists()

    server.jobs = {}
    _load_history()

    assert "job-1" in server.jobs
    assert server.jobs["job-1"]["city"] == "Madrid"
    assert server.jobs["job-1"]["valid_count"] == 42
    assert server.jobs["job-1"]["lines"] == []
    assert server.jobs["job-1"]["proc"] is None

    # Restore
    server.jobs = original_jobs
    server.HISTORY_PATH = original_path


def test_load_history_missing_file(tmp_path):
    import server
    original_path = server.HISTORY_PATH
    server.HISTORY_PATH = tmp_path / "nonexistent.json"
    server.jobs = {}
    _load_history()  # must not raise
    assert server.jobs == {}
    server.HISTORY_PATH = original_path


def test_load_history_corrupt_file(tmp_path):
    import server
    original_path = server.HISTORY_PATH
    corrupt = tmp_path / "history.json"
    corrupt.write_text("not valid json", encoding="utf-8")
    server.HISTORY_PATH = corrupt
    server.jobs = {}
    _load_history()  # must not raise
    assert server.jobs == {}
    server.HISTORY_PATH = original_path
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_server_utils.py::test_save_and_load_history -v
```
Expected: `ImportError` — `_load_history` not defined yet.

- [ ] **Step 3: Add history constants and functions to `server.py`**

Add after the `BASE_DIR` line:

```python
HISTORY_PATH = BASE_DIR / "out" / "history.json"
```

Add these functions after `_make_output_path`:

```python
def _load_history() -> None:
    """Carga el historial de ejecuciones desde disco al arrancar el servidor."""
    if not HISTORY_PATH.exists():
        return
    try:
        entries = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        for entry in entries:
            jobs[entry["job_id"]] = {
                "city": entry.get("city", ""),
                "category": entry.get("category", ""),
                "started_at": entry.get("started_at", ""),
                "status": entry.get("status", "done"),
                "valid_count": entry.get("valid_count", 0),
                "output": entry.get("output", ""),
                "lines": [],
                "proc": None,
            }
    except Exception:
        pass  # fichero corrupto — arrancar sin historial


def _save_history() -> None:
    """Persiste el historial de ejecuciones a disco."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "job_id": jid,
            "city": j.get("city", ""),
            "category": j.get("category", ""),
            "started_at": j.get("started_at", ""),
            "status": j["status"],
            "valid_count": j.get("valid_count", 0),
            "output": j.get("output", ""),
        }
        for jid, j in jobs.items()
        if j.get("started_at")
    ]
    HISTORY_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

Add the startup call at module level, after the `jobs` dict definition:

```python
_load_history()
```

- [ ] **Step 4: Update `POST /run` to store metadata and auto-generate filename**

Replace the existing `run_scraper` function signature and body in `server.py`:

```python
@app.post("/run")
async def run_scraper(
    city: str = Form(...),
    category: str = Form(...),
    headless: str = Form("true"),
    max_results: int = Form(0),
    slow_ms: int = Form(250),
    timeout_ms: int = Form(15000),
    concurrency: int = Form(3),
    adaptive_subdivision: str = Form("false"),
) -> dict:
    job_id = str(uuid.uuid4())
    output = _make_output_path(city, category)
    jobs[job_id] = {
        "city": city,
        "category": category,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "valid_count": 0,
        "output": output,
        "lines": [],
        "proc": None,
    }

    cmd = [
        sys.executable, "-u", "-m", "src.cli",
        "--city", city,
        "--category", category,
        "--output", output,
        "--headless", headless,
        "--max-results", str(max_results),
        "--slow-ms", str(slow_ms),
        "--timeout-ms", str(timeout_ms),
        "--concurrency", str(concurrency),
        "--adaptive-subdivision", adaptive_subdivision,
    ]

    async def run() -> None:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(BASE_DIR),
        )
        jobs[job_id]["proc"] = proc
        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            jobs[job_id]["lines"].append(line)
            # Actualizar valid_count en tiempo real desde líneas STATS
            m = re.search(r"valid=(\d+)", line)
            if m:
                jobs[job_id]["valid_count"] = int(m.group(1))
        await proc.wait()
        if jobs[job_id]["status"] != "stopped":
            jobs[job_id]["status"] = "done" if proc.returncode == 0 else "error"
        _save_history()

    asyncio.create_task(run())
    return {"job_id": job_id, "output": output}
```

- [ ] **Step 5: Update `POST /stop/{job_id}` to save history on stop**

Find the `stop_job` function and add `_save_history()` before the return:

```python
@app.post("/stop/{job_id}")
async def stop_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if not job:
        return {"error": "not found"}
    if job["status"] != "running":
        return {"status": job["status"]}
    job["status"] = "stopped"
    proc = job.get("proc")
    if proc and proc.returncode is None:
        proc.terminate()
    _save_history()
    return {"status": "stopped"}
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_server_utils.py -v
```
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add server.py tests/test_server_utils.py
git commit -m "feat: add history persistence and job metadata to server"
```

---

## Task 4: `/history` and `/open-folder` endpoints in `server.py`

**Files:**
- Modify: `server.py`
- Modify: `tests/test_server_utils.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_server_utils.py`:

```python
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_history_endpoint_returns_list():
    import server
    original = server.jobs.copy()
    server.jobs = {
        "j1": {
            "city": "Vigo",
            "category": "bares",
            "started_at": "2026-03-25T09:00:00+00:00",
            "status": "done",
            "valid_count": 10,
            "output": "out/vigo_bares_20260325_090000.csv",
            "lines": [],
            "proc": None,
        }
    }
    res = client.get("/history")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert data[0]["city"] == "Vigo"
    assert data[0]["valid_count"] == 10
    server.jobs = original


def test_history_excludes_jobs_without_started_at():
    import server
    original = server.jobs.copy()
    server.jobs = {
        "j-legacy": {
            "status": "done",
            "output": "out/foo.csv",
            "lines": [],
            "proc": None,
        }
    }
    res = client.get("/history")
    assert res.status_code == 200
    assert res.json() == []
    server.jobs = original
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_server_utils.py::test_history_endpoint_returns_list -v
```
Expected: `404` — endpoint not defined yet.

- [ ] **Step 3: Add `GET /history` endpoint to `server.py`**

Add after the `stop_job` endpoint:

```python
@app.get("/history")
async def history() -> list:
    return [
        {
            "job_id": jid,
            "city": j.get("city", ""),
            "category": j.get("category", ""),
            "started_at": j.get("started_at", ""),
            "status": j["status"],
            "valid_count": j.get("valid_count", 0),
            "output": j.get("output", ""),
        }
        for jid, j in reversed(list(jobs.items()))
        if j.get("started_at")
    ]
```

- [ ] **Step 4: Add `POST /open-folder/{job_id}` endpoint to `server.py`**

Add after the `/history` endpoint:

```python
@app.post("/open-folder/{job_id}")
async def open_folder(job_id: str) -> dict:
    job = jobs.get(job_id)
    if not job:
        return {"error": "not found"}
    output_path = BASE_DIR / job["output"]
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", "-R", str(output_path)])
        elif system == "Windows":
            subprocess.Popen(["explorer", str(output_path.parent)])
        else:
            subprocess.Popen(["xdg-open", str(output_path.parent)])
        return {"status": "ok"}
    except Exception as exc:
        return {"error": str(exc)}
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_server_utils.py -v
```
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add server.py tests/test_server_utils.py
git commit -m "feat: add /history and /open-folder endpoints"
```

---

## Task 5: UI — checkbox, remove output field, history section

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: Add adaptive subdivision checkbox to the form**

In `static/index.html`, find the closing `</div>` of the `.grid` div (after the concurrency input) and add a new row before it:

```html
        <label class="full" style="flex-direction:row; align-items:center; gap:0.6rem; cursor:pointer;">
          <input type="checkbox" name="adaptive_subdivision" value="true" checked
                 style="width:auto; accent-color:#6366f1; width:1rem; height:1rem;" />
          <span>Subdivisión adaptativa</span>
          <small style="color:#4b5563; text-transform:none; font-weight:400; font-size:0.75rem; margin-left:0.25rem">
            (subdivide sectores con alta densidad recursivamente)
          </small>
        </label>
```

- [ ] **Step 2: Remove the "Archivo de salida" field**

Find and delete these lines from the form:

```html
        <label class="full">
          Archivo de salida
          <input type="text" name="output" value="./out/resultado.csv" required />
        </label>
```

- [ ] **Step 3: Add history section HTML after the main card**

Find the closing `</div>` of the main `.card` div (before `<script>`) and add after it:

```html
  <div class="card" id="history-card" style="display:none; margin-top:1.5rem; max-width:720px; width:100%;">
    <div class="section-title">Historial de ejecuciones</div>
    <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
      <thead>
        <tr style="color:#4b5563; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em;">
          <th style="text-align:left; padding:0.4rem 0.5rem; font-weight:600;">Hora</th>
          <th style="text-align:left; padding:0.4rem 0.5rem; font-weight:600;">Ciudad</th>
          <th style="text-align:left; padding:0.4rem 0.5rem; font-weight:600;">Categoría</th>
          <th style="text-align:left; padding:0.4rem 0.5rem; font-weight:600;">Estado</th>
          <th style="text-align:right; padding:0.4rem 0.5rem; font-weight:600;">Válidos</th>
        </tr>
      </thead>
      <tbody id="history-body"></tbody>
    </table>
  </div>
```

- [ ] **Step 4: Add history JS to the script section**

Add these variables at the top of the `<script>` block, after the existing variable declarations:

```js
    const historyCard = document.getElementById('history-card');
    const historyBody = document.getElementById('history-body');
    const isLocal = ['localhost', '127.0.0.1', ''].includes(window.location.hostname);
    let currentHistoryRow = null;
```

Add these functions before the `btnClear` event listener:

```js
    const STATUS_LABELS = {
      done:    '<span style="color:#34d399">✓ Completado</span>',
      stopped: '<span style="color:#fdba74">■ Detenido</span>',
      error:   '<span style="color:#f87171">✗ Error</span>',
      running: '<span style="color:#60a5fa">● Ejecutando…</span>',
    };

    function formatTime(isoString) {
      if (!isoString) return '—';
      return isoString.substring(11, 19);
    }

    function makeHistoryRow(entry) {
      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      tr.style.borderTop = '1px solid #2d3148';
      tr.dataset.jobId = entry.job_id;
      tr.addEventListener('mouseenter', () => tr.style.background = '#161926');
      tr.addEventListener('mouseleave', () => tr.style.background = '');
      tr.addEventListener('click', () => {
        if (isLocal) {
          fetch(`/open-folder/${entry.job_id}`, { method: 'POST' });
        } else {
          window.location = `/download/${entry.job_id}`;
        }
      });
      tr.innerHTML = `
        <td style="padding:0.45rem 0.5rem; color:#64748b">${formatTime(entry.started_at)}</td>
        <td style="padding:0.45rem 0.5rem">${entry.city}</td>
        <td style="padding:0.45rem 0.5rem">${entry.category}</td>
        <td class="status-cell" style="padding:0.45rem 0.5rem">${STATUS_LABELS[entry.status] || entry.status}</td>
        <td class="valid-cell" style="padding:0.45rem 0.5rem; text-align:right; color:#f8fafc; font-weight:600">${entry.valid_count ?? '—'}</td>
      `;
      return tr;
    }

    async function loadHistory() {
      const res = await fetch('/history');
      const entries = await res.json();
      historyBody.innerHTML = '';
      for (const entry of entries) {
        historyBody.appendChild(makeHistoryRow(entry));
      }
      historyCard.style.display = entries.length > 0 ? 'block' : 'none';
    }

    function updateCurrentHistoryRow(validCount, status) {
      if (!currentHistoryRow) return;
      const validCell = currentHistoryRow.querySelector('.valid-cell');
      const statusCell = currentHistoryRow.querySelector('.status-cell');
      if (validCell) validCell.textContent = validCount;
      if (statusCell && status) statusCell.innerHTML = STATUS_LABELS[status] || status;
    }

    // Cargar historial al iniciar
    loadHistory();
```

- [ ] **Step 5: Wire the history row to the job lifecycle**

In the `form.addEventListener('submit', ...)` handler, find the line:

```js
      const { job_id } = await res.json();
```

Replace with:

```js
      const { job_id, output } = await res.json();
      currentJobId = job_id;

      // Añadir fila al historial inmediatamente
      const newEntry = {
        job_id,
        city: data.get('city'),
        category: data.get('category'),
        started_at: new Date().toISOString(),
        status: 'running',
        valid_count: 0,
        output,
      };
      currentHistoryRow = makeHistoryRow(newEntry);
      historyBody.prepend(currentHistoryRow);
      historyCard.style.display = 'block';
```

Find the line `currentJobId = job_id;` that comes after and **remove it** (it's now set above).

- [ ] **Step 6: Update history row on STATS and on job end**

In `tryParseProgress`, after updating the stat cells, add a call to update the history row. Find:

```js
        statErrors.textContent     = s[4];
        return;
```

Replace with:

```js
        statErrors.textContent     = s[4];
        updateCurrentHistoryRow(s[3], null);
        return;
```

In the `es.addEventListener('done', ...)` handler, add after `setStatus(status);`:

```js
        updateCurrentHistoryRow(statValid.textContent, status);
```

- [ ] **Step 7: Verify in browser**

Start the server:
```bash
uvicorn server:app --reload
```

Open `http://localhost:8000` and verify:
- The "Archivo de salida" field is gone
- The checkbox "Subdivisión adaptativa" appears checked by default
- Launch a scraper run — the history section appears with status "Ejecutando…"
- Valid count updates in real time
- On completion, status changes to "Completado"
- Restart the server — history persists
- Click a history row — Finder/Explorer opens at the CSV location

- [ ] **Step 8: Commit**

```bash
git add static/index.html
git commit -m "feat: UI — adaptive subdivision checkbox, auto filename, history section"
```

---

## Task 6: Version bump and final push

- [ ] **Step 1: Update version to 0.3**

In `README.md`, change the title line:
```
# Google Maps Scraper `v0.3`
```

In `CLAUDE.md`, change:
```
## Versión actual: 0.3
```

- [ ] **Step 2: Commit and push**

```bash
git add README.md CLAUDE.md
git commit -m "chore: bump version to 0.3"
git push origin main
```
