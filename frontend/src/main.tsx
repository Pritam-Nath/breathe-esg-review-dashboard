import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  BadgeCheck,
  DatabaseZap,
  FileUp,
  Filter,
  Leaf,
  LockKeyhole,
  Plane,
  PlugZap,
  RefreshCw,
  Server,
} from "lucide-react";
import "./style.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

type Row = {
  id: number;
  external_id: string;
  source_type: "sap" | "utility" | "travel";
  activity_date: string | null;
  period_start: string | null;
  period_end: string | null;
  facility_or_cost_center: string;
  category: string;
  normalized_quantity: string | null;
  normalized_unit: string;
  co2e_kg: string | null;
  status: string;
  validation_errors: string[];
  suspicious_reasons: string[];
};

type Summary = {
  total_rows: number;
  approved: number;
  locked: number;
  failed: number;
  suspicious: number;
  co2e_kg: number | string;
  by_source: { source_batch__source_type: string; count: number; co2e: string | null }[];
};

const sourceMeta = {
  sap: { label: "SAP", icon: Server, color: "teal", detail: "Fuel and procurement exports" },
  utility: { label: "Utility", icon: PlugZap, color: "amber", detail: "Green Button style electricity" },
  travel: { label: "Travel", icon: Plane, color: "coral", detail: "Concur-like T&E rows" },
};

