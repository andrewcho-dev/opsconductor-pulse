import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Building2, Loader2, Save } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  getOrganization,
  updateOrganization,
  type OrganizationUpdate,
} from "@/services/api/organization";

const INDUSTRY_OPTIONS = [
  "Manufacturing",
  "Agriculture",
  "Healthcare",
  "Energy & Utilities",
  "Logistics",
  "Retail",
  "Smart Buildings",
  "Technology",
  "Other",
] as const;

const COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"] as const;

export default function OrganizationPage({ embedded }: { embedded?: boolean }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["organization"],
    queryFn: getOrganization,
  });

  const updateMutation = useMutation({
    mutationFn: (payload: OrganizationUpdate) => updateOrganization(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["organization"] });
      toast.success("Organization updated");
    },
    onError: () => {
      toast.error("Failed to update organization");
    },
  });

  const [form, setForm] = useState<OrganizationUpdate>({
    name: "",
    legal_name: "",
    phone: "",
    billing_email: "",
    industry: "",
    company_size: "",
    address_line1: "",
    address_line2: "",
    city: "",
    state_province: "",
    postal_code: "",
    country: "",
  });

  useEffect(() => {
    if (!data) return;
    setForm({
      name: data.name ?? "",
      legal_name: data.legal_name ?? "",
      phone: data.phone ?? "",
      billing_email: data.billing_email ?? "",
      industry: data.industry ?? "",
      company_size: data.company_size ?? "",
      address_line1: data.address_line1 ?? "",
      address_line2: data.address_line2 ?? "",
      city: data.city ?? "",
      state_province: data.state_province ?? "",
      postal_code: data.postal_code ?? "",
      country: data.country ?? "",
    });
  }, [data]);

  const canSave = useMemo(() => {
    // Allow saving even if some fields are empty; backend does partial update.
    return !!data && !updateMutation.isPending;
  }, [data, updateMutation.isPending]);

  function setField<K extends keyof OrganizationUpdate>(key: K, value: OrganizationUpdate[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSave() {
    // Send only fields we manage; backend uses exclude_unset, but we have a full form.
    updateMutation.mutate({
      ...form,
      country: form.country ? form.country.trim().toUpperCase() : "",
    });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader
          title="Organization"
          description="Manage your company profile, address, and billing contact info."
        />
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-4 w-4" />
              Company Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="org-name">Name</Label>
              <Input
                id="org-name"
                value={form.name ?? ""}
                onChange={(e) => setField("name", e.target.value)}
                maxLength={200}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="org-legal-name">Legal Name</Label>
              <Input
                id="org-legal-name"
                value={form.legal_name ?? ""}
                onChange={(e) => setField("legal_name", e.target.value)}
                maxLength={200}
              />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="org-phone">Phone</Label>
                <Input
                  id="org-phone"
                  value={form.phone ?? ""}
                  onChange={(e) => setField("phone", e.target.value)}
                  maxLength={50}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="org-billing-email">Billing Email</Label>
                <Input
                  id="org-billing-email"
                  value={form.billing_email ?? ""}
                  onChange={(e) => setField("billing_email", e.target.value)}
                  maxLength={255}
                />
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Industry</Label>
                <Select
                  value={form.industry || "none"}
                  onValueChange={(v) => setField("industry", v === "none" ? "" : v)}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select industry" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Not set</SelectItem>
                    {INDUSTRY_OPTIONS.map((opt) => (
                      <SelectItem key={opt} value={opt}>
                        {opt}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Company Size</Label>
                <Select
                  value={form.company_size || "none"}
                  onValueChange={(v) =>
                    setField("company_size", v === "none" ? "" : (v as string))
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select size" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Not set</SelectItem>
                    {COMPANY_SIZES.map((opt) => (
                      <SelectItem key={opt} value={opt}>
                        {opt}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Address</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="addr1">Address Line 1</Label>
              <Input
                id="addr1"
                value={form.address_line1 ?? ""}
                onChange={(e) => setField("address_line1", e.target.value)}
                maxLength={200}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="addr2">Address Line 2</Label>
              <Input
                id="addr2"
                value={form.address_line2 ?? ""}
                onChange={(e) => setField("address_line2", e.target.value)}
                maxLength={200}
              />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="city">City</Label>
                <Input
                  id="city"
                  value={form.city ?? ""}
                  onChange={(e) => setField("city", e.target.value)}
                  maxLength={100}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="state">State/Province</Label>
                <Input
                  id="state"
                  value={form.state_province ?? ""}
                  onChange={(e) => setField("state_province", e.target.value)}
                  maxLength={100}
                />
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="postal">Postal Code</Label>
                <Input
                  id="postal"
                  value={form.postal_code ?? ""}
                  onChange={(e) => setField("postal_code", e.target.value)}
                  maxLength={20}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="country">Country (2-char)</Label>
                <Input
                  id="country"
                  value={form.country ?? ""}
                  onChange={(e) => setField("country", e.target.value.toUpperCase())}
                  maxLength={2}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Plan & Support</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            <div>
              <div className="text-sm text-muted-foreground">Data Residency Region</div>
              <div className="text-sm">{data?.data_residency_region ?? "—"}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Support Tier</div>
              <div className="text-sm">{data?.support_tier ?? "—"}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">SLA Level</div>
              <div className="text-sm">
                {data?.sla_level != null ? String(data.sla_level) : "—"}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={!canSave}>
          {updateMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save
        </Button>
      </div>
    </div>
  );
}

