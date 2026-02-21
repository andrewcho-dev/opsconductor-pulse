import { EmptyState, PageHeader } from "@/components/shared";

export default function ReportsPage({ embedded }: { embedded?: boolean }) {
  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader title="Reports" description="Reporting is coming soon." />
      )}
      <EmptyState
        title="Reports coming soon"
        description="We are building rich reporting for your fleet. Check back later."
      />
    </div>
  );
}
