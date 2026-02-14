import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  createUser,
  deleteUser,
  fetchUsers,
  sendPasswordReset,
} from "@/services/api/operator";

export default function UserListPage() {
  const qc = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [openCreate, setOpenCreate] = useState(false);
  const [form, setForm] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    temporary_password: "",
  });

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const usersQ = useQuery({
    queryKey: ["operator-users", search],
    queryFn: () => fetchUsers({ search, first: 0, max: 100 }),
  });

  const createMut = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operator-users"] });
      setOpenCreate(false);
      setForm({
        username: "",
        email: "",
        first_name: "",
        last_name: "",
        temporary_password: "",
      });
    },
  });
  const deleteMut = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["operator-users"] }),
  });
  const resetMut = useMutation({ mutationFn: sendPasswordReset });

  const users = useMemo(() => usersQ.data?.users || [], [usersQ.data]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Users</CardTitle>
          <Button onClick={() => setOpenCreate(true)}>Create User</Button>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="Search users"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <div className="rounded border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="text-left p-2">Username</th>
                  <th className="text-left p-2">Email</th>
                  <th className="text-left p-2">Name</th>
                  <th className="text-left p-2">Enabled</th>
                  <th className="text-left p-2">Email Verified</th>
                  <th className="text-left p-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t">
                    <td className="p-2">
                      <Link className="underline" to={`/operator/users/${u.id}`}>
                        {u.username}
                      </Link>
                    </td>
                    <td className="p-2">{u.email}</td>
                    <td className="p-2">{`${u.firstName || ""} ${u.lastName || ""}`.trim() || "-"}</td>
                    <td className="p-2">
                      <Badge variant={u.enabled ? "default" : "secondary"}>
                        {u.enabled ? "Enabled" : "Disabled"}
                      </Badge>
                    </td>
                    <td className="p-2">
                      <Badge variant={u.emailVerified ? "default" : "outline"}>
                        {u.emailVerified ? "Verified" : "Unverified"}
                      </Badge>
                    </td>
                    <td className="p-2">
                      <div className="flex gap-2">
                        <Button asChild size="sm" variant="outline">
                          <Link to={`/operator/users/${u.id}`}>View</Link>
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => resetMut.mutate(u.id)}
                        >
                          Send Password Reset
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => deleteMut.mutate(u.id)}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {usersQ.error ? (
            <p className="text-sm text-destructive">{(usersQ.error as Error).message}</p>
          ) : null}
        </CardContent>
      </Card>

      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create User</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid gap-2">
              <Label>Username</Label>
              <Input
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <div className="grid gap-2">
                <Label>First Name</Label>
                <Input
                  value={form.first_name}
                  onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
                />
              </div>
              <div className="grid gap-2">
                <Label>Last Name</Label>
                <Input
                  value={form.last_name}
                  onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label>Temporary Password</Label>
              <Input
                type="password"
                value={form.temporary_password}
                onChange={(e) =>
                  setForm((f) => ({ ...f, temporary_password: e.target.value }))
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenCreate(false)}>
              Cancel
            </Button>
            <Button
              disabled={createMut.isPending}
              onClick={() => createMut.mutate(form)}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
