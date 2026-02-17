import { useEffect } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useOperatorUser, useUpdateOperatorUser } from "@/hooks/use-users";
import { useFormDirtyGuard } from "@/hooks/use-form-dirty-guard";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

interface EditUserDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

const editUserSchema = z.object({
  email: z.string().email("Valid email is required"),
  first_name: z.string().max(50).optional().or(z.literal("")),
  last_name: z.string().max(50).optional().or(z.literal("")),
  enabled: z.boolean(),
});

type EditUserFormValues = z.infer<typeof editUserSchema>;

export function EditUserDialog({ userId, open, onOpenChange, onSaved }: EditUserDialogProps) {
  const { data: user, isLoading } = useOperatorUser(userId);
  const updateMutation = useUpdateOperatorUser();

  const form = useForm<EditUserFormValues>({
    resolver: zodResolver(editUserSchema),
    defaultValues: { email: "", first_name: "", last_name: "", enabled: true },
  });

  const { handleClose, showConfirm, confirmDiscard, cancelDiscard } = useFormDirtyGuard({
    form,
    onClose: () => onOpenChange(false),
  });

  useEffect(() => {
    if (!open) return;
    if (user) {
      form.reset({
        email: user.email || "",
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        enabled: Boolean(user.enabled),
      });
    }
  }, [form, open, user]);

  const onSubmit = async (values: EditUserFormValues) => {
    try {
      await updateMutation.mutateAsync({
        userId,
        data: {
          first_name: values.first_name?.trim() || "",
          last_name: values.last_name?.trim() || "",
          email: values.email,
          enabled: values.enabled,
        },
      });
      onSaved();
    } catch {
      // mutation state shows error
    }
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
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
          </DialogHeader>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <div className="space-y-2">
                  <Label>Username</Label>
                  <Input value={user?.username || ""} disabled className="bg-muted" />
                </div>

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="first_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>First Name</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="last_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Last Name</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="enabled"
                render={({ field }) => (
                  <div className="flex items-center justify-between rounded-md border border-border p-3">
                    <div>
                      <Label className="text-sm">Enabled</Label>
                      <p className="text-xs text-muted-foreground">Disable to prevent login.</p>
                    </div>
                    <Switch checked={Boolean(field.value)} onCheckedChange={field.onChange} />
                  </div>
                )}
              />

              {updateMutation.isError && (
                <div className="text-sm text-destructive">{(updateMutation.error as Error).message}</div>
              )}

              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </DialogFooter>
              </form>
            </Form>
          )}
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
