"use client";

import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import { useToast } from "@/components/toast-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createSchedule,
  deleteSchedule,
  getSchedules,
  isApiError,
  updateSchedule,
  type Schedule,
} from "@/lib/api";

const DAYS_OF_WEEK = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const scheduleSchema = z.object({
  frequency: z.enum(["daily", "weekly", "monthly"]),
  time_of_day: z.string().regex(/^\d{2}:\d{2}$/, "Use HH:MM format"),
  day_of_week: z.coerce.number().min(0).max(6).optional(),
  day_of_month: z.coerce.number().min(1).max(31).optional(),
  business_id: z.string().optional(),
  all_businesses: z.boolean().default(false),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().optional(),
  send_whatsapp: z.boolean().default(true),
});

type ScheduleForm = z.infer<typeof scheduleSchema>;

export function ScheduleManager() {
  const { token } = useAuth();
  const { organizationId, activeBusinessId } = useOrg();
  const { pushToast } = useToast();

  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<ScheduleForm>({
    resolver: zodResolver(scheduleSchema),
    defaultValues: {
      frequency: "weekly",
      time_of_day: "18:00",
      day_of_week: 4,
      day_of_month: 1,
      business_id: activeBusinessId,
      all_businesses: false,
      start_date: new Date().toISOString().slice(0, 10),
      end_date: "",
      send_whatsapp: true,
    },
  });

  const frequency = form.watch("frequency");
  const allBusinesses = form.watch("all_businesses");

  useEffect(() => {
    if (!token) return;
    let mounted = true;
    setLoading(true);
    void getSchedules(token, organizationId)
      .then((res) => {
        if (mounted) setSchedules(res);
      })
      .catch((err) => {
        if (mounted) setError(isApiError(err) ? err.message : "Failed to load schedules");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, [token, organizationId]);

  const onSubmit = form.handleSubmit(async (values) => {
    if (!token) return;
    setError(null);

    try {
      const result = await createSchedule(token, {
        organization_id: organizationId,
        business_id: values.all_businesses ? null : (values.business_id?.trim() || activeBusinessId),
        frequency: values.frequency,
        time_of_day: values.time_of_day,
        day_of_week: values.frequency === "weekly" ? values.day_of_week : undefined,
        day_of_month: values.frequency === "monthly" ? values.day_of_month : undefined,
        start_date: values.start_date,
        end_date: values.end_date?.trim() || undefined,
        send_whatsapp: values.send_whatsapp,
      });
      setSchedules((prev) => [result, ...prev]);
      pushToast("Schedule created", "success");
      form.reset();
    } catch (err) {
      const msg = isApiError(err) ? err.message : "Failed to create schedule";
      setError(msg);
      pushToast(msg, "danger");
    }
  });

  const onToggle = async (schedule: Schedule) => {
    if (!token) return;
    try {
      await updateSchedule(token, schedule.id, { is_active: !schedule.is_active });
      setSchedules((prev) =>
        prev.map((s) => (s.id === schedule.id ? { ...s, is_active: !s.is_active } : s))
      );
      pushToast(schedule.is_active ? "Schedule paused" : "Schedule activated", "info");
    } catch (err) {
      pushToast(isApiError(err) ? err.message : "Failed to update schedule", "danger");
    }
  };

  const onDelete = async (id: string) => {
    if (!token) return;
    try {
      await deleteSchedule(token, id);
      setSchedules((prev) => prev.filter((s) => s.id !== id));
      pushToast("Schedule deleted", "info");
    } catch (err) {
      pushToast(isApiError(err) ? err.message : "Failed to delete schedule", "danger");
    }
  };

  return (
    <section className="card p-6">
      <h2 className="text-lg font-semibold">Report Scheduling</h2>
      <p className="mt-1 text-sm muted">Automate report generation and WhatsApp delivery.</p>

      {error ? (
        <div className="mt-3 rounded-md border border-[rgba(255,107,122,0.3)] bg-[rgba(255,107,122,0.08)] px-4 py-2">
          <p className="text-xs text-[var(--danger)]">{error}</p>
        </div>
      ) : null}

      <form className="mt-4 grid gap-4" onSubmit={onSubmit}>
        <div className="grid gap-4 md:grid-cols-3">
          <label className="text-sm font-medium">
            Frequency
            <select
              {...form.register("frequency")}
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[rgba(11,21,37,0.9)] px-3 py-2 text-sm"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </label>

          <label className="text-sm font-medium">
            Time (HH:MM)
            <Input {...form.register("time_of_day")} placeholder="18:00" className="mt-1" />
            {form.formState.errors.time_of_day ? (
              <p className="mt-1 text-xs text-[var(--danger)]">{form.formState.errors.time_of_day.message}</p>
            ) : null}
          </label>

          {frequency === "weekly" ? (
            <label className="text-sm font-medium">
              Day of Week
              <div className="mt-1 flex gap-1">
                {DAYS_OF_WEEK.map((day, idx) => (
                  <button
                    key={day}
                    type="button"
                    onClick={() => form.setValue("day_of_week", idx)}
                    className={`flex h-8 w-8 items-center justify-center rounded text-xs font-semibold transition-colors ${
                      form.watch("day_of_week") === idx
                        ? "bg-[var(--accent)] text-white"
                        : "border border-[var(--border)] bg-[rgba(10,19,33,0.6)] hover:bg-[rgba(55,181,255,0.15)]"
                    }`}
                  >
                    {day[0]}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-[10px] muted">
                Selected: {DAYS_OF_WEEK[form.watch("day_of_week") ?? 4]}
              </p>
            </label>
          ) : null}

          {frequency === "monthly" ? (
            <label className="text-sm font-medium">
              Day of Month (1-31)
              <Input
                type="number"
                min={1}
                max={31}
                {...form.register("day_of_month")}
                className="mt-1"
              />
            </label>
          ) : null}
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <label className="text-sm font-medium">
            Start Date
            <Input type="date" {...form.register("start_date")} className="mt-1" />
          </label>
          <label className="text-sm font-medium">
            End Date (optional)
            <Input type="date" {...form.register("end_date")} className="mt-1" />
          </label>
          <div className="flex flex-col justify-end gap-2">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" {...form.register("all_businesses")} className="h-4 w-4 accent-[var(--accent)]" />
              All SMEs in organization
            </label>
            {!allBusinesses ? (
              <Input
                {...form.register("business_id")}
                placeholder={activeBusinessId}
                className="text-xs"
              />
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" {...form.register("send_whatsapp")} className="h-4 w-4 accent-[var(--accent)]" />
            Send via WhatsApp
          </label>
          <Button type="submit" variant="primary" disabled={form.formState.isSubmitting}>
            {form.formState.isSubmitting ? "Saving..." : "Save Schedule"}
          </Button>
        </div>
      </form>

      {/* Schedules table */}
      {loading ? (
        <p className="mt-4 text-sm muted">Loading schedules...</p>
      ) : schedules.length > 0 ? (
        <div className="mt-6 overflow-x-auto rounded-md border border-[var(--border)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[rgba(10,19,33,0.7)] text-left">
                <th className="px-4 py-2 font-semibold">Frequency</th>
                <th className="px-4 py-2 font-semibold">Time</th>
                <th className="px-4 py-2 font-semibold">Scope</th>
                <th className="px-4 py-2 font-semibold">WhatsApp</th>
                <th className="px-4 py-2 font-semibold">Status</th>
                <th className="px-4 py-2 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => (
                <tr key={s.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[rgba(79,121,199,0.07)]">
                  <td className="px-4 py-2 capitalize">{s.frequency}</td>
                  <td className="px-4 py-2 font-mono text-xs">
                    {s.time_of_day}
                    {s.frequency === "weekly" && s.day_of_week != null ? ` (${DAYS_OF_WEEK[s.day_of_week]})` : ""}
                    {s.frequency === "monthly" && s.day_of_month != null ? ` (Day ${s.day_of_month})` : ""}
                  </td>
                  <td className="px-4 py-2 text-xs">
                    {s.business_id ? (
                      <span className="font-mono text-[var(--accent)]">{s.business_id}</span>
                    ) : (
                      <span className="text-[var(--ok)]">All SMEs</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    {s.send_whatsapp ? (
                      <span className="text-[var(--ok)]">Yes</span>
                    ) : (
                      <span className="muted">No</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`badge ${s.is_active ? "badge-ok" : "badge-warn"}`}>
                      {s.is_active ? "Active" : "Paused"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => void onToggle(s)}
                        className="text-xs text-[var(--accent)] underline"
                      >
                        {s.is_active ? "Pause" : "Enable"}
                      </button>
                      <button
                        type="button"
                        onClick={() => void onDelete(s.id)}
                        className="text-xs text-[var(--danger)] underline"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-4 text-sm muted">No schedules configured yet.</p>
      )}
    </section>
  );
}
