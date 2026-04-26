"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { SystemContext } from "@/components/system-context";
import { useToast } from "@/components/toast-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { JsonPanel } from "@/components/ui/json-panel";
import { WhatsAppPreview } from "@/components/whatsapp-preview";
import { getAdminReports, isApiError, type AdminReportsResponse } from "@/lib/api";

const reportSchema = z
  .object({
    businessId: z.string().optional(),
    weekStart: z.string().min(1, "Start date is required."),
    weekEnd: z.string().min(1, "End date is required."),
  })
  .refine((value) => value.weekEnd >= value.weekStart, {
    message: "End date must be on or after start date.",
    path: ["weekEnd"],
  });

type ReportForm = z.infer<typeof reportSchema>;

export default function ReportsPage() {
  const router = useRouter();
  const { token, logout } = useAuth();
  const { pushToast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<AdminReportsResponse | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ReportForm>({
    resolver: zodResolver(reportSchema),
    defaultValues: {
      businessId: "biz_001",
      weekStart: "",
      weekEnd: "",
    },
  });

  const businessId = watch("businessId") || "biz_001";

  const onSubmit = async (values: ReportForm) => {
    if (!token) {
      router.replace("/login");
      return;
    }

    setError(null);
    setReport(null);

    try {
      const response = await getAdminReports(token, {
        businessId: values.businessId?.trim() || "biz_001",
        weekStart: values.weekStart,
        weekEnd: values.weekEnd,
      });
      setReport(response);
      pushToast("Report preview loaded.", "success");
    } catch (requestError) {
      if (isApiError(requestError) && requestError.status === 401) {
        logout();
        router.replace("/login");
        return;
      }
      const message = isApiError(requestError) ? requestError.message : "Failed to fetch report preview.";
      setError(message);
      pushToast(message, "danger");
    }
  };

  const copyMessage = async () => {
    if (!report?.whatsapp_preview.message) {
      return;
    }
    try {
      await navigator.clipboard.writeText(report.whatsapp_preview.message);
      pushToast("WhatsApp message copied.", "success");
    } catch {
      const message = "Clipboard access failed. Copy manually from preview.";
      setError(message);
      pushToast(message, "warning");
    }
  };

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <SystemContext
          title="Report Preview"
          subtitle="Date-range report rendering. Structured backend output only."
          businessId={businessId}
        />

        <section className="card p-6">
          <form className="grid gap-4 md:grid-cols-3" onSubmit={handleSubmit(onSubmit)}>
            <label className="text-sm font-medium" htmlFor="businessId">
              Business ID (optional)
              <Input id="businessId" {...register("businessId")} />
            </label>

            <label className="text-sm font-medium" htmlFor="weekStart">
              Start Date
              <Input id="weekStart" type="date" {...register("weekStart")} />
            </label>

            <label className="text-sm font-medium" htmlFor="weekEnd">
              End Date
              <Input id="weekEnd" type="date" {...register("weekEnd")} />
            </label>

            <div className="md:col-span-3">
              {errors.weekStart ? <p className="text-sm text-[var(--danger)]">{errors.weekStart.message}</p> : null}
              {errors.weekEnd ? <p className="text-sm text-[var(--danger)]">{errors.weekEnd.message}</p> : null}
            </div>

            <div className="md:col-span-3">
              <Button type="submit" variant="primary" disabled={isSubmitting}>
                {isSubmitting ? "Loading..." : "Load Preview"}
              </Button>
            </div>
          </form>

          {error ? <p className="mt-4 text-sm text-[var(--danger)]">{error}</p> : null}
        </section>

        {report ? (
          <section className="mt-6 grid gap-4 lg:grid-cols-2">
            <WhatsAppPreview message={report.whatsapp_preview.message} onCopy={() => void copyMessage()} />

            <JsonPanel title="LLM Narration JSON" value={report.llm_narration_json ?? { status: "not_available" }} />

            <div className="lg:col-span-2">
              <JsonPanel title="Metrics JSON" value={report.metrics_json} defaultCollapsed={true} />
            </div>
          </section>
        ) : null}
      </main>
    </AuthGuard>
  );
}
