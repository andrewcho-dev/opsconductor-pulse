import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  assignRole,
  fetchUserDetail,
  removeRole,
  resetUserPassword,
  sendPasswordReset,
  updateUser,
} from "@/services/api/operator";

const KNOWN_ROLES = ["customer", "operator", "admin"];

export default function UserDetailPage() {
  const { userId = "" } = useParams();
  const qc = useQueryClient();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [emailVerified, setEmailVerified] = useState(false);
  const [newRole, setNewRole] = useState("customer");
  const [password, setPassword] = useState("");
  const [temporary, setTemporary] = useState(true);

  const userQ = useQuery({
    queryKey: ["operator-user", userId],
    queryFn: () => fetchUserDetail(userId),
    enabled: !!userId,
  });

  const patchMut = useMutation({
    mutationFn: (payload: {
      first_name: string;
      last_name: string;
      enabled: boolean;
      email_verified: boolean;
    }) => updateUser(userId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["operator-user", userId] }),
  });
  const addRoleMut = useMutation({
    mutationFn: (role: string) => assignRole(userId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["operator-user", userId] }),
  });
  const removeRoleMut = useMutation({
    mutationFn: (role: string) => removeRole(userId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["operator-user", userId] }),
  });
  const setPasswordMut = useMutation({
    mutationFn: () => resetUserPassword(userId, password, temporary),
  });
  const sendResetMut = useMutation({ mutationFn: () => sendPasswordReset(userId) });

  const user = userQ.data;
  const roles: string[] = useMemo(() => {
    const raw = (user as { roles?: Array<{ name?: string } | string> } | undefined)?.roles || [];
    return raw.map((r) => (typeof r === "string" ? r : r.name || "")).filter(Boolean);
  }, [user]);

  useEffect(() => {
    if (!user) return;
    setFirstName(user.firstName || "");
    setLastName(user.lastName || "");
    setEnabled(!!user.enabled);
    setEmailVerified(!!user.emailVerified);
  }, [user]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>User Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm"><strong>Username:</strong> {user?.username || "-"}</p>
          <p className="text-sm"><strong>Email:</strong> {user?.email || "-"}</p>
          <div className="grid gap-2 md:grid-cols-2">
            <div className="grid gap-2">
              <Label>First Name</Label>
              <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label>Last Name</Label>
              <Input value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Label>Enabled</Label>
              <Switch checked={enabled} onCheckedChange={setEnabled} />
            </div>
            <div className="flex items-center gap-2">
              <Label>Email Verified</Label>
              <Switch checked={emailVerified} onCheckedChange={setEmailVerified} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={enabled ? "default" : "secondary"}>
              {enabled ? "Enabled" : "Disabled"}
            </Badge>
            <Badge variant={emailVerified ? "default" : "outline"}>
              {emailVerified ? "Email Verified" : "Email Unverified"}
            </Badge>
          </div>
          <Button
            onClick={() =>
              patchMut.mutate({
                first_name: firstName,
                last_name: lastName,
                enabled,
                email_verified: emailVerified,
              })
            }
          >
            Save Profile
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Roles</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {roles.map((role) => (
              <Badge key={role} variant="outline" className="flex items-center gap-2">
                {role}
                <button
                  type="button"
                  className="text-xs"
                  onClick={() => removeRoleMut.mutate(role)}
                >
                  Remove
                </button>
              </Badge>
            ))}
            {roles.length === 0 ? <p className="text-sm text-muted-foreground">No roles</p> : null}
          </div>
          <div className="flex items-center gap-2">
            <select
              className="h-9 rounded border px-2 text-sm"
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
            >
              {KNOWN_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <Button variant="outline" onClick={() => addRoleMut.mutate(newRole)}>
              Add Role
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Password Actions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 md:grid-cols-[1fr_auto]">
            <Input
              type="password"
              placeholder="New password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <div className="flex items-center gap-2">
              <Label>Temporary</Label>
              <Switch checked={temporary} onCheckedChange={setTemporary} />
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setPasswordMut.mutate()}>
              Set Password
            </Button>
            <Button variant="outline" onClick={() => sendResetMut.mutate()}>
              Send Reset Email
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
