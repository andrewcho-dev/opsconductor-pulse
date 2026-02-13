import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

interface DeviceActionsProps {
  canCreate: boolean;
  createDisabled: boolean;
}

export function DeviceActions({ canCreate, createDisabled }: DeviceActionsProps) {
  if (!canCreate) return null;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span>
            <Button disabled={createDisabled} size="sm">
              <Plus className="h-4 w-4 mr-2" />
              New Device
            </Button>
          </span>
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
