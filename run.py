from flask import Flask, request, render_template_string, send_file
import sqlite3
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
DB = "payroll.db"
EXPORT_FILE = "payroll_export.xlsx"

# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect(DB)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        role TEXT,
        basic REAL,
        housing REAL,
        transport REAL,
        feeding REAL
    )
    """)
    conn.commit()
    conn.close()

# ---------- PAYROLL LOGIC ----------
def compute_payroll():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM staff", conn)
    conn.close()

    if df.empty:
        return df

    df["gross"] = df["basic"] + df["housing"] + df["transport"] + df["feeding"]
    df["tax"] = df["gross"] * 0.10
    df["pension"] = df["gross"] * 0.08
    df["net"] = df["gross"] - (df["tax"] + df["pension"])

    return df.sort_values("net", ascending=False)

# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO staff (name, role, basic, housing, transport, feeding)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.form["name"],
            request.form["role"],
            float(request.form["basic"]),
            float(request.form["housing"]),
            float(request.form["transport"]),
            float(request.form["feeding"])
        ))
        conn.commit()
        conn.close()

    df = compute_payroll()
    avg_gross = df["gross"].mean() if not df.empty else 0
    above_30k = (df["net"] > 30000).sum() if not df.empty else 0

    return render_template_string(TEMPLATE,
        table=df.to_html(index=False) if not df.empty else "No staff yet",
        avg_gross=round(avg_gross,2),
        above_30k=above_30k
    )

@app.route("/export")
def export():
    df = compute_payroll()
    df.to_excel(EXPORT_FILE, index=False)
    return send_file(EXPORT_FILE, as_attachment=True)

# ---------- HTML (INLINE) ----------
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<title>Payroll System</title>
<script src="https://js.puter.com/v2/"></script>
</head>
<body>
<h2>Payroll System (Python + SQLite)</h2>

<form method="post">
<input name="name" placeholder="Name" required>
<input name="role" placeholder="Role" required>
<input name="basic" placeholder="Basic" required>
<input name="housing" placeholder="Housing" required>
<input name="transport" placeholder="Transport" required>
<input name="feeding" placeholder="Feeding" required>
<button>Add Staff</button>
</form>

<hr>
{{ table }}

<p><b>Average Gross Pay:</b> {{ avg_gross }}</p>
<p><b>Staff above ₦30,000 Net Pay:</b> {{ above_30k }}</p>

<a href="/export">Export to Excel</a>

<hr>
<h3>AI Explanation (Optional)</h3>
<button onclick="explain()">Explain Payroll</button>
<pre id="ai"></pre>

<script>
function explain(){
    puter.ai.chat(
        "Explain this payroll system output, focusing on tax, pension, and net pay.",
        { model: "gpt-4o-mini" }
    ).then(r => {
        document.getElementById("ai").innerText = r.message.content;
    });
}
</script>

</body>
</html>
"""

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
