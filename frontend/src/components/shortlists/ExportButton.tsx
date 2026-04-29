"use client";

import type { ShortlistMember } from "@/types/api";

interface ExportButtonProps {
  shortlistId: string;
  members: ShortlistMember[];
  shortlistName: string;
}

export default function ExportButton({ members, shortlistName }: ExportButtonProps) {
  const handleExportCSV = () => {
    const header = "Name,UUID,Added By,Added At";
    const rows = members.map((m) =>
      [
        m.candidate_name ?? m.candidate_uuid,
        m.candidate_uuid,
        m.added_by,
        m.added_at,
      ]
        .map((v) => `"${String(v).replace(/"/g, '""')}"`)
        .join(",")
    );
    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${shortlistName.replace(/[^a-zA-Z0-9]/g, "_")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = () => {
    window.print();
  };

  return (
    <div className="flex gap-2 print:hidden">
      <button
        onClick={handleExportCSV}
        className="px-3 py-2 rounded-md bg-white border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm transition-colors"
      >
        Export CSV
      </button>
      <button
        onClick={handleExportPDF}
        className="px-3 py-2 rounded-md bg-white border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm transition-colors"
      >
        Export PDF
      </button>
    </div>
  );
}
