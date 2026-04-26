"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { SystemContext } from "@/components/system-context";
import { useToast } from "@/components/toast-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  isApiError,
  uploadAdminWeekly,
  type AdminUploadWeeklyResponse,
  type UploadDatasetResult,
  type UploadIssue,
} from "@/lib/api";

const uploadSchema = z
  .object({
    businessId: z.string().min(1, "Business ID is required."),
    weekStart: z.string().min(1, "Start date is required."),
    weekEnd: z.string().min(1, "End date is required."),
    businessCurrency: z.string().min(3).max(3).default("KES"),
    excelFile: z.custom<File | undefined>((value) => {
      if (typeof File === "undefined") return true;
      return value === undefined || value instanceof File;
    }),
    mpesaFile: z.custom<File | undefined>((value) => {
      if (typeof File === "undefined") return true;
      return value === undefined || value instanceof File;
    }),
  })
  .refine((value) => Boolean(value.excelFile || value.mpesaFile), {
    message: "Attach at least one file (Excel and/or M-Pesa CSV).",
    path: ["excelFile"],
  })
  .refine((value) => value.weekEnd >= value.weekStart, {
    message: "End date must be on or after start date.",
    path: ["weekEnd"],
  });

type UploadForm = z.infer<typeof uploadSchema>;

export default function UploadPage() {
  const { token } = useAuth();
  const { pushToast } = useToast();
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AdminUploadWeeklyResponse | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<UploadForm>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      businessId: "biz_001",
      weekStart: "",
      weekEnd: "",
      businessCurrency: "KES",
      excelFile: undefined,
      mpesaFile: undefined,
    },
  });

  const excelName = watch("excelFile")?.name;
  const mpesaName = watch("mpesaFile")?.name;
  const businessId = watch("businessId") || "biz_001";

  const actionableErrors = useMemo(() => {
    if (!result) return [];

    const collect = (dataset: string, issues: UploadIssue[] | undefined) =>
      (issues ?? []).map((issue) => {
        const rowLabel = issue.row_number ? `row ${issue.row_number}` : "file-level";
        const suggestion = issue.suggestion ? ` Suggestion: ${issue.suggestion}` : "";
        return `[${dataset}] ${issue.rule_id} (${rowLabel}) ${issue.message}.${suggestion}`.trim();
      });

    return [...collect("excel", result.excel?.issues), ...collect("mpesa", result.mpesa?.issues)];
  }, [result]);

  const onSubmit = async (values: UploadForm) => {
    if (!token) {
      setError("You must log in with an admin token first.");
      return;
    }

    setError(null);
    setResult(null);
    setProgress(0);

    try {
      const response = await uploadAdminWeekly({
        token,
        businessId: values.businessId,
        weekStart: values.weekStart,
        weekEnd: values.weekEnd,
        businessCurrency: values.businessCurrency.toUpperCase(),
        excelFile: values.excelFile,
        mpesaFile: values.mpesaFile,
        onProgress: setProgress,
      });
      setProgress(100);
      setResult(response);
      pushToast("Upload and validation complete.", "success");
    } catch (uploadError: unknown) {
      setProgress(0);
      const message = isApiError(uploadError) ? uploadError.message : "Upload failed. Try again.";
      setError(message);
      pushToast(message, "danger");
    }
  };

  const copyActionableErrors = async () => {
    if (!actionableErrors.length) return;
    try {
      await navigator.clipboard.writeText(actionableErrors.join("\n"));
      pushToast("Actionable issues copied.", "success");
    } catch {
      const message = "Clipboard access failed. Copy manually from the error block.";
      setError(message);
      pushToast(message, "warning");
    }
  };

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <SystemContext
          title="Upload + Validate"
          subtitle="Ingestion intake with deterministic validation summaries."
          businessId={businessId}
        />

        <section className="card p-6">
          <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit(onSubmit)}>
            <label className="text-sm font-medium" htmlFor="businessId">
              Business ID
              <Input id="businessId" {...register("businessId")} />
            </label>

            <label className="text-sm font-medium" htmlFor="businessCurrency">
              Currency (3-char)
              <Input id="businessCurrency" maxLength={3} className="uppercase" {...register("businessCurrency")} />
            </label>

            <label className="text-sm font-medium" htmlFor="weekStart">
              Start Date
              <Input id="weekStart" type="date" {...register("weekStart")} />
            </label>

            <label className="text-sm font-medium" htmlFor="weekEnd">
              End Date
              <Input id="weekEnd" type="date" {...register("weekEnd")} />
            </label>

            <label className="text-sm font-medium" htmlFor="excelFile">
              Excel Sales (.xlsx/.xls)
              <Input
                id="excelFile"
                type="file"
                accept=".xlsx,.xls"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  setValue("excelFile", file, { shouldValidate: true });
                }}
              />
              <span className="mt-1 block text-xs muted">{excelName ?? "No file selected"}</span>
            </label>

            <label className="text-sm font-medium" htmlFor="mpesaFile">
              M-Pesa CSV (.csv)
              <Input
                id="mpesaFile"
                type="file"
                accept=".csv"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  setValue("mpesaFile", file, { shouldValidate: true });
                }}
              />
              <span className="mt-1 block text-xs muted">{mpesaName ?? "No file selected"}</span>
            </label>

            <div className="md:col-span-2">
              {errors.businessId ? <p className="text-sm text-[var(--danger)]">{errors.businessId.message}</p> : null}
              {errors.weekStart ? <p className="text-sm text-[var(--danger)]">{errors.weekStart.message}</p> : null}
              {errors.weekEnd ? <p className="text-sm text-[var(--danger)]">{errors.weekEnd.message}</p> : null}
              {errors.excelFile ? <p className="text-sm text-[var(--danger)]">{errors.excelFile.message}</p> : null}
            </div>

            <div className="md:col-span-2 flex items-center gap-3">
              <Button type="submit" variant="primary" disabled={isSubmitting}>
                {isSubmitting ? "Uploading..." : "Upload + Validate"}
              </Button>
              <div aria-live="polite" className="text-sm muted">
                {progress > 0 && progress < 100 ? `Upload progress: ${progress}%` : null}
              </div>
            </div>
          </form>

          {progress > 0 && progress < 100 ? (
            <div className="mt-4">
              <progress aria-label="Upload progress" className="h-2 w-full" max={100} value={progress} />
            </div>
          ) : null}

          {error ? <p className="mt-4 text-sm text-[var(--danger)]">{error}</p> : null}
        </section>

        {result ? (
          <section className="mt-6 grid gap-4 lg:grid-cols-2">
            <DatasetPanel title="Excel Sales" dataset={result.excel} />
            <DatasetPanel title="M-Pesa" dataset={result.mpesa} />

            <article className="card p-5 lg:col-span-2">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-semibold">Actionable Errors for SME Follow-Up</h2>
                <Button type="button" variant="ghost" onClick={() => void copyActionableErrors()} disabled={!actionableErrors.length}>
                  Copy Errors
                </Button>
              </div>

              {actionableErrors.length ? (
                <pre className="code-panel max-h-64 overflow-auto p-4 text-xs">{actionableErrors.join("\n")}</pre>
              ) : (
                <p className="text-sm muted">No validation issues detected.</p>
              )}
            </article>
          </section>
        ) : null}
      </main>
    </AuthGuard>
  );
}

