'use client';
import { useState } from 'react';

interface Payment {
  id: string;
  amount: number;
  status: string;
  failure_reason: string;
  failure_code: string;
  customer_email: string;
  retry_count: number;
  created_at: string;
  last_attempted_at: string | null;
}

interface Props {
  payments: Payment[];
  onSelectPayment: (id: string) => void;
}

const statusColors: Record<string, string> = {
  recovered: 'bg-green-100 text-green-800',
  failed_recovery: 'bg-red-100 text-red-800',
  skipped: 'bg-yellow-100 text-yellow-800',
  pending: 'bg-gray-100 text-gray-800',
};

export default function PaymentsTable({ payments, onSelectPayment }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-4 py-3 font-semibold text-gray-600">Payment ID</th>
            <th className="text-left px-4 py-3 font-semibold text-gray-600">Amount</th>
            <th className="text-left px-4 py-3 font-semibold text-gray-600">Status</th>
            <th className="text-left px-4 py-3 font-semibold text-gray-600">Failure</th>
            <th className="text-left px-4 py-3 font-semibold text-gray-600">Customer</th>
            <th className="text-left px-4 py-3 font-semibold text-gray-600">Retries</th>
            <th className="text-left px-4 py-3 font-semibold text-gray-600">Audit</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {payments.map((p) => (
            <tr key={p.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-gray-500">{p.id.slice(0, 18)}...</td>
              <td className="px-4 py-3 font-semibold">₹{(p.amount / 100).toFixed(2)}</td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[p.status] || statusColors.pending}`}>
                  {p.status.replace('_', ' ')}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{p.failure_code}</td>
              <td className="px-4 py-3 text-gray-600">{p.customer_email}</td>
              <td className="px-4 py-3 text-center">{p.retry_count}</td>
              <td className="px-4 py-3">
                <button
                  onClick={() => onSelectPayment(p.id)}
                  className="text-blue-600 hover:text-blue-800 font-medium text-xs underline"
                >
                  View Trail
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}