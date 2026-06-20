import React, { useState } from "react";
import { uploadCsvDataset, testMysqlConnection, registerMysqlDataset } from "@/lib/datasetApi";
import { Eye, EyeOff } from "lucide-react";

interface Props {
  onDatasetLinked: (datasetId: string) => void;
}

export function DatasetLinker({ onDatasetLinked }: Props) {
  const [tab, setTab] = useState<"csv" | "mysql">("csv");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // CSV State
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvName, setCsvName] = useState("");

  // MySQL State
  const [host, setHost] = useState("");
  const [port, setPort] = useState("3306");
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState("");
  const [mysqlName, setMysqlName] = useState("");
  const [tested, setTested] = useState(false);

  const handleCsvUpload = async () => {
    if (!csvFile || !csvName) return;
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await uploadCsvDataset(csvFile, csvName);
      setSuccessMsg("CSV Dataset uploaded and registered successfully!");
      onDatasetLinked(res.dataset_id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    if (!host || !database || !username || !password) return;
    setLoading(true);
    setError(null);
    try {
      const res = await testMysqlConnection({ host, port: parseInt(port), database, username, password });
      setTables(res.tables);
      if (res.tables.length > 0) {
        setSelectedTable(res.tables[0]);
      }
      setTested(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMysqlRegister = async () => {
    if (!selectedTable || !mysqlName) return;
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await registerMysqlDataset({
        host, port: parseInt(port), database, username, password,
        table_name: selectedTable, display_name: mysqlName
      });
      setSuccessMsg("MySQL Table registered successfully!");
      onDatasetLinked(res.dataset_id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        <button 
          onClick={() => setTab("csv")} 
          style={{ flex: 1, padding: "8px", borderRadius: "8px", border: "1px solid", borderColor: tab === "csv" ? "#4f46e5" : "#cbd5e1", background: tab === "csv" ? "#e0e7ff" : "#fff", color: tab === "csv" ? "#4f46e5" : "#64748b", fontWeight: 600 }}
        >
          CSV Upload
        </button>
        <button 
          onClick={() => setTab("mysql")} 
          style={{ flex: 1, padding: "8px", borderRadius: "8px", border: "1px solid", borderColor: tab === "mysql" ? "#4f46e5" : "#cbd5e1", background: tab === "mysql" ? "#e0e7ff" : "#fff", color: tab === "mysql" ? "#4f46e5" : "#64748b", fontWeight: 600 }}
        >
          MySQL Connection
        </button>
      </div>

      {error && (
        <div style={{ padding: "10px", marginBottom: "16px", background: "#fee2e2", color: "#dc2626", borderRadius: "8px", fontSize: "14px" }}>
          {error}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: "12px", marginBottom: "16px", background: "#dcfce7", color: "#166534", borderRadius: "8px", fontSize: "14px", fontWeight: 600, border: "1px solid #bbf7d0" }}>
          {successMsg}
        </div>
      )}

      {!successMsg && tab === "csv" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <input type="text" placeholder="Dataset Name" value={csvName} onChange={e => setCsvName(e.target.value)} style={{ padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1" }} />
          <input type="file" accept=".csv" onChange={e => setCsvFile(e.target.files?.[0] || null)} style={{ padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1", background: "#fff" }} />
          <button onClick={handleCsvUpload} disabled={loading || !csvFile || !csvName} style={{ padding: "10px", borderRadius: "8px", border: "none", background: "#4f46e5", color: "#fff", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", opacity: loading || !csvFile || !csvName ? 0.6 : 1 }}>
            {loading ? "Uploading..." : "Upload & Register"}
          </button>
        </div>
      )}

      {!successMsg && tab === "mysql" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <input type="text" placeholder="Host (e.g. 127.0.0.1)" value={host} onChange={e => setHost(e.target.value)} style={{ padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1" }} />
          <input type="text" placeholder="Port (default: 3306)" value={port} onChange={e => setPort(e.target.value)} style={{ padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1" }} />
          <input type="text" placeholder="Database Name" value={database} onChange={e => setDatabase(e.target.value)} style={{ padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1" }} />
          <input type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} style={{ padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1" }} />
          <div style={{ position: "relative", width: "100%" }}>
            <input 
              type={showPassword ? "text" : "password"} 
              placeholder="Password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              style={{ width: "100%", padding: "10px", paddingRight: "40px", borderRadius: "8px", border: "1px solid #cbd5e1", boxSizing: "border-box" }} 
            />
            <button 
              type="button"
              onClick={() => setShowPassword(!showPassword)} 
              style={{ position: "absolute", right: "10px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "#64748b", display: "flex", padding: 0 }}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          
          {!tested ? (
             <button onClick={handleTestConnection} disabled={loading || !host || !database || !username || !password} style={{ padding: "10px", borderRadius: "8px", border: "none", background: "#4f46e5", color: "#fff", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1 }}>
               {loading ? "Testing..." : "Test Connection"}
             </button>
          ) : (
            <>
              <div style={{ padding: "10px", background: "#dcfce7", color: "#166534", borderRadius: "8px", fontSize: "14px", fontWeight: 600 }}>Connection Successful!</div>
              <select value={selectedTable} onChange={e => setSelectedTable(e.target.value)} style={{ padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1" }}>
                {tables.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <input type="text" placeholder="Dataset Name" value={mysqlName} onChange={e => setMysqlName(e.target.value)} style={{ padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1" }} />
              <button onClick={handleMysqlRegister} disabled={loading || !selectedTable || !mysqlName} style={{ padding: "10px", borderRadius: "8px", border: "none", background: "#4f46e5", color: "#fff", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", opacity: loading || !selectedTable || !mysqlName ? 0.6 : 1 }}>
                {loading ? "Registering..." : "Register Table"}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
