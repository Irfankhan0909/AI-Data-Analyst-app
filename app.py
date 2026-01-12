import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from io import BytesIO
from groq import Groq
import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)


# ================= PAGE =================
st.set_page_config("AI-Driven Self-Service Business Intelligence Platform", "📊", layout="wide")
st.title("📊 AI-Driven Self-Service Business Intelligence Platform")
st.caption("Upload CSV files and ask business questions in plain English")

# ================= FILE UPLOAD =================
st.sidebar.header("Upload CSV Files")
files = st.sidebar.file_uploader("Upload one or more CSV files", type="csv", accept_multiple_files=True)

if not files:
    st.info("Upload CSV files to begin")
    st.stop()

# ================= SQLITE =================
conn = sqlite3.connect(":memory:", check_same_thread=False)

schema = ""

for file in files:
    df = pd.read_csv(file)

    table = file.name.replace(".csv","").lower().replace(" ","_")
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]

    df.to_sql(table, conn, index=False, if_exists="replace")

    schema += f"{table}({', '.join(df.columns)})\n"

st.sidebar.success("Data loaded")

# ================= RUN SQL =================
def run_sql(query):
    try:
        return pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"SQL Error: {e}")
        return pd.DataFrame()

# ================= AI =================
def call_ai(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a SQL and business analytics expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=600
    )
    return response.choices[0].message.content.strip()

# ================= TEXT → SQL =================
def ask_ai(question):
    prompt = f"""
You are a data analyst.

Here is the database schema:
{schema}

Rules:
- Use only these tables and columns
- Use table.column format
- No guessing columns
- If revenue not present, calculate as quantity * price
- Write ONE SQLite query
- No explanation

User question:
{question}
"""
    raw = call_ai(prompt)
    raw = raw.replace("```sql","").replace("```","").strip()
    return raw.split(";")[0] + ";"

# ================= EXPLAIN =================
def explain(df):
    if df.empty:
        return "No data was returned for this question."

    preview = df.head(10).to_string(index=False)

    prompt = f"""
You are a senior business analyst.

Here is a table of results:
{preview}

Write a clear 2–3 sentence business summary.
Do not mention SQL.
Do not repeat the numbers exactly.
Explain what this means for the business.
"""

    return call_ai(prompt)


# ================= UI =================
question = st.text_input("Ask a business question")

if st.button("Run") and question:
    sql = ask_ai(question)
    st.code(sql, language="sql")

    df = run_sql(sql)
    st.dataframe(df)

# ================= CHART =================
st.subheader("📈 Visualization")
chart_type = st.selectbox("Choose chart type", ["Bar", "Line", "Pie"])

numeric_cols = df.select_dtypes(include="number").columns
categorical_cols = df.select_dtypes(exclude="number").columns

if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
    x = categorical_cols[0]
    y = numeric_cols[0]

    if chart_type == "Bar":
        fig, ax = plt.subplots(figsize=(10,5))
        ax.bar(df[x].astype(str), df[y])
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        plt.xticks(rotation=45)
        st.pyplot(fig)

    elif chart_type == "Line":
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(df[x].astype(str), df[y], marker="o")
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        plt.xticks(rotation=45)
        st.pyplot(fig)

    elif chart_type == "Pie":
        fig, ax = plt.subplots()
        ax.pie(df[y], labels=df[x].astype(str), autopct="%1.1f%%")
        ax.set_title(y + " by " + x)
        st.pyplot(fig)
else:
    st.info("Not enough categorical + numeric data to create a chart.")

# ================= DOWNLOAD =================
excel_buffer = BytesIO()
df.to_excel(excel_buffer, index=False)
excel_buffer.seek(0)

st.download_button(
    "📥 Download Excel",
    data=excel_buffer,
    file_name="data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ================= AI INSIGHT =================
st.subheader("🤖 AI Insight")
summary = explain(df)
st.write(summary)


