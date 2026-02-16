import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchPreferences,
  updatePreferences,
  type UpdatePreferencesPayload,
} from "@/services/api/preferences";

export function usePreferences() {
  return useQuery({
    queryKey: ["preferences"],
    queryFn: fetchPreferences,
  });
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdatePreferencesPayload) => updatePreferences(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["preferences"] });
    },
  });
}

