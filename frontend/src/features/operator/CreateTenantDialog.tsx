import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createTenant } from "@/services/api/tenants";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateTenantDialog({ open, onOpenChange }: Props) {
  const [tenantId, setTenantId] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const queryClient = useQueryClient();

  const generateSlug = (text: string): string =>
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .substring(0, 64);

  const handleNameChange = (value: string) => {
    setName(value);
    const generated = generateSlug(value);
    if (!tenantId || tenantId === generateSlug(name)) {
      setTenantId(generated);
    }
  };

  const mutation = useMutation({
    mutationFn: createTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants-summary"] });
      onOpenChange(false);
      setTenantId("");
      setName("");
      setEmail("");
    },
    onError: (error: any) => {
      console.error("Create tenant error:", error?.body || error?.response?.data);
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      tenant_id: tenantId,
      name,
      contact_email: email || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Tenant</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="name">Display Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="My Company Inc."
              required
            />
            <p className="text-xs text-muted-foreground mt-1">
              Human-readable name (spaces allowed)
            </p>
          </div>
          <div>
            <Label htmlFor="tenant_id">Tenant ID (URL Slug)</Label>
            <Input
              id="tenant_id"
              value={tenantId}
              onChange={(e) =>
                setTenantId(
                  e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "")
                )
              }
              placeholder="my-company"
              pattern="[a-z0-9][a-z0-9\\-]*[a-z0-9]|[a-z0-9]{1,2}"
              required
            />
            <p className="text-xs text-muted-foreground mt-1">
              Lowercase letters, numbers, hyphens only. Used in URLs.
            </p>
          </div>
          <div>
            <Label htmlFor="email">Contact Email (optional)</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@company.com"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating..." : "Create Tenant"}
            </Button>
          </div>
          {mutation.isError && (
            <p className="text-sm text-destructive">
              {(mutation.error as any)?.body?.detail ||
                (mutation.error as any)?.response?.data?.detail ||
                (mutation.error as Error).message ||
                "Failed to create tenant"}
            </p>
          )}
        </form>
      </DialogContent>
    </Dialog>
  );
}
