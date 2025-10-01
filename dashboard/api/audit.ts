/**
 * Audit Trail API Client
 * Provides functions to interact with the audit logging system
 */

export interface AuditLog {
  log_id: string;
  timestamp: string;
  action_type: string;
  user: string;
  user_agent?: string;
  ip_address?: string;
  action_details: Record<string, unknown>;
  success: boolean;
  error_message?: string;
  execution_time_ms?: number;
}

export interface AuditLogFilters {
  action_type?: string;
  user?: string;
  start_date?: string;
  end_date?: string;
  status?: 'success' | 'failed' | 'all';
}

const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8089';

export async function getAuditLogs(
  filters: AuditLogFilters = {},
  limit = 100
): Promise<AuditLog[]> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    ...Object.entries(filters)
      .filter(([, v]) => v !== undefined && v !== 'all')
      .reduce((acc, [k, v]) => ({ ...acc, [k]: v as string }), {})
  });

  const response = await fetch(`${ORCHESTRATOR_URL}/api/audit/logs?${params}`);

  if (!response.ok) {
    throw new Error('Failed to fetch audit logs');
  }

  const data = await response.json();
  return data.logs || [];
}

export function exportAuditLogs(logs: AuditLog[], format: 'csv' | 'json') {
  if (format === 'json') {
    const blob = new Blob([JSON.stringify(logs, null, 2)], {
      type: 'application/json'
    });
    downloadBlob(blob, `audit_trail_${timestamp()}.json`);
  } else {
    const csv = convertToCSV(logs);
    const blob = new Blob([csv], { type: 'text/csv' });
    downloadBlob(blob, `audit_trail_${timestamp()}.csv`);
  }
}

function convertToCSV(logs: AuditLog[]): string {
  const headers = ['Timestamp', 'Action', 'User', 'Status', 'Details'];
  const rows = logs.map(log => [
    log.timestamp,
    log.action_type,
    log.user,
    log.success ? 'Success' : 'Failed',
    JSON.stringify(log.action_details)
  ]);

  return [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n');
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function timestamp(): string {
  return new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
}
