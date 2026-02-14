import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared";
import { importDevicesCSV, type ImportResult } from "@/services/api/devices";

export default function BulkImportPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");

  async function handleUpload() {
    if (!selectedFile) return;
    setError("");
    setIsUploading(true);
    try {
      const response = await importDevicesCSV(selectedFile);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Import Devices"
        description="Upload CSV with columns: name, device_type, site_id (optional), tags (optional)."
      />

      {!result ? (
        <div className="space-y-3 rounded-md border border-border p-4">
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
          <p className="text-xs text-muted-foreground">
            Required format: <code>name,device_type,site_id,tags</code>
          </p>
          {error && <div className="text-sm text-destructive">{error}</div>}
          <Button onClick={handleUpload} disabled={!selectedFile || isUploading}>
            {isUploading ? "Importing..." : "Import CSV"}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-md border border-green-500/30 bg-green-500/10 p-3 text-sm">
            Imported {result.imported} of {result.total} devices
          </div>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-2 py-2 text-left">Row</th>
                  <th className="px-2 py-2 text-left">Name</th>
                  <th className="px-2 py-2 text-left">Status</th>
                  <th className="px-2 py-2 text-left">Detail</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((row) => (
                  <tr key={`${row.row}-${row.name}`} className="border-b border-border/50">
                    <td className="px-2 py-2">{row.row}</td>
                    <td className="px-2 py-2">{row.name || "-"}</td>
                    <td className="px-2 py-2">
                      {row.status === "ok" ? (
                        <span className="text-green-600">✓ ok</span>
                      ) : (
                        <span className="text-red-600">✗ error</span>
                      )}
                    </td>
                    <td className="px-2 py-2 text-xs">{row.device_id || row.message || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Button
            variant="outline"
            onClick={() => {
              setSelectedFile(null);
              setResult(null);
              setError("");
            }}
          >
            Import Another File
          </Button>
        </div>
      )}
    </div>
  );
}
