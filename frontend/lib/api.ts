// ScholarForge - API client
// Phase 1 placeholder. Will be filled in as backend endpoints come online.

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadPaper(file: File): Promise<{ job_id: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/upload-paper`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Upload failed: ${res.statusText}`);
  }

  return res.json();
}

export async function getStatus(jobId: string) {
  const res = await fetch(`${API_URL}/status/${jobId}`);
  if (!res.ok) throw new Error(`Status check failed: ${res.statusText}`);
  return res.json();
}

export async function getResult(jobId: string) {
  const res = await fetch(`${API_URL}/result/${jobId}`);
  if (!res.ok) throw new Error(`Result fetch failed: ${res.statusText}`);
  return res.json();
}
