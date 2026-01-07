from flask import Flask, request, render_template_string, send_file, redirect, url_for
import sqlite3
import pandas as pd
import os

app = Flask(__name__)

# ---------------- CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "payroll.db")
EXPORT_FILE = os.path.join(BASE_DIR, "payroll_export.xlsx")

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            basic REAL NOT NULL,
            housing REAL NOT NULL,
            transport REAL NOT NULL,
            feeding REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

# ---------------- PAYROLL LOGIC ----------------
def compute_payroll():
    with get_db() as conn:
        df = pd.read_sql_query("SELECT * FROM staff", conn)

    if df.empty:
        return df

    df["gross"] = df[["basic", "housing", "transport", "feeding"]].sum(axis=1)
    df["tax"] = df["gross"] * 0.10
    df["pension"] = df["gross"] * 0.08
    df["net"] = df["gross"] - (df["tax"] + df["pension"])

    return df.sort_values("net", ascending=False)

# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    error = None

    if request.method == "POST":
        try:
            data = {
                "name": request.form["name"].strip(),
                "role": request.form["role"].strip(),
                "basic": float(request.form["basic"]),
                "housing": float(request.form["housing"]),
                "transport": float(request.form["transport"]),
                "feeding": float(request.form["feeding"]),
            }

            with get_db() as conn:
                conn.execute("""
                INSERT INTO staff (name, role, basic, housing, transport, feeding)
                VALUES (:name, :role, :basic, :housing, :transport, :feeding)
                """, data)

            return redirect(url_for("index"))

        except ValueError:
            error = "Salary fields must be valid numbers."

    df = compute_payroll()
    avg_gross = round(df["gross"].mean(), 2) if not df.empty else 0
    above_30k = int((df["net"] > 30000).sum()) if not df.empty else 0

    return render_template_string(
        TEMPLATE,
        table=df.to_html(index=False, classes="table") if not df.empty else "<p>No staff added yet.</p>",
        avg_gross=avg_gross,
        above_30k=above_30k,
        error=error
    )

@app.route("/export")
def export():
    df = compute_payroll()
    if df.empty:
        return "No data to export", 400

    df.to_excel(EXPORT_FILE, index=False)
    return send_file(EXPORT_FILE, as_attachment=True)

# ---------------- INLINE HTML + CSS + JS ----------------
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<title>Payroll System</title>

<script src="https://js.puter.com/v2/"></script>

<style>
* { box-sizing: border-box; }

body {
  font-family: Inter, system-ui, Arial;
  background: #f4f6f9;
  padding: 40px;
}

.container {
  background: #fff;
  max-width: 1100px;
  margin: auto;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 15px 40px rgba(0,0,0,0.08);
}

h2, h3 { margin-bottom: 10px; }

form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

input {
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #ccc;
}

input:focus {
  outline: none;
  border-color: #4f46e5;
}

button {
  padding: 12px;
  border-radius: 8px;
  border: none;
  background: #4f46e5;
  color: white;
  font-weight: 600;
  cursor: pointer;
}

button:hover {
  background: #4338ca;
}

.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.table th {
  background: #4f46e5;
  color: white;
  padding: 10px;
}

.table td {
  padding: 10px;
  border-bottom: 1px solid #eee;
}

.stats {
  display: flex;
  gap: 20px;
  margin-top: 20px;
}

.stat-box {
  background: #f8fafc;
  padding: 15px;
  border-radius: 10px;
  flex: 1;
  border-left: 4px solid #4f46e5;
}

.error {
  background: #fee2e2;
  color: #991b1b;
  padding: 10px;
  border-radius: 8px;
}

a {
  display: inline-block;
  margin-top: 15px;
  font-weight: 600;
  color: #4f46e5;
  text-decoration: none;
}

pre {
  background: #0f172a;
  color: #e5e7eb;
  padding: 15px;
  border-radius: 10px;
}
</style>
</head>

<body>
<div class="container">

<h2>Payroll Management System</h2>

{% if error %}
<div class="error">{{ error }}</div>
{% endif %}

<form method="post">
  <input name="name" placeholder="Staff Name" required>
  <input name="role" placeholder="Role" required>
  <input name="basic" type="number" step="0.01" placeholder="Basic Salary" required>
  <input name="housing" type="number" step="0.01" placeholder="Housing Allowance" required>
  <input name="transport" type="number" step="0.01" placeholder="Transport Allowance" required>
  <input name="feeding" type="number" step="0.01" placeholder="Feeding Allowance" required>
  <button>Add Staff</button>
</form>

{{ table | safe }}

<div class="stats">
  <div class="stat-box"><b>Average Gross:</b><br> ₦{{ avg_gross }}</div>
  <div class="stat-box"><b>Above ₦30k Net:</b><br> {{ above_30k }}</div>
</div>

<a href="/export">📥 Export to Excel</a>

<hr>

<h3>AI Payroll Explanation</h3>
<button onclick="explain()">Explain Payroll</button>
<pre id="ai"></pre>

</div>

<script>
function explain(){
  puter.ai.chat(
    "Explain gross pay, tax deduction, pension, and net salary in simple terms.",
    { model: "gpt-4o-mini" }
  ).then(r => {
    document.getElementById("ai").innerText = r.message.content;
  });
}
</script>

</body>
</html>
"""

# ---------------- MAIN ----------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
