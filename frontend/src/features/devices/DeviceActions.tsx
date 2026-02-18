import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

interface DeviceActionsProps {
  canCreate: boolean;
  createDisabled: boolean;
  onCreate: () => void;
  onGuidedSetup?: () => void;
  onImport?: () => void;
}

export function DeviceActions({
  canCreate,
  createDisabled,
  onCreate,
  onGuidedSetup,
  onImport,
}: DeviceActionsProps) {
  if (!canCreate) return null;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-2">
            <span>
              <Button disabled={createDisabled} size="sm" onClick={onCreate}>
                <Plus className="h-4 w-4 mr-1" />
                Add Device
              </Button>
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onGuidedSetup}
              disabled={createDisabled}
            >
              Guided Setup
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onImport}
              disabled={createDisabled}
            >
              Import Devices
            </Button>
          </div>
        </TooltipTrigger>
        {createDisabled && (
          <TooltipContent>
            <p>Device limit reached. Remove devices or upgrade your plan.</p>
          </TooltipContent>
        )}
      </Tooltip>
    </TooltipProvider>
  );
}
