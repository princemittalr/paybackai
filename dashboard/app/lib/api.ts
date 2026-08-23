const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getStats() {
  const res = await fetch(`${API_BASE}/api/stats`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function getPayments(status?: string, limit = 20, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (status) params.append('status', status);
  const res = await fetch(`${API_BASE}/api/payments?${params}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch payments');
  return res.json();
}

export async function getPaymentAudit(paymentId: string) {
  const res = await fetch(`${API_BASE}/api/payments/${paymentId}/audit`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

export async function getBatchRun(runId: string) {
  const res = await fetch(`${API_BASE}/api/batch/${runId}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch batch run');
  return res.json();
}