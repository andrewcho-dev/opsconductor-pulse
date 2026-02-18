import { useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { updateTenant, type Tenant, type TenantUpdate } from "@/services/api/tenants";
import { toast } from "sonner";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useFormDirtyGuard } from "@/hooks/use-form-dirty-guard";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { getErrorMessage } from "@/lib/errors";

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

const editTenantSchema = z.object({
  name: z.string().min(2, "Tenant name required").max(100),
  contact_email: z.string().email("Valid email required").optional().or(z.literal("")),
  contact_name: z.string().max(100).optional().or(z.literal("")),
  legal_name: z.string().max(100).optional().or(z.literal("")),
  phone: z.string().max(50).optional().or(z.literal("")),
  billing_email: z.string().email("Valid email required").optional().or(z.literal("")),
  industry: z.string().max(100).optional().or(z.literal("")),
  company_size: z.string().max(50).optional().or(z.literal("")),
  address_line1: z.string().max(200).optional().or(z.literal("")),
  address_line2: z.string().max(200).optional().or(z.literal("")),
  city: z.string().max(100).optional().or(z.literal("")),
  state_province: z.string().max(100).optional().or(z.literal("")),
  postal_code: z.string().max(32).optional().or(z.literal("")),
  country: z
    .string()
    .max(2, "Country must be 2 characters")
    .optional()
    .or(z.literal(""))
    .refine((v) => v == null || v === "" || v.length === 2, "Country must be 2 characters"),
  data_residency_region: z.string().optional().or(z.literal("")),
  support_tier: z.string().optional().or(z.literal("")),
  sla_level: z
    .string()
    .optional()
    .or(z.literal(""))
    .refine((v) => v === "" || Number.isFinite(Number(v)), "SLA level must be a number")
    .refine(
      (v) => v === "" || (Number(v) >= 0 && Number(v) <= 100),
      "SLA level must be between 0 and 100"
    ),
  stripe_customer_id: z.string().max(100).optional().or(z.literal("")),
  status: z.enum(["ACTIVE", "SUSPENDED"]),
});

type EditTenantFormValues = z.infer<typeof editTenantSchema>;

function mapTenantToFormValues(tenant: Tenant): EditTenantFormValues {
  const normalizedStatus: "ACTIVE" | "SUSPENDED" = tenant.status === "SUSPENDED" ? "SUSPENDED" : "ACTIVE";
  return {
    name: tenant.name || "",
    contact_email: tenant.contact_email || "",
    contact_name: tenant.contact_name || "",
    legal_name: tenant.legal_name || "",
    phone: tenant.phone || "",
    billing_email: tenant.billing_email || "",
    industry: tenant.industry || "",
    company_size: tenant.company_size || "",
    address_line1: tenant.address_line1 || "",
    address_line2: tenant.address_line2 || "",
    city: tenant.city || "",
    state_province: tenant.state_province || "",
    postal_code: tenant.postal_code || "",
    country: tenant.country || "",
    data_residency_region: tenant.data_residency_region || "",
    support_tier: tenant.support_tier || "",
    sla_level: tenant.sla_level != null ? String(tenant.sla_level) : "",
    stripe_customer_id: tenant.stripe_customer_id || "",
    status: normalizedStatus,
  };
}

