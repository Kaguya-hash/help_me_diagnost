import os
import json
import threading

from flask import Flask, render_template, request
import csv
import io
from pathlib import Path
import math
import subprocess
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from datetime import datetime

from errors import error_redirect, get_error


load_dotenv()
curr_dir = Path(__file__).resolve().parent
app = Flask(__name__)


def delete_comparation(comparation_id):
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM comparisons 
                    WHERE comparison_id = %(comparation_id)s;
                    """, {"comparation_id": comparation_id})
                conn.commit()
    except Exception:
        pass
    return


def run_heavy_r_task(comparison_id, disease_1, disease_2, file_content):
    try:
        result_r = subprocess.run(
            ["Rscript", "train_lr_lasso.R", disease_1, disease_2],
            cwd=curr_dir,
            input=file_content.read(),
            check=True,
            capture_output=True,
        )
    except Exception:
        delete_comparation(comparison_id)
        return

    try:
        genes_data = json.loads(result_r.stdout.decode("utf-8"))

        symbols = []
        values = []
        intercept_value = None

        for gene, weight in zip(genes_data["Gene"], genes_data["Weight"]):
            if gene == "(Intercept)":
                intercept_value = weight
            else:
                symbols.append(gene)
                values.append(weight)

        if intercept_value is None or not symbols:
            raise ValueError("The R task returned an incomplete model result.")
    except Exception:
        delete_comparation(comparison_id)
        return

    try:
        with psycopg.connect(os.getenv("DATABASE_URL"), row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                        UPDATE comparisons SET intercept = %(intercept)s
                        WHERE comparison_id = %(comparison_id)s
                    """,
                    {"intercept": intercept_value, "comparison_id": comparison_id},
                )

                cur.execute(
                    """
                        INSERT INTO genes (symbol)
                        SELECT UNNEST(%(symbols)s::text[])
                        ON CONFLICT (symbol) DO UPDATE SET symbol = EXCLUDED.symbol
                        RETURNING gene_id, symbol
                    """,
                    {"symbols": symbols},
                )

                gene_to_value = dict(zip(symbols, values))

                coefficient_rows = [
                    {
                        "comparison_id": comparison_id,
                        "gene_id": row["gene_id"],
                        "value": gene_to_value.get(row["symbol"]),
                    }
                    for row in cur.fetchall()
                ]

                if coefficient_rows:
                    cur.executemany(
                        """
                            INSERT INTO coefficients (comparison_id, gene_id, value)
                            VALUES (%(comparison_id)s, %(gene_id)s, %(value)s)
                        """,
                        coefficient_rows,
                    )

                cur.execute("""
                        UPDATE comparisons SET status = %(status)s
                        WHERE comparison_id = %(comparison_id)s
                        """, {"status": "DONE", "comparison_id": comparison_id})

                conn.commit()
    except Exception:
        delete_comparation(comparison_id)
        return
    
    return


@app.route("/error")
def error_page():
    code = request.args.get("code", "unknown")
    error = get_error(code)
    return render_template("error.html", error=error, code=code)


