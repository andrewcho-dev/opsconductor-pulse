import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared";
import { importDevicesCSV, type ImportResult } from "@/services/api/devices";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";

type PreviewRow = {
  row: number;
  device_id: string;
  name: string;
  model: string;
  site_id: string;
  tags: string;
  valid: boolean;
};

const DEVICE_ID_PATTERN = /^[a-z0-9][a-z0-9-_]*$/;

function parseCsvLine(line: string): string[] {
  const cols: string[] = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      cols.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  cols.push(cur);
  return cols.map((c) => c.trim());
}

export default function BulkImportPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");
  const [previewRows, setPreviewRows] = useState<PreviewRow[]>([]);
  const [errorRows, setErrorRows] = useState<Array<{ row: number; device_id: string; reason: string }>>([]);
  const [expandedErrors, setExpandedErrors] = useState(false);

  const validCount = useMemo(() => previewRows.filter((row) => row.valid).length, [previewRows]);
  const invalidCount = previewRows.length - validCount;

  const resultsColumns: ColumnDef<ImportResult["results"][number]>[] = useMemo(
    () => [
      { accessorKey: "row", header: "Row" },
      {
        accessorKey: "device_id",
        header: "Device ID",
        cell: ({ row }) => row.original.device_id ?? "—",
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => {
          const status = row.original.status;
          const variant =
            status === "ok"
              ? "default"
              : status === "error"
                ? "destructive"
                : "secondary";
          const label = status === "ok" ? "success" : status;
          return <Badge variant={variant}>{label}</Badge>;
        },
      },
      {
        id: "message",
        header: "Message",
        enableSorting: false,
        accessorFn: (r) => r.message ?? "",
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {row.original.message ?? "—"}
          </span>
        ),
      },
    ],
    []
  );

  function downloadTemplate() {
    const csv =
      'device_id,name,model,site_id,tags\nexample-device-001,My Sensor,sensor-v2,site-abc,"env=prod,region=us-east"\n';
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "device-import-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function parsePreview(file: File) {
    const text = await file.text();
    const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
    if (lines.length === 0) {
      setPreviewRows([]);
      return;
    }
    const header = parseCsvLine(lines[0]).map((h) => h.toLowerCase());
    const idx = {
      device_id: header.indexOf("device_id"),
      name: header.indexOf("name"),
      model: header.indexOf("model"),
      site_id: header.indexOf("site_id"),
      tags: header.indexOf("tags"),
    };
    const rows: PreviewRow[] = [];
    for (let i = 1; i < lines.length; i += 1) {
      const cols = parseCsvLine(lines[i]);
      const row: PreviewRow = {
        row: i,
        device_id: idx.device_id >= 0 ? cols[idx.device_id] || "" : "",
        name: idx.name >= 0 ? cols[idx.name] || "" : "",
        model: idx.model >= 0 ? cols[idx.model] || "" : "",
        site_id: idx.site_id >= 0 ? cols[idx.site_id] || "" : "",
        tags: idx.tags >= 0 ? cols[idx.tags] || "" : "",
        valid: true,
      };
      row.valid = !!row.device_id && DEVICE_ID_PATTERN.test(row.device_id);
      rows.push(row);
    }
    setPreviewRows(rows);
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setError("");
    setIsUploading(true);
    try {
      const response = await importDevicesCSV(selectedFile);
      setResult(response);
      const fallbackErrors =
        response.results
          .filter((row) => row.status === "error")
          .map((row) => ({
            row: row.row,
            device_id: row.device_id ?? "",
            reason: row.message ?? "Import failed",
          })) ?? [];
      const explicitErrors = (response as ImportResult & {
        errors?: Array<{ row: number; device_id: string; reason: string }>;
      }).errors ?? [];
      setErrorRows(explicitErrors.length > 0 ? explicitErrors : fallbackErrors);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setIsUploading(false);
    }
  }

  function downloadErrorReport() {
    const csv =
      "row,device_id,reason\n" +
      errorRows
        .map((row) => `${row.row},${row.device_id.replaceAll(",", " ")},${row.reason.replaceAll(",", " ")}`)
        .join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "device-import-errors.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Import Devices"
        description="Upload CSV with columns: device_id, name, model, site_id, tags."
      />

      {!result ? (
        <div className="space-y-3 rounded-md border border-border p-4">
          <Button variant="outline" onClick={downloadTemplate}>
            Download CSV Template
          </Button>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={async (event) => {
              const file = event.target.files?.[0] ?? null;
              setSelectedFile(file);
              setResult(null);
              setErrorRows([]);
              if (file) {
                await parsePreview(file);
              } else {
                setPreviewRows([]);
              }
            }}
          />
          <p className="text-sm text-muted-foreground">
            Required format: <code>device_id,name,model,site_id,tags</code>
          </p>
          {previewRows.length > 0 && (
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">
                {previewRows.length} rows total, {validCount} valid, {invalidCount} invalid
              </div>
              <div className="overflow-x-auto rounded border border-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/40">
                      <th className="px-2 py-1 text-left">device_id</th>
                      <th className="px-2 py-1 text-left">name</th>
                      <th className="px-2 py-1 text-left">model</th>
                      <th className="px-2 py-1 text-left">site_id</th>
                      <th className="px-2 py-1 text-left">tags</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.slice(0, 10).map((row) => (
                      <tr key={row.row} className="border-b border-border/40">
                        <td
                          className={`px-2 py-1 ${
                            row.valid ? "" : "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300"
                          }`}
                        >
                          {row.device_id}
                        </td>
                        <td className="px-2 py-1">{row.name}</td>
                        <td className="px-2 py-1">{row.model}</td>
                        <td className="px-2 py-1">{row.site_id}</td>
                        <td className="px-2 py-1">{row.tags}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {error && <div className="text-sm text-destructive">{error}</div>}
          <Button onClick={handleUpload} disabled={!selectedFile || isUploading || invalidCount > 0}>
            {isUploading ? "Importing..." : `Import ${validCount || 0} valid rows`}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-md border border-status-online/30 bg-status-online/10 p-3 text-sm">
            Imported {result.imported} of {result.total} devices
          </div>
          <DataTable
            columns={resultsColumns}
            data={result.results}
            isLoading={isUploading}
            emptyState={
              <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
                Upload a CSV file to see import results.
              </div>
            }
            manualPagination={false}
          />
          {errorRows.length > 0 && (
            <div className="space-y-2 rounded-md border border-status-critical/30 bg-status-critical/10 p-3">
              <div className="text-sm text-red-700 dark:text-red-300">
                {errorRows.length} rows failed to import
              </div>
              <Button variant="outline" size="sm" onClick={downloadErrorReport}>
                Download Error Report
              </Button>
              <details open={expandedErrors} onToggle={(e) => setExpandedErrors(e.currentTarget.open)}>
                <summary className="cursor-pointer text-sm text-muted-foreground">Show error rows</summary>
                <div className="mt-2 overflow-x-auto rounded border border-red-300/40">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-red-300/40">
                        <th className="px-2 py-1 text-left">Row</th>
                        <th className="px-2 py-1 text-left">Device ID</th>
                        <th className="px-2 py-1 text-left">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {errorRows.map((row) => (
                        <tr key={`${row.row}-${row.device_id}`} className="border-b border-red-300/20">
                          <td className="px-2 py-1">{row.row}</td>
                          <td className="px-2 py-1">{row.device_id || "-"}</td>
                          <td className="px-2 py-1">{row.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </div>
          )}
          <Button
            variant="outline"
            onClick={() => {
              setSelectedFile(null);
              setResult(null);
              setError("");
              setPreviewRows([]);
              setErrorRows([]);
            }}
          >
            Import Another File
          </Button>
        </div>
      )}
    </div>
  );
}