export function EditTenantDialog({ tenant, open, onOpenChange }: Props) {
  const queryClient = useQueryClient();

  const form = useForm<EditTenantFormValues>({
    resolver: zodResolver(editTenantSchema),
    defaultValues: tenant ? mapTenantToFormValues(tenant) : undefined,
  });

  const { handleClose, showConfirm, confirmDiscard, cancelDiscard } = useFormDirtyGuard({
    form,
    onClose: () => onOpenChange(false),
  });

  useEffect(() => {
    if (!open) return;
    if (tenant) form.reset(mapTenantToFormValues(tenant));
  }, [form, open, tenant]);

  const mutation = useMutation({
    mutationFn: (data: TenantUpdate) => updateTenant(tenant!.tenant_id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants-summary"] });
      queryClient.invalidateQueries({ queryKey: ["tenant-stats", tenant?.tenant_id] });
      queryClient.invalidateQueries({ queryKey: ["tenant-detail", tenant?.tenant_id] });
      onOpenChange(false);
      toast.success("Tenant updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update tenant");
    },
  });

  const onSubmit = (values: EditTenantFormValues) => {
    const slaParsed = values.sla_level?.trim() ? Number.parseFloat(values.sla_level) : NaN;
    mutation.mutate({
      name: values.name,
      contact_email: values.contact_email?.trim() || undefined,
      contact_name: values.contact_name?.trim() || undefined,
      legal_name: values.legal_name?.trim() || undefined,
      phone: values.phone?.trim() || undefined,
      billing_email: values.billing_email?.trim() || undefined,
      industry: values.industry?.trim() || undefined,
      company_size: values.company_size?.trim() || undefined,
      address_line1: values.address_line1?.trim() || undefined,
      address_line2: values.address_line2?.trim() || undefined,
      city: values.city?.trim() || undefined,
      state_province: values.state_province?.trim() || undefined,
      postal_code: values.postal_code?.trim() || undefined,
      country: values.country ? values.country.trim().toUpperCase() : undefined,
      data_residency_region: values.data_residency_region || undefined,
      support_tier: values.support_tier || undefined,
      sla_level: Number.isFinite(slaParsed) ? slaParsed : undefined,
      stripe_customer_id: values.stripe_customer_id?.trim() || undefined,
      status: values.status,
    });
  };

  if (!tenant) return null;

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(openState) => {
          if (!openState) handleClose();
          else onOpenChange(true);
        }}
      >
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Tenant: {tenant.tenant_id}</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">Basic Info</legend>
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Display Name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="legal_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Legal Name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="contact_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Contact Name</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="contact_email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Contact Email</FormLabel>
                      <FormControl>
                        <Input type="email" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="phone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Phone</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="billing_email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Billing Email</FormLabel>
                      <FormControl>
                        <Input type="email" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </fieldset>

            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">Company Details</legend>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="industry"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Industry</FormLabel>
                      <Select
                        value={field.value || "none"}
                        onValueChange={(v) => field.onChange(v === "none" ? "" : v)}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select industry" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="none">Not set</SelectItem>
                          {INDUSTRY_OPTIONS.map((opt) => (
                            <SelectItem key={opt} value={opt}>
                              {opt}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="company_size"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Company Size</FormLabel>
                      <Select
                        value={field.value || "none"}
                        onValueChange={(v) => field.onChange(v === "none" ? "" : v)}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select size" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="none">Not set</SelectItem>
                          {COMPANY_SIZE_OPTIONS.map((opt) => (
                            <SelectItem key={opt} value={opt}>
                              {opt}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </fieldset>

            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">Address</legend>
              <FormField
                control={form.control}
                name="address_line1"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Address Line 1</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="address_line2"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Address Line 2</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="city"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>City</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="state_province"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>State/Province</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="postal_code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Postal Code</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="country"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Country (2-char)</FormLabel>
                      <FormControl>
                        <Input
                          maxLength={2}
                          {...field}
                          onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </fieldset>

            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">Operations</legend>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="data_residency_region"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Data Residency Region</FormLabel>
                      <Select
                        value={field.value || "none"}
                        onValueChange={(v) => field.onChange(v === "none" ? "" : v)}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select region" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="none">Not set</SelectItem>
                          {REGION_OPTIONS.map((opt) => (
                            <SelectItem key={opt} value={opt}>
                              {opt}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="support_tier"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Support Tier</FormLabel>
                      <Select
                        value={field.value || "none"}
                        onValueChange={(v) => field.onChange(v === "none" ? "" : v)}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select tier" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="none">Not set</SelectItem>
                          {SUPPORT_TIER_OPTIONS.map((opt) => (
                            <SelectItem key={opt} value={opt}>
                              {opt}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="sla_level"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>SLA Level</FormLabel>
                      <FormControl>
                        <Input type="number" step="0.01" placeholder="99.90" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="stripe_customer_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Stripe Customer ID</FormLabel>
                      <FormControl>
                        <Input placeholder="cus_..." {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={form.control}
                name="status"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Status</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="ACTIVE">Active</SelectItem>
                        <SelectItem value="SUSPENDED">Suspended</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </fieldset>

            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </div>

            {mutation.isError && (
              <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
            )}
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showConfirm} onOpenChange={cancelDiscard}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Discard changes?</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes. Are you sure you want to close without saving?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={cancelDiscard}>Keep Editing</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDiscard}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