@app.route("/", methods=["GET"])
def index():
    rows = []

    try:
        with psycopg.connect(os.getenv("DATABASE_URL"), row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        c.model_name,
                        d1.name AS class_a,
                        d2.name AS class_b
                    FROM comparisons c
                    JOIN diseases d1
                        ON c.class_a = d1.disease_id
                    JOIN diseases d2
                        ON c.class_b = d2.disease_id
                    WHERE c.status = %(status)s
                    """, {"status": "DONE"})
                rows = cur.fetchall()
    except Exception:
        return error_redirect("index_db_error")

    return render_template("index.html", rows=rows)


@app.route("/test", methods=["GET", "POST"])
def test_page():
    rows = []
    percentage_d1 = None
    percentage_d2 = None
    missing_genes = []
    filename = None
    disease1_name = None
    disease2_name = None

    if request.method == "POST":
        comparison_id = request.form.get("comparison_id")

        if not comparison_id or not comparison_id.isdigit():
            return error_redirect("test_invalid_comparison")

        try:
            with psycopg.connect(os.getenv("DATABASE_URL"), row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH
                            coef AS (
                                SELECT gene_id, value FROM coefficients WHERE comparison_id = %(comparison_id)s
                            )
                        SELECT g.symbol, c.value
                        FROM genes g
                        JOIN coef c ON g.gene_id = c.gene_id
                    """, {"comparison_id": comparison_id})

                    genes = cur.fetchall()

                    cur.execute("""
                        SELECT d1.name AS name_1, d2.name AS name_2, c.intercept
                        FROM comparisons c
                        JOIN diseases d1 ON c.class_a = d1.disease_id
                        JOIN diseases d2 ON c.class_b = d2.disease_id
                        WHERE c.comparison_id = %(comparison_id)s
                    """, {"comparison_id": comparison_id})

                    info = cur.fetchone()
        except Exception:
            return error_redirect("test_db_error")

        if info is None:
            return error_redirect("test_model_not_found")

        csv_file = request.files.get("csv_file")

        if not csv_file or not csv_file.filename:
            return error_redirect("test_no_file")

        if not csv_file.filename.lower().endswith(".csv"):
            return error_redirect("test_invalid_file")

        filename = csv_file.filename

        try:
            stream = io.StringIO(csv_file.stream.read().decode("utf-8"))
            reader = csv.DictReader(stream)

            if not reader.fieldnames or "Gene" not in reader.fieldnames or "Expression" not in reader.fieldnames:
                return error_redirect("test_csv_columns")

            gene_lookup = {gene["symbol"]: gene["value"] for gene in genes}
            mu = 0

            for row in reader:
                symbol = row["Gene"]
                if symbol in gene_lookup:
                    mu += gene_lookup.pop(symbol) * float(row["Expression"])

            missing_genes = list(gene_lookup.keys())
        except UnicodeDecodeError:
            return error_redirect("test_csv_encoding")
        except (ValueError, TypeError):
            return error_redirect("test_csv_expression")
        except KeyError:
            return error_redirect("test_csv_columns")
        except Exception:
            return error_redirect("test_csv_invalid")

        mu += info["intercept"]

        percentage_d1 = (1.0 / (1.0 + math.exp(-mu))) * 100.0
        percentage_d2 = 100.0 - percentage_d1
        disease1_name = info["name_1"]
        disease2_name = info["name_2"]

    try:
        with psycopg.connect(os.getenv("DATABASE_URL"), row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        c.comparison_id,
                        c.model_name,
                        d1.name AS name_1,
                        d2.name AS name_2
                    FROM comparisons c
                    JOIN diseases d1
                        ON c.class_a = d1.disease_id
                    JOIN diseases d2
                        ON c.class_b = d2.disease_id
                    WHERE c.status = %(status)s
                    """, {"status": "DONE"})
                rows = cur.fetchall()
    except Exception:
        if request.method != "POST" or percentage_d1 is None:
            return error_redirect("test_db_error")
        rows = []

    return render_template(
        "test.html",
        rows=rows,
        filename=filename,
        disease1_name=disease1_name,
        disease2_name=disease2_name,
        percentage_d1=percentage_d1,
        percentage_d2=percentage_d2,
        missing_genes=missing_genes,
    )


@app.route("/model", methods=["GET", "POST"])
def model_page():
    if request.method == "POST":
        disease_1 = request.form.get("disease_1", "").strip().lower().replace(" ", "_")
        disease_2 = request.form.get("disease_2", "").strip().lower().replace(" ", "_")
        name_of_model = request.form.get("name_of_model", "").strip().lower().replace(" ", "_")

        if disease_1 == disease_2 or disease_1 == "" or disease_2 == "" or name_of_model == "":
            return error_redirect("model_invalid_fields")
        
        try:
            with psycopg.connect(os.getenv("DATABASE_URL"), row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        WITH
                            d AS (
                                INSERT INTO diseases (name) VALUES (%(name_1)s), (%(name_2)s)
                                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                                RETURNING disease_id
                            ),
                            comp AS (
                                INSERT INTO comparisons (class_a, class_b, model_name, status, date)
                                SELECT a.disease_id, b.disease_id, %(model_name)s, %(status)s, %(date)s
                                FROM d a, d b
                                WHERE a.disease_id < b.disease_id
                                ON CONFLICT ON CONSTRAINT comparisons_unordered_unique
                                DO NOTHING
                                RETURNING comparison_id
                            )
                        SELECT (SELECT comparison_id FROM comp) AS comparison_id
                        """, 
                        {
                            "name_1": disease_1, 
                            "name_2": disease_2, 
                            "model_name": name_of_model, 
                            "status": "NOT_DONE",
                            "date": datetime.now().replace(microsecond=0)
                        }
                    )

                    result = cur.fetchone()

                    if result is None or result["comparison_id"] is None:
                        conn.rollback()
                        return error_redirect("model_duplicate")
        except Exception:
            conn.rollback()
            return error_redirect("model_db_save_error")

        rdata_file = request.files.get("rdata_file")

        if not rdata_file or not rdata_file.filename:
            return error_redirect("model_no_file")

        if not Path(rdata_file.filename).suffix.lower() in {".rdata", ".rda"}:
            return error_redirect("model_invalid_file")

        thread = threading.Thread(
            target=run_heavy_r_task,
            args=(result["comparison_id"], disease_1, disease_2, rdata_file),
            daemon=True,
        )
        thread.start()

    return render_template("model.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
