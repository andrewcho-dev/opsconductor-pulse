import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPatch, apiDelete } from "@/services/api/client";
import { PageHeader } from "@/components/shared";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDistanceToNow } from "date-fns";

type Broadcast = {
  id: string;
  title: string;
  body: string;
  type: "info" | "warning" | "update";
  active: boolean;
  pinned: boolean;
  created_at: string;
  expires_at?: string | null;
  is_banner?: boolean;
};

function useBroadcasts() {
  return useQuery({
    queryKey: ["operator-broadcasts"],
    queryFn: () => apiGet<Broadcast[]>("/api/v1/operator/broadcasts"),
  });
}

export default function BroadcastsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useBroadcasts();

  const [form, setForm] = useState<Partial<Broadcast>>({
    title: "",
    body: "",
    type: "info",
    active: true,
    pinned: false,
    is_banner: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: Partial<Broadcast>) => apiPost<Broadcast>("/api/v1/operator/broadcasts", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operator-broadcasts"] });
      setForm({ title: "", body: "", type: "info", active: true, pinned: false, is_banner: false });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Partial<Broadcast> & { id: string }) =>
      apiPatch<Broadcast>(`/api/v1/operator/broadcasts/${payload.id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["operator-broadcasts"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiDelete(`/api/v1/operator/broadcasts/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["operator-broadcasts"] }),
  });

  const sorted = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [data]);

  useEffect(() => {
    if (!form.title && !form.body) {
      setForm((prev) => ({ ...prev, type: "info", active: true, pinned: false, is_banner: false }));
    }
  }, [form.title, form.body]);

  return (
    <div className="space-y-6">
      <PageHeader title="Broadcasts" description="Create announcements and news for customers." />

      <Card>
        <CardHeader>
          <CardTitle>Create Broadcast</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={form.title ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Type</Label>
              <Select
                value={form.type ?? "info"}
                onValueChange={(val) => setForm((f) => ({ ...f, type: val as Broadcast["type"] }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                  <SelectItem value="update">Update</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="body">Body</Label>
            <Textarea
              id="body"
              rows={3}
              value={form.body ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-center gap-2">
              <Switch
                id="active"
                checked={form.active ?? true}
                onCheckedChange={(val) => setForm((f) => ({ ...f, active: val }))}
              />
              <Label htmlFor="active">Active</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                id="pinned"
                checked={form.pinned ?? false}
                onCheckedChange={(val) => setForm((f) => ({ ...f, pinned: val }))}
              />
              <Label htmlFor="pinned">Pinned</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                id="is_banner"
                checked={form.is_banner ?? false}
                onCheckedChange={(val) => setForm((f) => ({ ...f, is_banner: val }))}
              />
              <Label htmlFor="is_banner">Banner (top of app)</Label>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={() => createMutation.mutate(form)}
              disabled={!form.title || !form.body || createMutation.isPending}
            >
              {createMutation.isPending ? "Saving..." : "Create"}
            </Button>
            <Button variant="outline" onClick={() => setForm({ title: "", body: "", type: "info", active: true, pinned: false, is_banner: false })}>
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Existing Broadcasts</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Pinned</TableHead>
                <TableHead>Banner</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7}>Loading...</TableCell>
                </TableRow>
              ) : !sorted.length ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-muted-foreground">
                    No broadcasts yet.
                  </TableCell>
                </TableRow>
              ) : (
                sorted.map((b) => (
                  <TableRow key={b.id}>
                    <TableCell className="font-medium">{b.title}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{b.type}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={b.active ? "default" : "secondary"}>
                        {b.active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>{b.pinned ? "Yes" : "No"}</TableCell>
                    <TableCell>{b.is_banner ? "Yes" : "No"}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDistanceToNow(new Date(b.created_at), { addSuffix: true })}
                    </TableCell>
                    <TableCell className="text-right space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          updateMutation.mutate({
                            id: b.id,
                            active: !b.active,
                          })
                        }
                      >
                        {b.active ? "Deactivate" : "Activate"}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => deleteMutation.mutate(b.id)}
                      >
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
