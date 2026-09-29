import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, Clock3, RefreshCw, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, StatusPill, Surface } from "@/components/govflow/bits";
import {
  api,
  type ConnectedSystemMetrics,
  type DataMappingConfiguration,
  type InteroperabilityTransaction,
  type MeshException,
} from "@/lib/api";

type HubData = {
  systems: ConnectedSystemMetrics[];
  transactions: InteroperabilityTransaction[];
  mappings: DataMappingConfiguration[];
  exceptions: MeshException[];
};

export function InteroperabilityHub({
  query,
  systemsOnly = false,
  setQuery,
  initialTransactionId,
}: {
  query: string;
  systemsOnly?: boolean;
  setQuery: (value: string) => void;
  initialTransactionId?: string;
}) {
  const [data, setData] = useState<HubData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(initialTransactionId ?? null);
  const [transaction, setTransaction] = useState<InteroperabilityTransaction | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [retryingId, setRetryingId] = useState<number | null>(null);
  const [retryNotice, setRetryNotice] = useState("");
  const [retryError, setRetryError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [systems, transactions, mappings, exceptions] = await Promise.all([
        api.getConnectedSystems(),
        api.getInteroperabilityTransactions(),
        api.getDataMappings(),
        api.getExceptions(),
      ]);
      setData({ systems, transactions, mappings, exceptions });
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Interoperability data could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const retry = useCallback(
    async (exception: MeshException) => {
      setRetryingId(exception.id);
      setRetryNotice("");
      setRetryError("");
      try {
        const result = await api.retryException(exception.id);
        if (result.status === "success") {
          setRetryNotice(result.message);
        } else {
          setRetryError(result.message);
        }
        await refresh();
        if (selectedId === result.transactionId) {
          try {
            setTransaction(await api.getInteroperabilityTransaction(result.transactionId));
          } catch (detailLoadError) {
            setDetailError(
              detailLoadError instanceof Error
                ? detailLoadError.message
                : "Updated transaction details could not be loaded.",
            );
          }
        }
      } catch (retryLoadError) {
        setRetryError(
          retryLoadError instanceof Error
            ? retryLoadError.message
            : "Exception retry could not be completed.",
        );
      } finally {
        setRetryingId(null);
      }
    },
    [refresh, selectedId],
  );

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), 15_000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    if (initialTransactionId) setSelectedId(initialTransactionId);
  }, [initialTransactionId]);

  useEffect(() => {
    if (!selectedId) {
      setTransaction(null);
      setDetailError("");
      return;
    }
    let active = true;
    setDetailLoading(true);
    setDetailError("");
    api
      .getInteroperabilityTransaction(selectedId)
      .then((result) => {
        if (active) setTransaction(result);
      })
      .catch((detailLoadError: unknown) => {
        if (active) {
          setDetailError(
            detailLoadError instanceof Error
              ? detailLoadError.message
              : "Transaction details could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (active) setDetailLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  const normalizedQuery = query.trim().toLowerCase();
  const systems = useMemo(
    () =>
      (data?.systems ?? []).filter((system) =>
        `${system.name} ${system.department ?? ""} ${system.slug}`
          .toLowerCase()
          .includes(normalizedQuery),
      ),
    [data?.systems, normalizedQuery],
  );
  const transactions = useMemo(
    () =>
      (data?.transactions ?? []).filter((item) =>
        `${item.transactionId} ${item.source} ${item.destination} ${item.applicationReference ?? ""} ${item.dataType} ${item.status}`
          .toLowerCase()
          .includes(normalizedQuery),
      ),
    [data?.transactions, normalizedQuery],
  );

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Interoperability Command Centre"
        title={systemsOnly ? "Connected Systems" : "Interoperability Hub"}
        subtitle="Connected system health and transaction activity from persisted interoperability records."
        actions={
          <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
            <RefreshCw className="mr-2 size-4" /> Refresh
          </Button>
        }
      />
      <Input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search systems, transactions, applications, and data types"
        aria-label="Search interoperability data"
      />

      {error ? (
        <Surface>
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
          {!data ? (
            <Button className="mt-3" variant="outline" onClick={() => void refresh()}>
              Retry loading interoperability data
            </Button>
          ) : null}
        </Surface>
      ) : null}

      {loading && !data ? (
        <Surface>
          <p className="text-sm text-muted-foreground">
            Loading data from the interoperability backend…
          </p>
        </Surface>
      ) : null}

      {data ? (
        <>
          <section className="space-y-3" aria-labelledby="connected-systems-heading">
            <div>
              <h2 id="connected-systems-heading" className="text-base font-bold">
                Connected Systems
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                System records and measured transaction metrics.
              </p>
            </div>
            {systems.length ? (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {systems.map((system) => (
                  <Surface key={system.id} className="space-y-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="truncate font-bold">{system.department || system.name}</h3>
                        <p className="mt-1 truncate text-xs text-muted-foreground">{system.name}</p>
                      </div>
                      <StatusPill
                        status={
                          system.connectionStatus === "connected" ? "Connected" : "Disconnected"
                        }
                      />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <HealthStatus status={system.healthStatus} />
                      <span className="rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground">
                        {system.integrationType} · {system.apiVersion} ·{" "}
                        {system.connectorMode ?? "mode unavailable"}
                      </span>
                    </div>
                    <dl className="grid grid-cols-2 gap-x-3 gap-y-4 border-t border-border pt-3">
                      <Metric
                        label="Response time"
                        value={
                          system.responseTimeMs === null
                            ? "No probe"
                            : `${system.responseTimeMs} ms probe`
                        }
                      />
                      <Metric
                        label="Last successful check/request"
                        value={formatDate(system.lastSuccessfulRequestAt)}
                      />
                      <Metric
                        label="Transactions"
                        value={system.transactionCount.toLocaleString()}
                      />
                      <Metric
                        label="Failed transactions"
                        value={system.failedTransactionCount.toLocaleString()}
                      />
                      <Metric
                        label="Failures (checks + transactions)"
                        value={system.failureCount.toLocaleString()}
                      />
                      <Metric label="Last failure" value={formatDate(system.lastFailureAt)} />
                    </dl>
                    {system.lastFailureMessage ? (
                      <p className="border-t border-border pt-3 text-xs text-danger">
                        Latest health-check error: {system.lastFailureMessage}
                      </p>
                    ) : null}
                  </Surface>
                ))}
              </div>
            ) : (
              <Surface>
                <p className="text-sm text-muted-foreground">
                  No connected systems are configured in the backend.
                </p>
              </Surface>
            )}
          </section>

          {!systemsOnly ? (
            <>
              <section className="space-y-3" aria-labelledby="transactions-heading">
                <div>
                  <h2 id="transactions-heading" className="text-base font-bold">
                    Interoperability transactions
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Select a transaction to load its persisted event timeline.
                  </p>
                </div>
                {transactions.length ? (
                  <div className="surface overflow-x-auto">
                    <table className="w-full min-w-[1050px] text-left text-sm">
                      <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                        <tr>
                          {[
                            "Transaction ID",
                            "Source",
                            "Destination",
                            "Application",
                            "Data Type",
                            "Status",
                            "Started",
                            "Completed",
                          ].map((heading) => (
                            <th key={heading} className="px-3 py-3 font-semibold">
                              {heading}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {transactions.map((item) => (
                          <tr key={item.transactionId}>
                            <td className="px-3 py-3">
                              <button
                                className="font-semibold text-primary hover:underline"
                                onClick={() => setSelectedId(item.transactionId)}
                              >
                                {item.transactionId}
                              </button>
                            </td>
                            <td className="px-3 py-3">{item.source}</td>
                            <td className="px-3 py-3">{item.destination}</td>
                            <td className="px-3 py-3">
                              {item.applicationReference || `Application #${item.applicationId}`}
                            </td>
                            <td className="px-3 py-3">{item.dataType}</td>
                            <td className="px-3 py-3">
                              <StatusPill status={formatStatus(item.status)} />
                            </td>
                            <td className="px-3 py-3">{formatDate(item.startedAt)}</td>
                            <td className="px-3 py-3">{formatDate(item.completedAt)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Surface>
                    <p className="text-sm text-muted-foreground">
                      No interoperability transactions have been recorded.
                    </p>
                  </Surface>
                )}
              </section>

              <section className="grid gap-4 xl:grid-cols-2">
                <Surface>
                  <h2 className="text-base font-bold">Data mappings</h2>
                  {data.mappings.length ? (
                    <div className="mt-3 space-y-2">
                      {data.mappings.map((mapping) => (
                        <div key={mapping.id} className="rounded-lg border border-border p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-semibold">{mapping.name}</span>
                            <StatusPill status={formatStatus(mapping.status)} />
                          </div>
                          <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                            {mapping.sourceSystem || mapping.source}
                            <ArrowRight className="size-3 shrink-0" />
                            {mapping.targetSystem || mapping.target}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            Version {mapping.version} · {mapping.rules.length} persisted rules
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm text-muted-foreground">
                      No data mappings have been configured.
                    </p>
                  )}
                </Surface>
                <Surface>
                  <h2 className="text-base font-bold">Exceptions</h2>
                  {retryNotice ? (
                    <p role="status" className="mt-3 text-sm text-success">
                      {retryNotice}
                    </p>
                  ) : null}
                  {retryError ? (
                    <p role="alert" className="mt-3 text-sm text-danger">
                      {retryError}
                    </p>
                  ) : null}
                  {data.exceptions.length ? (
                    <div className="mt-3 space-y-2">
                      {data.exceptions.map((exception) => (
                        <div key={exception.id} className="rounded-lg border border-border p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-semibold">
                              {exception.sourceSystem || exception.system} ·{" "}
                              {exception.type || exception.category}
                            </span>
                            <StatusPill status={formatStatus(exception.status)} />
                          </div>
                          <p className="mt-1 text-sm">{exception.message}</p>
                          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                            <p className="text-xs text-muted-foreground">
                              {exception.severity} · {formatDate(exception.createdAt)}
                              {exception.transactionId ? ` · ${exception.transactionId}` : ""}
                              {exception.applicationId
                                ? ` · Application ${exception.applicationId}`
                                : ""}
                              {` · ${exception.retryCount} retries`}
                            </p>
                            {["OPEN", "ESCALATED"].includes(exception.status) ? (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => void retry(exception)}
                                disabled={retryingId !== null}
                              >
                                <RefreshCw
                                  className={`mr-2 size-3.5 ${
                                    retryingId === exception.id ? "animate-spin" : ""
                                  }`}
                                />
                                {retryingId === exception.id ? "Retrying…" : "Retry connector"}
                              </Button>
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm text-muted-foreground">
                      No interoperability exceptions have been recorded.
                    </p>
                  )}
                </Surface>
              </section>
            </>
          ) : null}
        </>
      ) : null}

      {selectedId ? (
        <TransactionDetail
          loading={detailLoading}
          error={detailError}
          transaction={transaction}
          onClose={() => setSelectedId(null)}
        />
      ) : null}
    </div>
  );
}

function TransactionDetail({
  loading,
  error,
  transaction,
  onClose,
}: {
  loading: boolean;
  error: string;
  transaction: InteroperabilityTransaction | null;
  onClose: () => void;
}) {
  return (
    <Surface className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold">Transaction detail</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {transaction?.transactionId || "Loading transaction…"}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={onClose}>
          Close detail
        </Button>
      </div>
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading transaction events…</p>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {transaction ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Source" value={transaction.source} />
            <Metric label="Destination" value={transaction.destination} />
            <Metric
              label="Application"
              value={transaction.applicationReference || `#${transaction.applicationId}`}
            />
            <Metric label="Data type" value={transaction.dataType} />
          </div>
          <div className="space-y-0">
            {transaction.timeline.map((step, index) => {
              const completed = step.status === "completed";
              return (
                <div key={step.key} className="flex min-h-20 gap-3">
                  <div className="flex w-6 shrink-0 flex-col items-center">
                    <span
                      className={`grid size-6 place-items-center rounded-full ${completed ? "bg-success/15 text-success" : "bg-muted text-muted-foreground"}`}
                    >
                      {completed ? (
                        <CheckCircle2 className="size-4" />
                      ) : (
                        <Clock3 className="size-4" />
                      )}
                    </span>
                    {index < transaction.timeline.length - 1 ? (
                      <span
                        className={`my-1 w-px flex-1 ${completed ? "bg-success/50" : "bg-border"}`}
                      />
                    ) : null}
                  </div>
                  <div className="min-w-0 pb-4">
                    <p className="font-semibold">{step.label}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {step.occurredAt ? formatDate(step.occurredAt) : "Not recorded"}
                      {step.detail ? ` · ${step.detail}` : ""}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
          {transaction.errorMessage ? (
            <div className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger/5 p-3 text-sm text-danger">
              <XCircle className="mt-0.5 size-4 shrink-0" />
              <span>
                {transaction.errorCode ? `${transaction.errorCode}: ` : ""}
                {transaction.errorMessage}
              </span>
            </div>
          ) : null}
        </>
      ) : null}
    </Surface>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold uppercase text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-words text-sm font-medium">{value}</dd>
    </div>
  );
}

function HealthStatus({ status }: { status: ConnectedSystemMetrics["healthStatus"] }) {
  const label = formatStatus(status);
  return <StatusPill status={status === "active" ? "Healthy" : label} />;
}

function formatStatus(status: string) {
  return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}
