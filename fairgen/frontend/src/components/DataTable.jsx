import { useEffect, useMemo, useState } from "react";

function ApprovalChip({ approved }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
        approved ? "bg-emerald-100 text-emerald-700" : "bg-red-50 text-red-600"
      }`}
    >
      {approved ? "Approved" : "Denied"}
    </span>
  );
}

function formatColumnName(column) {
  return column
    .replace("applicant_id", "Applicant ID")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatCellValue(column, value) {
  if (column === "applicant_id") {
    const stringValue = String(value ?? "");
    return `...${stringValue.slice(-8)}`;
  }
  return String(value);
}

export default function DataTable({ rows, schema = [] }) {
  const [page, setPage] = useState(1);
  const [showIds, setShowIds] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const pageSize = 50;

  useEffect(() => {
    setPage(1);
  }, [rows]);

  const columns = useMemo(() => {
    const schemaColumns = schema.map((column) => column.name);
    const rowColumns = rows[0] ? Object.keys(rows[0]) : [];
    const baseColumns = schemaColumns.length ? schemaColumns : rowColumns;
    return showIds ? baseColumns : baseColumns.filter((column) => column !== "applicant_id");
  }, [rows, schema, showIds]);

  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const pagedRows = rows.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="overflow-hidden rounded-xl shadow-[0_4px_24px_rgba(0,100,100,0.22)]">
      <div className="flex flex-col gap-3 bg-gradient-to-r from-white/80 to-emerald-50/40 px-4 py-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-800">Synthetic Dataset Preview</h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Page {page} of {totalPages}. Showing {pagedRows.length} records per page.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            className="rounded-md bg-white/60 px-3 py-1 text-xs font-semibold text-slate-600 hover:bg-white transition shadow-[0_1px_8px_rgba(0,100,100,0.14)]"
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "Collapse table" : "Expand table"}
          </button>
          <button
            className="rounded-md bg-white/60 px-3 py-1 text-xs font-semibold text-slate-600 hover:bg-white transition shadow-[0_1px_8px_rgba(0,100,100,0.14)]"
            onClick={() => setShowIds((value) => !value)}
          >
            {showIds ? "Hide ID column" : "Show ID column"}
          </button>
        </div>
      </div>

      <div className={`overflow-auto transition-[max-height] duration-300 scrollbar-minimal ${expanded ? "max-h-[70vh]" : "max-h-[24rem]"}`}>
        <table className="min-w-full divide-y divide-slate-200/60 text-sm">
          <thead className="bg-white/50 text-left">
            <tr>
              {columns.map((column) => (
                <th key={column} className="px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  {formatColumnName(column)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white/30">
            {pagedRows.map((row, rowIndex) => (
              <tr key={row.applicant_id || `${page}-${rowIndex}`} className="align-top text-slate-700 hover:bg-white/40 transition">
                {columns.map((column) => (
                  <td key={`${row.applicant_id || rowIndex}-${column}`} className="px-4 py-2">
                    {column === "loan_approved" ? <ApprovalChip approved={row[column]} /> : formatCellValue(column, row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between bg-gradient-to-r from-white/80 to-emerald-50/40 px-4 py-2.5 text-sm text-slate-600">
        <span className="text-xs font-medium">{rows.length} total rows</span>
        <div className="flex items-center gap-2">
          <button
            className="rounded-md bg-white/60 px-3 py-1 text-xs font-semibold text-slate-600 disabled:opacity-40 hover:bg-white transition shadow-[0_1px_8px_rgba(0,100,100,0.14)]"
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            disabled={page === 1}
          >
            Prev
          </button>
          <button
            className="rounded-md bg-white/60 px-3 py-1 text-xs font-semibold text-slate-600 disabled:opacity-40 hover:bg-white transition shadow-[0_1px_8px_rgba(0,100,100,0.14)]"
            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            disabled={page === totalPages}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
