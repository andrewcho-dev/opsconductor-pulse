import { useState, useEffect, type FormEvent } from "react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { updateTenant, type Tenant, type TenantUpdate } from "@/services/api/tenants";

interface Props {
  tenant: Tenant | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

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

const COMPANY_SIZE_OPTIONS = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"] as const;

const REGION_OPTIONS = [
  "us-east",
  "us-west",
  "eu-west",
  "eu-central",
  "ap-southeast",
  "ap-northeast",
] as const;

const SUPPORT_TIER_OPTIONS = ["developer", "standard", "business", "enterprise"] as const;

export function EditTenantDialog({ tenant, open, onOpenChange }: Props) {
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactName, setContactName] = useState("");
  const [legalName, setLegalName] = useState("");
  const [phone, setPhone] = useState("");
  const [billingEmail, setBillingEmail] = useState("");
  const [industry, setIndustry] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [addressLine1, setAddressLine1] = useState("");
  const [addressLine2, setAddressLine2] = useState("");
  const [city, setCity] = useState("");
  const [stateProvince, setStateProvince] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [country, setCountry] = useState("");
  const [dataResidencyRegion, setDataResidencyRegion] = useState("");
  const [supportTier, setSupportTier] = useState("");
  const [slaLevel, setSlaLevel] = useState("");
  const [stripeCustomerId, setStripeCustomerId] = useState("");
  const [status, setStatus] = useState("ACTIVE");

  const queryClient = useQueryClient();

  useEffect(() => {
    if (tenant) {
      setName(tenant.name);
      setContactEmail(tenant.contact_email || "");
      setContactName(tenant.contact_name || "");
      setLegalName(tenant.legal_name || "");
      setPhone(tenant.phone || "");
      setBillingEmail(tenant.billing_email || "");
      setIndustry(tenant.industry || "");
      setCompanySize(tenant.company_size || "");
      setAddressLine1(tenant.address_line1 || "");
      setAddressLine2(tenant.address_line2 || "");
      setCity(tenant.city || "");
      setStateProvince(tenant.state_province || "");
      setPostalCode(tenant.postal_code || "");
      setCountry(tenant.country || "");
      setDataResidencyRegion(tenant.data_residency_region || "");
      setSupportTier(tenant.support_tier || "");
      setSlaLevel(tenant.sla_level != null ? String(tenant.sla_level) : "");
      setStripeCustomerId(tenant.stripe_customer_id || "");
      setStatus(tenant.status);
    }
  }, [tenant]);

