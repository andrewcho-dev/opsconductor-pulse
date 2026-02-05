import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { ApiError } from "@/services/api/client";

interface TestDeliveryButtonProps {
  onTest: () => Promise<unknown>;
  disabled?: boolean;
}

type TestStatus = "idle" | "success" | "error";

function formatError(error: unknown): string {
  if (!error) return "";
  if (error instanceof ApiError) {
    if (typeof error.body === "string") return error.body;
    if (error.body && typeof error.body === "object") {
      const detail = (error.body as { detail?: string }).detail;
      if (detail) return detail;
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Unknown error";
}

export function TestDeliveryButton({ onTest, disabled }: TestDeliveryButtonProps) {
  const [isTesting, setIsTesting] = useState(false);
  const [status, setStatus] = useState<TestStatus>("idle");
  const [message, setMessage] = useState("");
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, []);

  async function handleTest() {
    if (disabled || isTesting) return;
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setIsTesting(true);
    setStatus("idle");
    setMessage("");
    try {
      await onTest();
      setStatus("success");
      setMessage("Delivered");
      timerRef.current = window.setTimeout(() => {
        setStatus("idle");
        setMessage("");
      }, 3000);
    } catch (err) {
      setStatus("error");
      setMessage(formatError(err));
      timerRef.current = window.setTimeout(() => {
        setStatus("idle");
        setMessage("");
      }, 5000);
    } finally {
      setIsTesting(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleTest}
        disabled={disabled || isTesting}
      >
        {isTesting ? (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Testing...
          </>
        ) : (
          "Test"
        )}
      </Button>
      {status === "success" && (
        <span className="text-xs text-green-400">{message}</span>
      )}
      {status === "error" && (
        <span className="text-xs text-destructive">{message}</span>
      )}
    </div>
  );
}
