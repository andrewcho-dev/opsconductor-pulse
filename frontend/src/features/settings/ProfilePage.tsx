import { useEffect, useState } from "react";
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useAuth } from "@/services/auth/AuthProvider";
import { usePreferences, useUpdatePreferences } from "@/hooks/use-preferences";
import { TIMEZONE_OPTIONS } from "@/services/api/preferences";
import { toast } from "sonner";
import { Loader2, Save, UserCircle } from "lucide-react";

export default function ProfilePage({ embedded }: { embedded?: boolean }) {
  const { user } = useAuth();
  const { data: preferences, isLoading } = usePreferences();
  const updateMutation = useUpdatePreferences();

  const [displayName, setDisplayName] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [digestFrequency, setDigestFrequency] = useState<
    "daily" | "weekly" | "disabled"
  >("disabled");

  useEffect(() => {
    if (preferences) {
      setDisplayName(preferences.display_name ?? "");
      setTimezone(preferences.timezone ?? "UTC");
      setDigestFrequency(
        (preferences.notification_prefs?.email_digest_frequency as
          | "daily"
          | "weekly"
          | "disabled") ?? "disabled"
      );
    }
  }, [preferences]);

  const handleSave = () => {
    updateMutation.mutate(
      {
        display_name: displayName || null,
        timezone,
        notification_prefs: {
          email_digest_frequency: digestFrequency,
        },
      },
      {
        onSuccess: () => {
          toast.success("Preferences saved", {
            description: "Your profile settings have been updated.",
          });
        },
        onError: () => {
          toast.error("Failed to save preferences", {
            description: "Please try again.",
          });
        },
      }
    );
  };

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
          title="Profile"
          description="Manage your display name, timezone, and notification preferences."
        />
      )}

      <div className="grid gap-4 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCircle className="h-4 w-4" />
              Personal Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="display-name">Display Name</Label>
              <Input
                id="display-name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Enter your display name"
                maxLength={100}
              />
              <p className="text-sm text-muted-foreground">
                This name will be shown in team views and activity logs.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                value={user?.email ?? ""}
                disabled
                readOnly
                className="bg-muted"
              />
              <p className="text-sm text-muted-foreground">
                Email is managed by your identity provider and cannot be changed here.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Timezone</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label htmlFor="timezone">Display timezone</Label>
            <Select value={timezone} onValueChange={setTimezone}>
              <SelectTrigger id="timezone" className="w-full">
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent>
                {TIMEZONE_OPTIONS.map((tz) => (
                  <SelectItem key={tz.value} value={tz.value}>
                    {tz.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Timestamps across the application will be displayed in this timezone.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notification Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <Label>Email Digest Frequency</Label>
              <RadioGroup
                value={digestFrequency}
                onValueChange={(v) =>
                  setDigestFrequency(v as "daily" | "weekly" | "disabled")
                }
                className="space-y-2"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="daily" id="digest-daily" />
                  <Label htmlFor="digest-daily" className="font-normal">
                    Daily summary
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="weekly" id="digest-weekly" />
                  <Label htmlFor="digest-weekly" className="font-normal">
                    Weekly summary
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="disabled" id="digest-disabled" />
                  <Label htmlFor="digest-disabled" className="font-normal">
                    Disabled (no email digests)
                  </Label>
                </div>
              </RadioGroup>
              <p className="text-sm text-muted-foreground">
                Receive a periodic summary of fleet activity and alerts to your email.
              </p>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Preferences
          </Button>
        </div>
      </div>
    </div>
  );
}

