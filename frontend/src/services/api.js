const API_BASE_URL = 'http://localhost:8000/api';

export async function fetchFiles() {
  const response = await fetch(`${API_BASE_URL}/files`);
  if (!response.ok) throw new Error('Failed to fetch files');
  return response.json();
}

export async function fetchMetadata(filename) {
  const response = await fetch(`${API_BASE_URL}/metadata/${encodeURIComponent(filename)}`);
  if (!response.ok) throw new Error('Failed to fetch metadata');
  return response.json();
}

export async function buildIndex(filename) {
  const response = await fetch(`${API_BASE_URL}/build-index/${encodeURIComponent(filename)}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to build index');
  return response.json();
}

export async function fetchSlice(request) {
  const response = await fetch(`${API_BASE_URL}/slice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch slice');
  }
  return response.json();
}

export async function fetchRange(params) {
  const query = new URLSearchParams(params).toString();
  const response = await fetch(`${API_BASE_URL}/range?${query}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch range');
  }
  return response.json();
}
