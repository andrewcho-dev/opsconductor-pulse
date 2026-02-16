import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  addGroupMember,
  createDeviceGroup,
  createDynamicGroup,
  deleteDeviceGroup,
  deleteDynamicGroup,
  fetchDeviceGroups,
  fetchGroupMembersV2,
  removeGroupMember,
  updateDeviceGroup,
  updateDynamicGroup,
} from "@/services/api/devices";
import { fetchDevices } from "@/services/api/devices";
import { Badge } from "@/components/ui/badge";

export default function DeviceGroupsPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [isDynamic, setIsDynamic] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterTags, setFilterTags] = useState<string[]>([]);
  const [filterSiteId, setFilterSiteId] = useState("");
  const [selectedGroupId, setSelectedGroupId] = useState<string>("");
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [selectedDeviceId, setSelectedDeviceId] = useState("");

  const groupsQuery = useQuery({
    queryKey: ["device-groups"],
    queryFn: fetchDeviceGroups,
  });
  const devicesQuery = useQuery({
    queryKey: ["all-devices-minimal"],
    queryFn: () => fetchDevices({ limit: 500, offset: 0 }),
  });
  const membersQuery = useQuery({
    queryKey: ["device-group-members", selectedGroupId],
    queryFn: () => fetchGroupMembersV2(selectedGroupId),
    enabled: !!selectedGroupId,
  });

  useEffect(() => {
    if (groupId) {
      setSelectedGroupId(groupId);
      return;
    }
    if (!selectedGroupId && groupsQuery.data?.groups?.length) {
      setSelectedGroupId(groupsQuery.data.groups[0].group_id);
    }
  }, [groupId, groupsQuery.data?.groups, selectedGroupId]);

  const selectedGroup = useMemo(
    () => groupsQuery.data?.groups.find((group) => group.group_id === selectedGroupId),
    [groupsQuery.data?.groups, selectedGroupId]
  );

  useEffect(() => {
    if (!selectedGroup) return;
    setEditName(selectedGroup.name);
    setEditDescription(selectedGroup.description ?? "");
  }, [selectedGroup]);

  function resetForm() {
    setNewName("");
    setNewDescription("");
    setIsDynamic(false);
    setFilterStatus("");
    setFilterTags([]);
    setFilterSiteId("");
  }

  const createMutation = useMutation({
    mutationFn: createDeviceGroup,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-groups"] });
      setCreateOpen(false);
      resetForm();
    },
  });

  const createDynamicMutation = useMutation({
    mutationFn: createDynamicGroup,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-groups"] });
      setCreateOpen(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      name,
      description,
    }: {
      id: string;
      name?: string;
      description?: string;
    }) => {
      if (selectedGroup?.group_type === "dynamic") {
        await updateDynamicGroup(id, { name, description });
        return;
      }
      await updateDeviceGroup(id, { name, description });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-groups"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      selectedGroup?.group_type === "dynamic" ? deleteDynamicGroup(id) : deleteDeviceGroup(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-groups"] });
      if (selectedGroupId) {
        navigate("/device-groups");
        setSelectedGroupId("");
      }
    },
  });

  const addMemberMutation = useMutation({
    mutationFn: ({ gid, did }: { gid: string; did: string }) => addGroupMember(gid, did),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-group-members", selectedGroupId] });
      await queryClient.invalidateQueries({ queryKey: ["device-groups"] });
      setSelectedDeviceId("");
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: ({ gid, did }: { gid: string; did: string }) => removeGroupMember(gid, did),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-group-members", selectedGroupId] });
      await queryClient.invalidateQueries({ queryKey: ["device-groups"] });
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Device Groups" description="Create and manage reusable device groups." />

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Groups</CardTitle>
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              Create Group
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {(groupsQuery.data?.groups ?? []).map((group) => (
              <button
                key={group.group_id}
                className={`w-full rounded-md border p-3 text-left ${
                  selectedGroupId === group.group_id ? "border-primary" : "border-border"
                }`}
                onClick={() => {
                  setSelectedGroupId(group.group_id);
                  navigate(`/device-groups/${group.group_id}`);
                }}
              >
                <div className="flex items-center gap-2 font-medium">
                  <span>{group.name}</span>
                  {group.group_type === "dynamic" && (
                    <Badge variant="secondary">Dynamic</Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {group.description || "No description"}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Members: {group.member_count == null ? "-" : group.member_count}
                </div>
              </button>
            ))}
            {(groupsQuery.data?.groups ?? []).length === 0 && (
              <div className="text-sm text-muted-foreground">No groups created yet.</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{selectedGroup ? `Group: ${selectedGroup.name}` : "Select a group"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedGroup ? (
              <>
                <div className="grid gap-2">
                  <Label htmlFor="group-name">Group Name</Label>
                  <Input
                    id="group-name"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="group-description">Description</Label>
                  <Textarea
                    id="group-description"
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() =>
                      updateMutation.mutate({
                        id: selectedGroup.group_id,
                        name: editName,
                        description: editDescription,
                      })
                    }
                  >
                    Save
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => deleteMutation.mutate(selectedGroup.group_id)}
                  >
                    Delete
                  </Button>
                </div>

                {selectedGroup.group_type !== "dynamic" && (
                  <div className="grid gap-2">
                    <Label>Add Device</Label>
                    <div className="flex gap-2">
                      <select
                        className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                        value={selectedDeviceId}
                        onChange={(e) => setSelectedDeviceId(e.target.value)}
                      >
                        <option value="">Select a device</option>
                        {(devicesQuery.data?.devices ?? []).map((device) => (
                          <option key={device.device_id} value={device.device_id}>
                            {device.device_id}
                          </option>
                        ))}
                      </select>
                      <Button
                        disabled={!selectedDeviceId}
                        onClick={() =>
                          addMemberMutation.mutate({
                            gid: selectedGroup.group_id,
                            did: selectedDeviceId,
                          })
                        }
                      >
                        Add
                      </Button>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <Label>Members</Label>
                  {(membersQuery.data?.members ?? []).length === 0 ? (
                    <div className="text-sm text-muted-foreground">No members in this group.</div>
                  ) : (
                    membersQuery.data?.members.map((member) => (
                      <div
                        key={member.device_id}
                        className="flex items-center justify-between rounded-md border p-2"
                      >
                        <div>
                          <div className="font-medium">{member.device_id}</div>
                          <div className="text-xs text-muted-foreground">
                            {member.name} - {member.status}
                          </div>
                        </div>
                        {selectedGroup.group_type !== "dynamic" && (
                          <Button
                            variant="outline"
                            onClick={() =>
                              removeMemberMutation.mutate({
                                gid: selectedGroup.group_id,
                                did: member.device_id,
                              })
                            }
                          >
                            Remove
                          </Button>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </>
            ) : (
              <div className="text-sm text-muted-foreground">Select a group to view details.</div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Group</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid gap-2">
              <Label htmlFor="new-group-name">Group Name</Label>
              <Input
                id="new-group-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="new-group-description">Description</Label>
              <Textarea
                id="new-group-description"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              />
            </div>
            <div className="flex items-center justify-between gap-3 rounded-md border border-border p-3">
              <div>
                <Label>Dynamic Group</Label>
                <div className="text-xs text-muted-foreground">
                  Membership is resolved automatically from a filter.
                </div>
              </div>
              <Switch checked={isDynamic} onCheckedChange={setIsDynamic} />
            </div>
            {isDynamic && (
              <div className="space-y-2 rounded-md border border-border p-3">
                <Label>Status Filter</Label>
                <select
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <option value="">Any status</option>
                  <option value="ONLINE">ONLINE</option>
                  <option value="STALE">STALE</option>
                </select>

                <Label>Tags (comma-separated)</Label>
                <Input
                  value={filterTags.join(",")}
                  onChange={(e) =>
                    setFilterTags(e.target.value.split(",").map((t) => t.trim()).filter(Boolean))
                  }
                />

                <Label>Site ID</Label>
                <Input value={filterSiteId} onChange={(e) => setFilterSiteId(e.target.value)} />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={!newName.trim()}
              onClick={() =>
                isDynamic
                  ? createDynamicMutation.mutate({
                      name: newName.trim(),
                      description: newDescription || undefined,
                      query_filter: {
                        ...(filterStatus ? { status: filterStatus } : {}),
                        ...(filterTags.length ? { tags: filterTags } : {}),
                        ...(filterSiteId ? { site_id: filterSiteId } : {}),
                      },
                    })
                  : createMutation.mutate({
                      name: newName.trim(),
                      description: newDescription || undefined,
                    })
              }
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
