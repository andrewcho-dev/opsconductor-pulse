import { useEffect, useState } from "react";
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
import { getErrorMessage } from "@/lib/errors";
import { createTenant } from "@/services/api/tenants";
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

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const createTenantSchema = z.object({
  tenant_id: z
    .string()
    .min(2, "Tenant ID is required")
    .max(64)
    .regex(/^[a-z0-9-]+$/, "Only lowercase letters, numbers, and hyphens"),
  name: z.string().min(2, "Tenant name is required").max(100),
  contact_email: z.string().email("Valid email required").optional().or(z.literal("")),
});

type CreateTenantFormValues = z.infer<typeof createTenantSchema>;

export function CreateTenantDialog({ open, onOpenChange }: Props) {
  const queryClient = useQueryClient();

  const generateSlug = (text: string): string =>
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .substring(0, 64);

  const form = useForm<CreateTenantFormValues>({
    resolver: zodResolver(createTenantSchema),
    defaultValues: { tenant_id: "", name: "", contact_email: "" },
  });

  const { handleClose, showConfirm, confirmDiscard, cancelDiscard } = useFormDirtyGuard({
    form,
    onClose: () => onOpenChange(false),
  });

  const watchedName = form.watch("name");
  const [prevName, setPrevName] = useState("");

  useEffect(() => {
    if (!open) return;
    form.reset({ tenant_id: "", name: "", contact_email: "" });
    setPrevName("");
  }, [form, open]);

  useEffect(() => {
    if (!open) return;
    const currentTenantId = form.getValues("tenant_id");
    const generatedSlug = generateSlug(watchedName || "");
    if (!currentTenantId || currentTenantId === generateSlug(prevName)) {
      form.setValue("tenant_id", generatedSlug, { shouldDirty: true });
    }
    setPrevName(watchedName || "");
  }, [form, open, prevName, watchedName]);

  const mutation = useMutation({
    mutationFn: createTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants-summary"] });
      onOpenChange(false);
      form.reset();
    },
    onError: (error: Error) => {
      console.error("Create tenant error:", getErrorMessage(error));
    },
  });

  const onSubmit = (values: CreateTenantFormValues) => {
    mutation.mutate({
      tenant_id: values.tenant_id,
      name: values.name,
      contact_email: values.contact_email?.trim() || undefined,
    });
  };

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(isOpen) => {
          if (!isOpen) handleClose();
          else onOpenChange(true);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Tenant</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Display Name</FormLabel>
                  <FormControl>
                    <Input placeholder="My Company Inc." {...field} />
                  </FormControl>
                  <div className="text-xs text-muted-foreground mt-1">
                    Human-readable name (spaces allowed)
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="tenant_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Tenant ID (URL Slug)</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="my-company"
                      {...field}
                      onChange={(e) => field.onChange(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                    />
                  </FormControl>
                  <div className="text-xs text-muted-foreground mt-1">
                    Lowercase letters, numbers, hyphens only. Used in URLs.
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="contact_email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Contact Email (optional)</FormLabel>
                  <FormControl>
                    <Input type="email" placeholder="admin@company.com" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Creating..." : "Create Tenant"}
              </Button>
            </div>
            {mutation.isError && (
              <p className="text-sm text-destructive">{getErrorMessage(mutation.error)}</p>
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
