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

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", fontFamily: "Arial, sans-serif" }}>
      <h1>Agent Result Explorer</h1>
      <form onSubmit={onSubmit} style={{ display: "flex", gap: "0.5rem" }}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question"
          style={{ flex: 1, padding: "0.5rem" }}
        />
        <button type="submit">Run Agent</button>
      </form>

      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {result && (
        <section style={{ marginTop: "1rem" }}>
          <p><strong>Answer:</strong> {result.answer}</p>
          <p><strong>Confidence:</strong> {result.confidence}</p>
        </section>
      )}
    </main>
  );
}
