// Knowledge base: documents (version, status, effective date, retriever on/off) and known conflicts.
import { Fragment, useEffect, useState } from "react";
import { api, type ConflictRow, type KBDocument } from "../api";
import { Badge, EmptyState, ErrorNote, Spinner } from "../components/ui";
import { useRole } from "../roles";

export default function KnowledgeBase() {
  const { role } = useRole();
  const [docs, setDocs] = useState<KBDocument[] | null>(null);
  const [conflicts, setConflicts] = useState<ConflictRow[]>([]);
  const [open, setOpen] = useState<KBDocument | null>(null);
  const [error, setError] = useState("");

  const load = () =>
    Promise.all([api.get<KBDocument[]>("/api/kb/documents"), api.get<ConflictRow[]>("/api/kb/conflicts")])
      .then(([d, c]) => {
        setDocs(d);
        setConflicts(c);
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const toggle = async (doc: KBDocument) => {
    try {
      await api.post(`/api/kb/documents/${doc.id}/retriever`, { enabled: !doc.retriever_enabled });
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const expand = async (doc: KBDocument) => {
    if (open?.id === doc.id) return setOpen(null);
    try {
      setOpen(await api.get<KBDocument>(`/api/kb/documents/${doc.id}`));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const labelOf = (id: string | null) => docs?.find((d) => d.id === id)?.label ?? id;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Knowledge base</h1>
        <p className="muted mt-1">
          Synthetic procedures of a fictional bank. OCBC AI retrieves from every document whose retriever is on,
          including superseded ones. Q AI checks answers against current documents only.
        </p>
      </div>

      {error && <ErrorNote message={error} />}
      {!docs && !error && <Spinner />}

      {docs && (
        <section className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-line bg-canvas text-xs uppercase tracking-wide text-ink-muted">
                <tr>
                  <th className="px-4 py-3">Document</th>
                  <th className="px-4 py-3">Topic</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Effective</th>
                  <th className="px-4 py-3">OCBC AI retriever</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <Fragment key={d.id}>
                    <tr className="border-b border-line last:border-0">
                      <td className="px-4 py-3">
                        <button onClick={() => expand(d)} className="text-left font-semibold text-ink hover:text-brand-dark">
                          {d.label}
                        </button>
                        <div className="text-xs text-ink-muted">{d.owner}</div>
                      </td>
                      <td className="px-4 py-3 text-ink-muted">{d.topic.replace(/_/g, " ")}</td>
                      <td className="px-4 py-3">
                        {d.status === "current" ? (
                          <Badge tone="ok">Current</Badge>
                        ) : (
                          <div className="space-y-1">
                            <Badge tone="bad">Superseded</Badge>
                            <div className="text-xs text-ink-muted">by {labelOf(d.superseded_by)}</div>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-ink-muted">{d.effective_date}</td>
                      <td className="px-4 py-3">
                        {role === "admin" ? (
                          <button
                            onClick={() => toggle(d)}
                            role="switch"
                            aria-checked={d.retriever_enabled}
                            className="flex items-center gap-2"
                          >
                            <span
                              className={`relative h-5 w-9 rounded-full transition ${d.retriever_enabled ? "bg-ok" : "bg-line"}`}
                            >
                              <span
                                className={`absolute top-0.5 h-4 w-4 rounded-full bg-surface shadow transition ${
                                  d.retriever_enabled ? "left-[18px]" : "left-0.5"
                                }`}
                              />
                            </span>
                            <span className="text-xs font-semibold">{d.retriever_enabled ? "On" : "Off (retired)"}</span>
                          </button>
                        ) : (
                          <Badge tone={d.retriever_enabled ? "ok" : "muted"}>
                            {d.retriever_enabled ? "On" : "Off (retired)"}
                          </Badge>
                        )}
                      </td>
                    </tr>
                    {open?.id === d.id && (
                      <tr className="border-b border-line bg-canvas">
                        <td colSpan={5} className="px-4 py-4">
                          <DocumentDetail doc={open} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section>
        <h2 className="text-lg font-bold">Known conflicts</h2>
        <p className="muted mb-3">
          Computed once when documents load: same topic, same field, different value.
        </p>
        {conflicts.length === 0 ? (
          <EmptyState title="No conflicts found" />
        ) : (
          <ul className="space-y-2">
            {conflicts.map((c) => (
              <li key={c.id} className="card flex flex-wrap items-center gap-3 py-3">
                <Badge tone="warn">Conflict</Badge>
                <span className="text-sm">
                  <strong>{c.field.replace(/_/g, " ")}</strong>: {c.doc_a_label} says <strong>{c.value_a}</strong>,{" "}
                  {c.doc_b_label} says <strong>{c.value_b}</strong>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function DocumentDetail({ doc }: { doc: KBDocument }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="space-y-2">
        {doc.passages
          .filter((p) => p.kind === "section")
          .map((p) => (
            <div key={p.section}>
              <div className="text-xs font-semibold text-ink-muted">
                {p.section_label} {p.heading}
              </div>
              <p className="text-sm">{p.text}</p>
            </div>
          ))}
      </div>
      <div>
        <div className="text-xs font-semibold text-ink-muted">Conditions and exceptions</div>
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
          {doc.conditions.map((c) => (
            <li key={c.id}>
              {c.text} <span className="text-xs text-ink-muted">(applies when: {c.when})</span>
            </li>
          ))}
        </ul>
        {doc.required_details.length > 0 && (
          <>
            <div className="mt-3 text-xs font-semibold text-ink-muted">Required details</div>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {doc.required_details.map((r) => (
                <li key={r.name}>
                  {r.name}: “{r.question}” ({r.options.join(" / ")})
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
