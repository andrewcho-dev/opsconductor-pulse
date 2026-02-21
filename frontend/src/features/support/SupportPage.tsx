import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SupportPage() {
  return (
    <div className="space-y-4">
      <PageHeader title="Support" description="Get help with OpsConductor Pulse." />

      <Card>
        <CardHeader>
          <CardTitle>Contact Support</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p>Email: <a className="text-primary underline" href="mailto:support@example.com">support@example.com</a></p>
          <p>Support form: <a className="text-primary underline" href="#">Coming soon</a></p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Documentation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p>
            Product docs: <a className="text-primary underline" href="#">View documentation</a>
          </p>
          <p>Knowledge base: <a className="text-primary underline" href="#">Coming soon</a></p>
        </CardContent>
      </Card>
    </div>
  );
}
