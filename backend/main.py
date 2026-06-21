"""
backend/main.py

ScholarForge — Phase 10: FastAPI Backend

Exposes the full pipeline (Phases 2-9) over HTTP:
    POST /upload-paper    -> upload a PDF, kicks off the pipeline in the
                             background, returns a job_id immediately
    GET  /status/{job_id} -> current stage + progress percent
    GET  /result/{job_id} -> full pipeline result, once done
    GET  /health          -> health check (used by Render.com)

Jobs are tracked in a simple in-memory dict. That's fine for a single-process
dev/demo deployment; a real production setup would use a database + queue
(e.g. Redis + Celery) so jobs survive a server restart and can scale across
multiple workers.
"""

import os
import sys
import uuid
import shutil
import traceback

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.join(os.path.dirname(__file__), "graph"))
from langgraph_pipeline import run_pipeline_with_progress  # noqa: E402

app = FastAPI(title="ScholarForge API")

# Set this on your Render service as an environment variable once you know
# your real Vercel project name, e.g. "scholarforge" if your URL is
# https://scholarforge.vercel.app — this single setting covers both your
# main production URL AND Vercel's per-deploy preview URLs (which look like
# scholarforge-git-main-yourname.vercel.app), since those change on every
# push and can't be listed individually in advance.
VERCEL_PROJECT_NAME = os.getenv("VERCEL_PROJECT_NAME", "scholarforge")

origins = ["http://localhost:3000"]
origin_regex = rf"https://{VERCEL_PROJECT_NAME}.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# job_id -> {status, stage, progress_percent, message, result}
jobs: dict = {}


def _process_job(job_id: str, pdf_path: str, github_token: str = "") -> None:
    """Runs in a background thread (via FastAPI's BackgroundTasks)."""
    jobs[job_id]["status"] = "running"
    jobs[job_id]["progress_percent"] = 0
    jobs[job_id]["message"] = "Starting pipeline..."

    def on_progress(node_name: str, step: int, total: int, message: str) -> None:
        jobs[job_id]["progress_percent"] = int((step / total) * 100)
        jobs[job_id]["stage"] = node_name
        jobs[job_id]["message"] = message or node_name

    try:
        result = run_pipeline_with_progress(
            pdf_path, github_token=github_token, progress_callback=on_progress
        )
        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress_percent"] = 100
        jobs[job_id]["result"] = result
        jobs[job_id]["message"] = result.get("status_message", "Pipeline complete.")
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["message"] = f"Pipeline failed: {e}"
        jobs[job_id]["error_trace"] = traceback.format_exc()
    finally:
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                pass


@app.post("/upload-paper")
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    github_token: str = Form(default=""),
):
    """
    github_token is the *uploader's own* GitHub Personal Access Token,
    submitted optionally via the form. If omitted, the pipeline still runs
    fully (parsing, codegen, evaluation) but skips the GitHub push step —
    it never falls back to the server operator's own token, so deployed
    visitors never accidentally push code into someone else's account.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    job_id = str(uuid.uuid4())
    pdf_path = os.path.join(UPLOAD_DIR, f"{job_id}.pdf")

    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    jobs[job_id] = {
        "status": "queued",
        "stage": "queued",
        "progress_percent": 0,
        "message": "Job queued.",
        "result": None,
    }

    background_tasks.add_task(_process_job, job_id, pdf_path, github_token)

    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "status": job["status"],
        "stage": job.get("stage", "queued"),
        "progress_percent": job["progress_percent"],
        "message": job["message"],
    }


@app.get("/result/{job_id}")
async def get_result(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "done":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not finished yet (status: {job['status']}).",
        )
    return job["result"]


@app.get("/health")
async def health():
    return {"status": "ok"}
