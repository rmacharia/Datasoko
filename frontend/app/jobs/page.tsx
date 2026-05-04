"use client";

import { useEffect, useRef, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import { SystemContext } from "@/components/system-context";
import { useToast } from "@/components/toast-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { generateAdminReport, getAdminJobStatus, isApiError, type AdminJobStatusResponse } from "@/lib/api";

const jobSchema = z
  .object({
    businessId: z.string().optional(),
    weekStart: z.string().min(1, "Start date is required."),
    weekEnd: z.string().min(1, "End date is required."),
    sendWhatsapp: z.boolean().default(true),
  })
  .refine((value) => value.weekEnd >= value.weekStart, {
    message: "End date must be on or after start date.",
    path: ["weekEnd"],
  });

type JobForm = z.infer<typeof jobSchema>;

export default function JobsPage() {
  const router = useRouter();
  const { token, logout } = useAuth();
  const { activeBusinessId } = useOrg();
  const { pushToast } = useToast();
  const pollingRef = useRef<number | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<AdminJobStatusResponse | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<JobForm>({
    resolver: zodResolver(jobSchema),
    defaultValues: {
      businessId: activeBusinessId,
      weekStart: "",
      weekEnd: "",
      sendWhatsapp: true,
    },
  });

  const businessId = watch("businessId") || activeBusinessId;

  useEffect(() => {
    return () => {
      if (pollingRef.current !== null) {
        window.clearInterval(pollingRef.current);
      }
    };
  }, []);

  const stopPolling = () => {
    if (pollingRef.current !== null) {
      window.clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const pollJob = (id: string, authToken: string) => {
    stopPolling();

    const runPoll = async () => {
      try {
        const status = await getAdminJobStatus(authToken, id);
        setJob(status);

        if (status.status === "completed") {
          const waInfo = status.whatsapp?.sent ? " — WhatsApp sent" : status.whatsapp ? " — WhatsApp skipped" : "";
          pushToast(`Job ${id.slice(0, 8)} completed${waInfo}.`, "success");
          stopPolling();
        }
        if (status.status === "failed") {
          pushToast(`Job ${id.slice(0, 8)} failed.`, "danger");
          stopPolling();
        }
      } catch (pollError) {
        if (isApiError(pollError) && pollError.status === 401) {
          stopPolling();
          logout();
          router.replace("/login");
          return;
        }
        stopPolling();
        const message = isApiError(pollError) ? pollError.message : "Failed to poll job status.";
        setError(message);
        pushToast(message, "danger");
      }
    };

    void runPoll();
    pollingRef.current = window.setInterval(() => {
      void runPoll();
    }, 2000);
  };

  const onGenerate = async (values: JobForm) => {
    if (!token) {
      router.replace("/login");
      return;
    }

    setError(null);
    setJob(null);
    setJobId(null);
    stopPolling();

    try {
      const response = await generateAdminReport(token, {
        business_id: values.businessId?.trim() || activeBusinessId,
        week_start: values.weekStart,
        week_end: values.weekEnd,
        send_whatsapp: values.sendWhatsapp,
      });

      setJobId(response.job_id);
      pushToast(`Job queued: ${response.job_id.slice(0, 8)}`, "info");
      pollJob(response.job_id, token);
    } catch (requestError) {
      if (isApiError(requestError) && requestError.status === 401) {
        logout();
        router.replace("/login");
        return;
      }
      const message = isApiError(requestError) ? requestError.message : "Failed to trigger report generation.";
      setError(message);
      pushToast(message, "danger");
    }
  };

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <SystemContext
          title="Trigger Report Job"
          subtitle="Asynchronous generation with live status polling."
          businessId={businessId}
        />

        <section className="card p-6">
          <form className="grid gap-4 md:grid-cols-3" onSubmit={handleSubmit(onGenerate)}>
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

            <div className="md:col-span-3 flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  {...register("sendWhatsapp")}
                  className="h-4 w-4 rounded border-[var(--border)] accent-[var(--accent)]"
                />
                Send via WhatsApp on completion
              </label>
            </div>

            <div className="md:col-span-3 flex gap-3">
              <Button type="submit" variant="primary" disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : "Generate Report"}
              </Button>
            </div>
          </form>

          {error ? <p className="mt-4 text-sm text-[var(--danger)]">{error}</p> : null}
        </section>

        {jobId ? (
          <section className="mt-6 card p-5">
            <h2 className="text-lg font-semibold">Job Status</h2>
            <p className="mt-2 text-sm">
              Job ID: <code>{jobId}</code>
            </p>

            <p className="mt-2 text-sm">
              Status:{" "}
              <span className={job?.status === "completed" ? "badge badge-ok" : job?.status === "failed" ? "badge badge-danger" : "badge badge-warn"}>
                {job?.status ?? "queued"}
              </span>
            </p>

            {job?.error ? <p className="mt-2 text-sm text-[var(--danger)]">{job.error}</p> : null}

            {job?.result_summary ? (
              <dl className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
                <div>
                  <dt className="muted">Weekly Revenue</dt>
                  <dd className="font-medium">{String(job.result_summary.weekly_revenue ?? "n/a")}</dd>
                </div>
                <div>
                  <dt className="muted">Repeat Customers</dt>
                  <dd className="font-medium">{String(job.result_summary.repeat_customers ?? "n/a")}</dd>
                </div>
                <div>
                  <dt className="muted">Records Processed</dt>
                  <dd className="font-medium">{String(job.result_summary.records_processed ?? "n/a")}</dd>
                </div>
              </dl>
            ) : null}

            {job?.whatsapp ? (
              <div className="mt-4 rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.4)] p-3">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-base" aria-hidden="true">
                    {job.whatsapp.sent ? "✅" : "❌"}
                  </span>
                  <span className="font-medium">
                    {job.whatsapp.sent ? "WhatsApp delivered" : "WhatsApp not sent"}
                  </span>
                  {job.whatsapp.sid ? (
                    <code className="ml-auto text-xs muted">{job.whatsapp.sid}</code>
                  ) : null}
                </div>
                {job.whatsapp.error && !job.whatsapp.sent ? (
                  <p className="mt-1 text-xs text-[var(--danger)]">{job.whatsapp.error}</p>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}
      </main>
    </AuthGuard>
  );
}
