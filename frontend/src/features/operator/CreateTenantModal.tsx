import { CreateTenantDialog } from "./CreateTenantDialog";

interface CreateTenantModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function CreateTenantModal({
  open,
  onOpenChange,
}: CreateTenantModalProps) {
  return <CreateTenantDialog open={open} onOpenChange={onOpenChange} />;
}
