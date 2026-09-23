import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, CircleDashed, Loader2, RefreshCw, TriangleAlert } from "lucide-react";
import type { StageDef } from "@/lib/govflow/data";

export type StageState =
  "idle" | "running" | "done" | "failed" | "retrying" | "fallback" | "recovered";

export type RunEvent = {
  id: string;
  time: string;
  stage: string;
  department: string;
  system: string;
  data: string;
  api: string;
  status: "Success" | "Failed" | "Retry" | "Fallback" | "Recovered";
  ms: number;
};

const now = () =>
  new Date().toLocaleTimeString("en-IN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

export function useWorkflowRun(
  stages: StageDef[],
  opts?: { onEvent?: (e: RunEvent) => void; speed?: number },
) {
  const speed = opts?.speed ?? 1;
  const [states, setStates] = useState<Record<string, StageState>>({});
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [failureRequested, setFailureRequested] = useState(false);
  const cursor = useRef(0);
  const failureStage = useRef<string | null>(null);
  const advanceRef = useRef<() => void>(() => undefined);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const onEvent = opts?.onEvent;

  const clear = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  useEffect(() => () => clear(), [clear]);

  const reset = useCallback(() => {
    clear();
    setStates({});
    setEvents([]);
    setActiveId(null);
    setRunning(false);
    setPaused(false);
    setFailureRequested(false);
    cursor.current = 0;
    failureStage.current = null;
  }, [clear]);

  const emit = useCallback(
    (event: RunEvent) => {
      setEvents((previous) => [...previous, event]);
      onEvent?.(event);
    },
    [onEvent],
  );

  const schedule = useCallback(
    (callback: () => void, delay = 850 / speed) => {
      timers.current.push(setTimeout(callback, delay));
    },
    [speed],
  );

  const advance = useCallback(() => {
    if (paused || !running) return;
    const stage = stages[cursor.current];
    if (!stage) {
      setRunning(false);
      setActiveId(null);
      return;
    }
    setActiveId(stage.id);
    setStates((previous) => ({ ...previous, [stage.id]: "running" }));
    schedule(() => {
      const shouldFail = stage.id === failureStage.current || stage.failsFirst;
      if (!shouldFail) {
        setStates((previous) => ({ ...previous, [stage.id]: "done" }));
        emit({
          id: `${stage.id}-success-${Date.now()}`,
          time: now(),
          stage: stage.name,
          department: stage.department,
          system: stage.system,
          data: stage.dataExchanged,
          api: stage.api,
          status: "Success",
          ms: stage.ms,
        });
        cursor.current += 1;
        schedule(() => advanceRef.current(), 250 / speed);
        return;
      }
      setStates((previous) => ({ ...previous, [stage.id]: "failed" }));
      emit({
        id: `${stage.id}-failed-${Date.now()}`,
        time: now(),
        stage: stage.name,
        department: stage.department,
        system: stage.system,
        data: stage.dataExchanged,
        api: stage.api,
        status: "Failed",
        ms: stage.ms * 3,
      });
      schedule(() => {
        setStates((previous) => ({ ...previous, [stage.id]: "retrying" }));
        emit({
          id: `${stage.id}-retry-1-${Date.now()}`,
          time: now(),
          stage: `${stage.name} · Retry 1/3`,
          department: "GovFlow Exception Engine",
          system: stage.system,
          data: "Replay request with exponential backoff",
          api: "POST /orchestrator/retry",
          status: "Retry",
          ms: 120,
        });
        schedule(() => {
          emit({
            id: `${stage.id}-retry-2-${Date.now()}`,
            time: now(),
            stage: `${stage.name} · Retry 2/3`,
            department: "GovFlow Exception Engine",
            system: stage.system,
            data: "Retry with idempotency key",
            api: "POST /orchestrator/retry",
            status: "Retry",
            ms: 180,
          });
          schedule(() => {
            setStates((previous) => ({ ...previous, [stage.id]: "fallback" }));
            emit({
              id: `${stage.id}-fallback-${Date.now()}`,
              time: now(),
              stage: `${stage.name} · Fallback connector`,
              department: "GovFlow Exception Engine",
              system: "Legacy Education Mirror",
              data: "Fallback connector payload",
              api: "POST /fallback/education",
              status: "Fallback",
              ms: 420,
            });
            schedule(() => {
              setStates((previous) => ({ ...previous, [stage.id]: "recovered" }));
              emit({
                id: `${stage.id}-recovered-${Date.now()}`,
                time: now(),
                stage: `${stage.name} · Recovery`,
                department: stage.department,
                system: "Legacy Education Mirror",
                data: stage.dataExchanged,
                api: stage.api,
                status: "Recovered",
                ms: stage.ms,
              });
              schedule(() => {
                setStates((previous) => ({ ...previous, [stage.id]: "done" }));
                cursor.current += 1;
                failureStage.current = null;
                setFailureRequested(false);
                schedule(() => advanceRef.current(), 250 / speed);
              }, 280 / speed);
            }, 650 / speed);
          }, 650 / speed);
        }, 650 / speed);
      }, 650 / speed);
    }, 650 / speed);
  }, [emit, paused, running, schedule, speed, stages]);

  advanceRef.current = advance;

  const run = useCallback(() => {
    clear();
    setStates({});
    setEvents([]);
    cursor.current = 0;
    failureStage.current = null;
    setFailureRequested(false);
    setPaused(false);
    setRunning(true);
    schedule(() => advanceRef.current(), 50);
  }, [clear, schedule]);

  const pause = useCallback(() => {
    clear();
    setPaused(true);
    setRunning(false);
  }, [clear]);

  const resume = useCallback(() => {
    setPaused(false);
    setRunning(true);
    schedule(() => advanceRef.current(), 50);
  }, [schedule]);

  const simulateFailure = useCallback(() => {
    const stage = stages[cursor.current];
    if (!stage) return;
    failureStage.current = stage.id;
    setFailureRequested(true);
    if (!running && !paused) {
      setRunning(true);
      schedule(() => advanceRef.current(), 50);
    }
  }, [paused, running, schedule, stages]);

  return {
    states,
    events,
    activeId,
    running,
    paused,
    failureRequested,
    run,
    pause,
    resume,
    reset,
    simulateFailure,
  };
}

function StageIcon({ state }: { state: StageState }) {
  if (state === "done") return <CheckCircle2 className="size-5 text-success" />;
  if (state === "failed") return <TriangleAlert className="size-5 text-warning" />;
  if (state === "retrying") return <RefreshCw className="size-5 animate-spin text-primary" />;
  if (state === "fallback") return <RefreshCw className="size-5 text-warning" />;
  if (state === "recovered") return <CheckCircle2 className="size-5 text-teal" />;
  if (state === "running") return <Loader2 className="size-5 animate-spin text-primary" />;
  return <CircleDashed className="size-5 text-muted-foreground" />;
}

export function WorkflowCanvas({
  stages,
  states,
  activeId,
  onSelect,
  compact,
}: {
  stages: StageDef[];
  states: Record<string, StageState>;
  activeId?: string | null;
  onSelect?: (s: StageDef) => void;
  compact?: boolean;
}) {
  const doneCount = stages.filter((s) => states[s.id] === "done").length;
  const pct = stages.length ? Math.round((doneCount / stages.length) * 100) : 0;

  return (
    <div className="space-y-4">
      <div className="govflow-grid overflow-x-auto rounded-xl border border-border bg-muted/25 p-4">
        <div className="flex min-w-max items-stretch gap-2">
          {stages.map((s, i) => {
            const state = states[s.id] ?? "idle";
            const active = activeId === s.id;
            return (
              <div key={s.id} className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onSelect?.(s)}
                  disabled={!onSelect}
                  aria-label={onSelect ? `Inspect ${s.name}` : undefined}
                  className={cn(
                    "w-36 rounded-xl border bg-card p-3 text-left transition-all disabled:cursor-default",
                    compact && "w-32 p-2.5",
                    state === "done" && "border-success/40 bg-success/5",
                    state === "failed" && "border-warning/50 bg-warning/10",
                    (state === "running" || state === "retrying") && "border-primary/60 shadow-md",
                    state === "fallback" && "border-warning/60 bg-warning/10 shadow-md",
                    state === "recovered" && "border-teal/50 bg-teal/5",
                    active && "ring-2 ring-primary/40",
                    state === "idle" && "border-border",
                  )}
                >
                  <StageIcon state={state} />
                  <p className="mt-2 text-xs leading-tight font-semibold">{s.name}</p>
                  {!compact ? (
                    <p className="mt-1 truncate text-[10px] text-muted-foreground">
                      {s.department}
                    </p>
                  ) : null}
                </button>
                {i < stages.length - 1 ? (
                  <span
                    className={cn(
                      "h-px w-6 shrink-0",
                      states[s.id] === "done" ? "bg-success" : "bg-border",
                    )}
                  />
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-linear-to-r from-primary to-teal transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="shrink-0 text-xs font-semibold text-muted-foreground">
          {pct}% complete
        </span>
      </div>
    </div>
  );
}

export function EventFeed({ events }: { events: RunEvent[] }) {
  if (!events.length)
    return (
      <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        Run the workflow to stream live orchestration events.
      </p>
    );
  return (
    <ol className="space-y-2">
      {[...events].reverse().map((e) => (
        <li key={e.id + e.time} className="rounded-xl border border-border bg-card p-3">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{e.stage}</p>
              <p className="truncate text-xs text-muted-foreground">
                {e.department} · {e.system}
              </p>
              <p className="mt-1 truncate font-mono text-[11px] text-muted-foreground">
                {e.api} · {e.data}
              </p>
            </div>
            <div className="shrink-0 text-right">
              <span
                className={cn(
                  "rounded-full border px-2 py-0.5 text-[11px] font-semibold",
                  e.status === "Success" && "border-success/25 bg-success/10 text-success",
                  e.status === "Failed" && "border-warning/30 bg-warning/15 text-warning",
                  e.status === "Retry" && "border-primary/25 bg-primary/10 text-primary",
                  e.status === "Fallback" && "border-warning/30 bg-warning/15 text-warning",
                  e.status === "Recovered" && "border-teal/30 bg-teal/10 text-teal",
                )}
              >
                {e.status}
              </span>
              <p className="mt-1 text-[11px] text-muted-foreground">
                {e.ms} ms · {e.time}
              </p>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