function formatNumber(value: number | string | null | undefined, digits = 0) {
  if (value === null || value === undefined || value === "") return "-";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function pillText(status: string) {
  return status.replaceAll("_", " ");
}

function App() {
  const [rows, setRows] = useState<Row[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [source, setSource] = useState("all");
  const [busy, setBusy] = useState(false);
  const [uploadType, setUploadType] = useState("sap");
  const [file, setFile] = useState<File | null>(null);

  async function load() {
    setBusy(true);
    const suffix = source === "all" ? "" : `?source_type=${source}`;
    const [summaryRes, rowsRes] = await Promise.all([
      fetch(`${API}/summary/`),
      fetch(`${API}/rows/${suffix}`),
    ]);
    setSummary(await summaryRes.json());
    setRows(await rowsRes.json());
    setBusy(false);
  }

  async function seedDemo() {
    setBusy(true);
    await fetch(`${API}/seed-demo/`, { method: "POST" });
    await load();
  }

  async function act(id: number, action: "approve" | "lock") {
    await fetch(`${API}/rows/${id}/${action}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: action === "approve" ? "analyst@breatheesg.com" : "auditor@breatheesg.com" }),
    });
    await load();
  }

  async function uploadCsv(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append("source_type", uploadType);
    form.append("file", file);
    form.append("source_system", uploadType === "sap" ? "SAP S/4HANA" : uploadType === "utility" ? "Utility portal" : "SAP Concur");
    await fetch(`${API}/upload-csv/`, { method: "POST", body: form });
    setFile(null);
    await load();
  }

  useEffect(() => {
    load();
  }, [source]);

  const reviewRows = useMemo(
    () => rows.filter((row) => row.status !== "locked" && (row.validation_errors.length || row.suspicious_reasons.length)),
    [rows],
  );
  const cleanRows = rows.length - reviewRows.length;

  return (
    <main>
      <section className="topbar">
        <div className="brand">
          <span className="brandMark"><Leaf size={22} /></span>
          <div>
            <strong>Breathe ESG</strong>
            <span>Ingestion review cockpit</span>
          </div>
        </div>
        <div className="actions">
          <button onClick={seedDemo} disabled={busy}><DatabaseZap size={17} /> Load demo</button>
          <button onClick={load} disabled={busy}><RefreshCw size={17} className={busy ? "spin" : ""} /> Refresh</button>
        </div>
      </section>

      <section className="hero">
        <div>
          <p className="eyebrow">Multi-source carbon activity intake</p>
          <h1>Normalize messy enterprise data before it reaches audit.</h1>
        </div>
        <div className="heroStats">
          <div><span>{formatNumber(summary?.co2e_kg, 0)}</span><small>kg CO2e in review system</small></div>
          <div><span>{summary?.total_rows ?? 0}</span><small>normalized activity rows</small></div>
        </div>
      </section>

      <section className="metrics">
        <Metric label="Approved" value={summary?.approved ?? 0} icon={BadgeCheck} />
        <Metric label="Locked" value={summary?.locked ?? 0} icon={LockKeyhole} />
        <Metric label="Suspicious" value={summary?.suspicious ?? 0} icon={AlertTriangle} />
        <Metric label="Failed validation" value={summary?.failed ?? 0} icon={FileUp} />
      </section>

      <section className="sourceGrid">
        {Object.entries(sourceMeta).map(([key, meta]) => {
          const Icon = meta.icon;
          const sourceSummary = summary?.by_source.find((item) => item.source_batch__source_type === key);
          return (
            <button className={`sourceCard ${meta.color} ${source === key ? "active" : ""}`} key={key} onClick={() => setSource(source === key ? "all" : key)}>
              <Icon size={22} />
              <strong>{meta.label}</strong>
              <span>{meta.detail}</span>
              <b>{sourceSummary?.count ?? 0} rows</b>
            </button>
          );
        })}
      </section>

      <section className="workbench">
        <aside>
          <div className="panelTitle"><Filter size={18} /> Intake controls</div>
          <div className="segmented">
            {["all", "sap", "utility", "travel"].map((item) => (
              <button className={source === item ? "selected" : ""} key={item} onClick={() => setSource(item)}>{item}</button>
            ))}
          </div>
          <form onSubmit={uploadCsv} className="upload">
            <label>Upload realistic CSV</label>
            <select value={uploadType} onChange={(event) => setUploadType(event.target.value)}>
              <option value="sap">SAP procurement/fuel</option>
              <option value="utility">Utility electricity</option>
              <option value="travel">Corporate travel</option>
            </select>
            <input type="file" accept=".csv" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            <button type="submit" disabled={!file}><FileUp size={16} /> Ingest CSV</button>
          </form>
          <div className="quality">
            <span>{cleanRows}</span>
            <p>Rows entered cleanly. Anything suspicious stays visible until an analyst signs off.</p>
          </div>
        </aside>

        <section className="tableWrap">
          <div className="tableHeader">
            <div>
              <p className="eyebrow">Analyst queue</p>
              <h2>{reviewRows.length} rows need attention</h2>
            </div>
            <span>{source === "all" ? "All sources" : sourceMeta[source as keyof typeof sourceMeta].label}</span>
          </div>
          <div className="rows">
            {rows.map((row) => (
              <article className="rowCard" key={row.id}>
                <div className="rowMain">
                  <span className={`sourceDot ${sourceMeta[row.source_type].color}`}>{sourceMeta[row.source_type].label}</span>
                  <div>
                    <h3>{row.category} · {row.external_id}</h3>
                    <p>{row.facility_or_cost_center || "No facility"} · {row.activity_date || `${row.period_start || "?"} to ${row.period_end || "?"}`}</p>
                  </div>
                </div>
                <div className="rowNumbers">
                  <span>{formatNumber(row.normalized_quantity, 1)} {row.normalized_unit}</span>
                  <b>{formatNumber(row.co2e_kg, 0)} kg CO2e</b>
                </div>
                <div className="rowFlags">
                  <span className={`status ${row.status}`}>{pillText(row.status)}</span>
                  {[...row.validation_errors, ...row.suspicious_reasons].map((flag) => <em key={flag}>{flag}</em>)}
                </div>
                <div className="rowActions">
                  <button onClick={() => act(row.id, "approve")} disabled={row.status === "approved" || row.status === "locked"}>
                    <BadgeCheck size={16} /> Approve
                  </button>
                  <button onClick={() => act(row.id, "lock")} disabled={row.status !== "approved"}>
                    <LockKeyhole size={16} /> Lock
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value, icon: Icon }: { label: string; value: number; icon: React.ElementType }) {
  return (
    <div className="metric">
      <Icon size={19} />
      <span>{value}</span>
      <small>{label}</small>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