function DatasetPanel({ title, dataset }: { title: string; dataset: UploadDatasetResult | null }) {
  if (!dataset) {
    return (
      <article className="card p-5">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm muted">Not uploaded in this run.</p>
      </article>
    );
  }

  return (
    <article className="card p-5">
      <h2 className="text-lg font-semibold">{title}</h2>

      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div>
          <dt className="muted">Rows</dt>
          <dd className="font-medium">{dataset.summary.row_count}</dd>
        </div>
        <div>
          <dt className="muted">Valid Rows</dt>
          <dd className="font-medium">{dataset.summary.valid_row_count}</dd>
        </div>
        <div>
          <dt className="muted">Quality Score</dt>
          <dd className="font-medium">{dataset.summary.quality_score}</dd>
        </div>
        <div>
          <dt className="muted">Quality Band</dt>
          <dd className="font-medium">{dataset.summary.quality_band}</dd>
        </div>
        <div>
          <dt className="muted">Errors</dt>
          <dd className="font-medium">{dataset.summary.error_count}</dd>
        </div>
        <div>
          <dt className="muted">Warnings</dt>
          <dd className="font-medium">{dataset.summary.warning_count}</dd>
        </div>
      </dl>

      <div className="mt-4">
        <h3 className="text-sm font-semibold">Normalized Schema Fields</h3>
        {dataset.schema_fields.length ? (
          <ul className="mt-2 flex flex-wrap gap-2">
            {dataset.schema_fields.map((field) => (
              <li key={field} className="rounded-full border border-[var(--border)] bg-[rgba(17,35,58,0.8)] px-2 py-1 text-xs">
                {field}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm muted">No valid rows mapped.</p>
        )}
      </div>

      <div className="mt-4">
        <h3 className="text-sm font-semibold">Top Validation Issues</h3>
        {dataset.quality.top_issues.length ? (
          <ul className="mt-2 space-y-1 text-sm">
            {dataset.quality.top_issues.map((issue) => (
              <li key={issue.rule_id}>
                <code>{issue.rule_id}</code>: {issue.count}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm muted">No recurring issue patterns.</p>
        )}
      </div>
    </article>
  );
}
