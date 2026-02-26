import { useState } from "react";
import { askAgent } from "./api";

export default function App() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    setError("");

    try {
      const data = await askAgent(question);
      setResult(data);
    } catch (err) {
      setError(err.message);
    }
  }
function renderValue(value) {
  if (value === null || value === undefined) return "N/A";

  if (Array.isArray(value)) {
    return (
      <ul>
        {value.map((item, i) => (
          <li key={i}>{typeof item === "object" ? JSON.stringify(item) : String(item)}</li>
        ))}
        </ul>

    );
  } 
  if (typeof value === "object") 
    return (
      <pre style={{background: "#f6f6f6f6", padding: "0.5rem"}}>
        {JSON.stringify(value, null, 2)}
      </pre>
      );
  return String(value);
}
  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", fontFamily: "Arial, sans-serif" }}>
      <h1>Agent Search</h1>
      <form onSubmit={onSubmit} style={{ display: "flex", gap: "0.5rem" }}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Agent Search Rating"
          style={{ flex: 1, padding: "0.5rem" }}
        />
        <button type="submit">Run Agent</button>
      </form>

      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {result && (
        <section style={{ marginTop: "1rem" }}>
          {Object.entries(result).map(([key, value]) => (
            <div key={key} style={{ marginBottom: "0.75rem" }}>
              <strong>{key}:</strong>
              <div>{renderValue(value)}</div>
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
