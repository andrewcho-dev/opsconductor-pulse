"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fetchAccountTiers } from "@/services/api/operator";

export default function AccountTiersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["operator-account-tiers"],
    queryFn: fetchAccountTiers,
  });

  const tiers = data?.tiers ?? [];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Account Tiers"
        description="View tenant-level account tiers (limits, features, support, pricing)."
      />

      <Card>
        <CardContent className="pt-6">
          <div className="rounded-md border">
            <Table aria-label="Account tiers list">
              <TableHeader>
                <TableRow>
                  <TableHead>Tier ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Monthly</TableHead>
                  <TableHead>Annual</TableHead>
                  <TableHead>Sort</TableHead>
                  <TableHead>Active</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-sm text-muted-foreground">
                      Loading account tiers...
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading && tiers.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-sm text-muted-foreground">
                      No account tiers found.
                    </TableCell>
                  </TableRow>
                )}
                {tiers.map((t) => (
                  <TableRow key={t.tier_id}>
                    <TableCell className="font-mono text-sm">{t.tier_id}</TableCell>
                    <TableCell>{t.name}</TableCell>
                    <TableCell>${(t.monthly_price_cents / 100).toFixed(2)}</TableCell>
                    <TableCell>${(t.annual_price_cents / 100).toFixed(2)}</TableCell>
                    <TableCell>{t.sort_order}</TableCell>
                    <TableCell>
                      <Badge variant={t.is_active ? "default" : "secondary"}>
                        {t.is_active ? "ACTIVE" : "INACTIVE"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

