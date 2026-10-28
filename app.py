from flask import Flask, render_template, request, redirect, jsonify
import pandas as pd
import sqlite3
import os
import re

app = Flask(__name__)

UPLOAD_FOLDER = 'data'
DB_PATH = 'database/placement.db'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('database', exist_ok=True)


# 🔹 HOME
@app.route('/')
def home():
    return render_template('index.html')


# 🔹 ABOUT
@app.route('/about')
def about():
    return render_template('about.html')


# 🔹 DATASET PAGE
@app.route('/dataset')
def dataset():
    return render_template('dataset.html')


# 🔹 UPLOAD
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['dataset']

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, 'placement_data.xlsx')
        file.save(filepath)

        df = pd.read_excel(filepath)

        conn = sqlite3.connect(DB_PATH)
        df.to_sql('placement', conn, if_exists='replace', index=False)
        conn.close()

        return redirect('/view')

    return "Upload failed"


# 🔹 DASHBOARD
@app.route('/view')
def view_data():

    if not os.path.exists(DB_PATH):
        return render_template('view_data.html', charts_exist=False)

    conn = sqlite3.connect(DB_PATH)

    try:
        df = pd.read_sql_query("SELECT * FROM placement", conn)
    except:
        conn.close()
        return render_template('view_data.html', charts_exist=False)

    if df.empty:
        conn.close()
        return render_template('view_data.html', charts_exist=False)

    # CLEAN
    df.columns = df.columns.str.strip()
    df['Placed'] = df['Placed'].astype(str).str.strip()
    df['Internship'] = df['Internship'].astype(str).str.strip()
    df['Salary'] = pd.to_numeric(df['Salary'], errors='coerce')
    df['CGPA'] = pd.to_numeric(df['CGPA'], errors='coerce')

    total_students = len(df)
    placed_students = len(df[df['Placed'] == 'Yes'])
    avg_salary = df[df['Salary'] > 0]['Salary'].mean()
    max_salary = df['Salary'].max()

    table_all = df.sort_values(by='Branch')

    table_placed = df[
        (df['Placed'] == 'Yes') &
        (df['Internship'] == 'Yes')
    ].sort_values(by='Branch')

    branch_group = df.groupby(['Branch', 'Placed']).size().unstack(fill_value=0)

    branch_group_data = {
        "branches": branch_group.index.tolist(),
        "yes": branch_group.get('Yes', pd.Series([0]*len(branch_group))).tolist(),
        "no": branch_group.get('No', pd.Series([0]*len(branch_group))).tolist()
    }

    placement_data = df['Placed'].value_counts().to_dict()
    salary_data = df['Salary'].dropna().tolist()
    cgpa_salary_data = df[['CGPA', 'Salary']].dropna().to_dict(orient='records')
    avg_salary_branch = df[df['Salary'] > 0].groupby('Branch')['Salary'].mean().to_dict()

    conn.close()

    return render_template(
        'view_data.html',
        charts_exist=True,
        table_all=table_all.to_html(classes='table table-striped', index=False),
        table_placed=table_placed.to_html(classes='table table-striped', index=False),
        total=total_students,
        placed=placed_students,
        avg=round(avg_salary, 2) if avg_salary else 0,
        branch_group=branch_group_data,
        placement_data=placement_data,
        salary_data=salary_data,
        cgpa_salary_data=cgpa_salary_data,
        avg_salary_branch=avg_salary_branch,
        max_salary=max_salary
    )


# 🤖 SMART CHATBOT (FINAL VERSION)
@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_input = data.get("message", "").lower()

    if not os.path.exists(DB_PATH):
        return jsonify({"response": "Please upload dataset first 📂"})

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM placement", conn)
    conn.close()

    if df.empty:
        return jsonify({"response": "Dataset is empty 😅"})

    # CLEAN
    df.columns = df.columns.str.strip()
    df['Placed'] = df['Placed'].astype(str).str.strip()
    df['Salary'] = pd.to_numeric(df['Salary'], errors='coerce')
    df['CGPA'] = pd.to_numeric(df['CGPA'], errors='coerce')

    # 🔥 SYNONYMS
    synonyms = {
        "package": "salary",
        "pay": "salary",
        "job": "placed",
        "hired": "placed",
        "cs": "computer science",
        "it": "information technology",
        "mech": "mechanical",
        "ece": "electronics",
        "avg": "average",
        "suggestions": "suggest",
        "advice": "suggest"
    }

    for word, replacement in synonyms.items():
        user_input = re.sub(r'\b' + re.escape(word) + r'\b', replacement, user_input)

    # 📊 CALCULATIONS
    total = len(df)
    placed = len(df[df['Placed'] == 'Yes'])
    not_placed = len(df[df['Placed'] == 'No'])

    avg_salary = df[df['Salary'] > 0]['Salary'].mean()
    max_salary = df['Salary'].max()
    max_cgpa = df['CGPA'].max()

    placement_rate = (placed / total) * 100 if total > 0 else 0

    placed_df = df[df['Placed'] == 'Yes']
    top_branch = placed_df['Branch'].value_counts().idxmax() if not placed_df.empty else "N/A"

    # =========================
    # 🔥 SMART INTENTS
    # =========================

    if "total" in user_input:
        return jsonify({"response": f"Total students are {total}"})

    if "not placed" in user_input:
        return jsonify({"response": f"{not_placed} students are not placed"})

    if "placed" in user_input:
        return jsonify({"response": f"{placed} students are placed"})

    if "average" in user_input and "salary" in user_input:
        return jsonify({"response": f"Average salary is {round(avg_salary,2)} LPA"})

    if "highest" in user_input and "salary" in user_input:
        return jsonify({"response": f"Highest salary is {max_salary} LPA"})

    if "cgpa" in user_input:
        return jsonify({"response": f"Highest CGPA is {max_cgpa}"})

    if "placement rate" in user_input or ("placement" in user_input and "rate" in user_input):
        return jsonify({"response": f"Placement rate is {round(placement_rate,2)}%"})

    if "branch" in user_input and ("highest" in user_input or "top" in user_input):
        return jsonify({"response": f"{top_branch} has the highest placements"})

    if "suggest" in user_input or "why" in user_input or "improve" in user_input:
        return jsonify({
            "response": "Improve CGPA, build projects, gain skills, and complete internships."
        })

    # 🔹 BRANCH SPECIFIC
    for branch in df['Branch'].unique():
        if branch.lower() in user_input:
            count = len(df[(df['Branch'] == branch) & (df['Placed'] == 'Yes')])
            return jsonify({"response": f"{count} students placed in {branch}"})

    # ❌ FALLBACK
    return jsonify({
        "response": "Try asking: total students, not placed, highest CGPA, top branch 😊"
    })


# 🔹 RUN
if __name__ == '__main__':
    app.run(debug=True)