  const mutation = useMutation({
    mutationFn: (data: TenantUpdate) => updateTenant(tenant!.tenant_id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants-summary"] });
      queryClient.invalidateQueries({ queryKey: ["tenant-stats", tenant?.tenant_id] });
      queryClient.invalidateQueries({ queryKey: ["tenant-detail", tenant?.tenant_id] });
      onOpenChange(false);
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const slaParsed = slaLevel.trim() ? Number.parseFloat(slaLevel) : NaN;
    mutation.mutate({
      name,
      contact_email: contactEmail || undefined,
      contact_name: contactName || undefined,
      legal_name: legalName || undefined,
      phone: phone || undefined,
      billing_email: billingEmail || undefined,
      industry: industry || undefined,
      company_size: companySize || undefined,
      address_line1: addressLine1 || undefined,
      address_line2: addressLine2 || undefined,
      city: city || undefined,
      state_province: stateProvince || undefined,
      postal_code: postalCode || undefined,
      country: country ? country.trim().toUpperCase() : undefined,
      data_residency_region: dataResidencyRegion || undefined,
      support_tier: supportTier || undefined,
      sla_level: Number.isFinite(slaParsed) ? slaParsed : undefined,
      stripe_customer_id: stripeCustomerId || undefined,
      status,
    });
  };

  if (!tenant) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Tenant: {tenant.tenant_id}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <fieldset className="space-y-3 rounded-md border p-4">
            <legend className="px-1 text-sm font-medium">Basic Info</legend>
            <div className="space-y-2">
              <Label htmlFor="name">Display Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="legal_name">Legal Name</Label>
              <Input
                id="legal_name"
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="contact_name">Contact Name</Label>
                <Input
                  id="contact_name"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="contact_email">Contact Email</Label>
                <Input
                  id="contact_email"
                  type="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="billing_email">Billing Email</Label>
                <Input
                  id="billing_email"
                  type="email"
                  value={billingEmail}
                  onChange={(e) => setBillingEmail(e.target.value)}
                />
              </div>
            </div>
          </fieldset>

          <fieldset className="space-y-3 rounded-md border p-4">
            <legend className="px-1 text-sm font-medium">Company Details</legend>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Industry</Label>
                <Select
                  value={industry || "none"}
                  onValueChange={(v) => setIndustry(v === "none" ? "" : v)}
                >
                  <SelectTrigger>
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
                  value={companySize || "none"}
                  onValueChange={(v) => setCompanySize(v === "none" ? "" : v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select size" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Not set</SelectItem>
                    {COMPANY_SIZE_OPTIONS.map((opt) => (
                      <SelectItem key={opt} value={opt}>
                        {opt}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </fieldset>

          <fieldset className="space-y-3 rounded-md border p-4">
            <legend className="px-1 text-sm font-medium">Address</legend>
            <div className="space-y-2">
              <Label htmlFor="address_line1">Address Line 1</Label>
              <Input
                id="address_line1"
                value={addressLine1}
                onChange={(e) => setAddressLine1(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="address_line2">Address Line 2</Label>
              <Input
                id="address_line2"
                value={addressLine2}
                onChange={(e) => setAddressLine2(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="city">City</Label>
                <Input id="city" value={city} onChange={(e) => setCity(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="state_province">State/Province</Label>
                <Input
                  id="state_province"
                  value={stateProvince}
                  onChange={(e) => setStateProvince(e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="postal_code">Postal Code</Label>
                <Input
                  id="postal_code"
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="country">Country (2-char)</Label>
                <Input
                  id="country"
                  value={country}
                  onChange={(e) => setCountry(e.target.value.toUpperCase())}
                  maxLength={2}
                />
              </div>
            </div>
          </fieldset>

          <fieldset className="space-y-3 rounded-md border p-4">
            <legend className="px-1 text-sm font-medium">Operations</legend>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Data Residency Region</Label>
                <Select
                  value={dataResidencyRegion || "none"}
                  onValueChange={(v) => setDataResidencyRegion(v === "none" ? "" : v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select region" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Not set</SelectItem>
                    {REGION_OPTIONS.map((opt) => (
                      <SelectItem key={opt} value={opt}>
                        {opt}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Support Tier</Label>
                <Select
                  value={supportTier || "none"}
                  onValueChange={(v) => setSupportTier(v === "none" ? "" : v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select tier" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Not set</SelectItem>
                    {SUPPORT_TIER_OPTIONS.map((opt) => (
                      <SelectItem key={opt} value={opt}>
                        {opt}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="sla_level">SLA Level</Label>
                <Input
                  id="sla_level"
                  type="number"
                  step="0.01"
                  value={slaLevel}
                  onChange={(e) => setSlaLevel(e.target.value)}
                  placeholder="99.90"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="stripe_customer_id">Stripe Customer ID</Label>
                <Input
                  id="stripe_customer_id"
                  value={stripeCustomerId}
                  onChange={(e) => setStripeCustomerId(e.target.value)}
                  placeholder="cus_..."
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVE">Active</SelectItem>
                  <SelectItem value="SUSPENDED">Suspended</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </fieldset>

          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </div>

          {mutation.isError && (
            <p className="text-sm text-destructive">
              {(mutation.error as Error).message}
            </p>
          )}
        </form>
      </DialogContent>
    </Dialog>
  );
}
