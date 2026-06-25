# Help Me Diagnost

A web application for **binary disease classification from gene expression data**. Upload training data, fit a sparse logistic regression model with LASSO, and run predictions on new patient samples — all through a simple browser interface.

Built during **[Iberian Modeling Week 2026](https://www.math-in.net/iberian/)** (Lisbon), originally for **Problem 3: Predicting brain tumor subtypes from gene expression data** (coordinator: Dr. Marta Lopes, NOVA School of Science and Technology). The challenge focused on distinguishing lower-grade gliomas — **oligodendroglioma** vs **astrocytoma** — using RNA-sequencing data from TCGA. This project generalizes that setup so you can train and deploy classifiers for **any pair of disease subtypes or conditions**.

---

## Motivation

Gliomas and many other diseases are hard to diagnose because they vary widely between patients. RNA-seq captures the activity of thousands of genes per tumor sample, offering a rich signal for classification — but also a high-dimensional, hard-to-interpret feature space.

This tool addresses two goals from the original challenge:

1. **Classify** patients into the correct disease subtype using gene expression profiles.
2. **Identify a small, interpretable set of genes** that drive the discrimination, via LASSO-regularized logistic regression.

The same workflow applies beyond gliomas: any binary comparison (disease A vs disease B) with per-patient gene expression matrices can be registered and used for inference.

---

## Live demo

You can try the app online at **[https://help-me-diagnost.onrender.com/](https://help-me-diagnost.onrender.com/)**, hosted on [Render](https://render.com/)'s free tier.

The **Test** page works well on the live deployment — browse registered models and run predictions on your own CSV samples.

**Be careful with the Model page.** Registering a new model runs R in the background (`cv.glmnet` on full expression matrices), which is memory-intensive. On Render's free plan the instance has limited RAM, so large datasets or many genes can **exceed available memory** and cause training to fail; use the live site mainly for inference on models that are already registered.

---

## How it works

```
┌─────────────────┐     RData upload      ┌──────────────────┐
│  Register model │ ────────────────────► │  train_lr_lasso.R │
│  (Flask + R)    │                       │  (glmnet / LASSO) │
└────────┬────────┘                       └────────┬─────────┘
         │                                         │
         │  sparse coefficients + intercept        │
         ▼                                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL (Neon)                        │
│  diseases · comparisons · genes · coefficients · patients  │
└──────────────────────────────┬──────────────────────────────┘
                               │
         CSV upload (Gene, Expression) │
                               ▼
                    ┌──────────────────┐
                    │  Run prediction  │
                    │  P(class A) via  │
                    │  logistic model  │
                    └──────────────────┘
```

### Model training (`train_lr_lasso.R`)

When you register a model, the backend runs an R script that:

1. Loads two patient × gene matrices from your `.RData` file (one per disease class).
2. Removes the **lowest 10% of genes by variance** across the combined dataset.
3. Fits **5-fold cross-validated LASSO logistic regression** (`cv.glmnet`, binomial family, `alpha = 1`).
4. Selects **`lambda.1se`** (one-standard-error rule) for a sparser, more stable model.
5. Returns non-zero coefficients sorted by absolute weight, plus the intercept.

Only genes with non-zero LASSO weights are stored — giving you an interpretable biomarker panel.

### Prediction

On the **Test** page, you select a registered model and upload a CSV with `Gene` and `Expression` columns. The app computes:

\[
P(\text{class A}) = \sigma\left(\beta_0 + \sum_j \beta_j \cdot x_j\right)
\]

where \(\sigma\) is the logistic function, \(\beta_0\) is the stored intercept, and \(x_j\) are expression values for genes present in both the model and your sample. Missing genes in the CSV are reported but do not block the prediction.

---

## Features

- **Register models** — upload an RData file with expression matrices for two disease classes; training runs asynchronously in the background.
- **Run diagnostic tests** — upload a CSV sample and get class probabilities with a visual breakdown.
- **Browse registered comparisons** — home page lists all successfully trained model / disease-pair combinations.
- **Automatic cleanup** — completed and failed models are purged from the database; stale pending jobs older than 7 days are removed.
- **Docker-ready** — single container with Python, R, `glmnet`, and Gunicorn.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Web framework | [Flask](https://flask.palletsprojects.com/) |
| Database | [PostgreSQL](https://www.postgresql.org/) ([Neon](https://neon.tech/)) via `psycopg` |
| ML / statistics | [R](https://www.r-project.org/) with [`glmnet`](https://glmnet.stanfor.edu/) and [`jsonlite`](https://cran.r-project.org/package=jsonlite) |
| Production server | [Gunicorn](https://gunicorn.org/) |
| Frontend | Server-rendered Jinja2 templates, vanilla CSS/JS |

---

## Database schema

The application uses the `public` schema. Auth tables under `neon_auth` are managed by Neon and are not used by the app logic.

### Core tables

| Table | Purpose |
|-------|---------|
| `diseases` | Disease subtypes / classes (`name`, optional `description`) |
| `comparisons` | A trained classifier linking two diseases (`class_a`, `class_b`, `model_name`, `intercept`, `status`, `date`) |
| `genes` | Gene symbols referenced by models |
| `coefficients` | LASSO weight per gene for each comparison |
| `patients` | Patient records tied to a comparison and disease label |
| `patient_gene_expression` | Per-patient, per-gene expression values |

### Key relationships

- A **comparison** always pairs two distinct diseases (`class_a < class_b` enforced by constraint).
- Each `(class_a, class_b, model_name)` triple is unique.
- **Coefficients** cascade-delete when their comparison is removed.
- Comparison **status** is stored as JSON, e.g. `{"status": "PENDING"}`, `{"status": "DONE"}`, or `{"status": "ERROR"}`.

---

## Getting started

### Prerequisites

- Python 3.11+
- R with packages `glmnet` and `jsonlite` (included in the Docker image)
- A PostgreSQL database (e.g. [Neon](https://neon.tech/)) with the schema applied

---

## Usage

### 1. Prepare training data (R)

Save an `.RData` file containing **two data frames or matrices**, one per disease class. Object names must match the disease names you will enter in the form (lowercase, spaces replaced with underscores).

Each matrix should have **patients as rows** and **genes as columns** (column names = gene symbols).

Example for the original glioma challenge:

```r
# oligodendroglioma: n1 patients × p genes
# astrocytoma:       n2 patients × p genes
save(oligodendroglioma, astrocytoma, file = "glioma_data.RData")
```

### 2. Register a model

1. Open **Model** in the navigation.
2. Enter names for **Disease class A** and **Disease class B** (e.g. `oligodendroglioma`, `astrocytoma`).
3. Provide a unique **Model name** (e.g. `lasso_lr_v1`).
4. Upload your `.RData` / `.rda` file and submit.

Training runs in a background thread. A loading page polls `/status/<comparison_id>` until the job finishes. On success, the model appears on the home page.

### 3. Run a prediction

1. Open **Test**.
2. Select a registered model from the dropdown.
3. Upload a CSV file with columns **`Gene`** and **`Expression`**:

```csv
Gene,Expression
TP53,2.41
EGFR,0.87
IDH1,1.05
```

4. Submit to see predicted probabilities for each disease class.

If your sample is missing genes that the model uses, those genes are listed as a warning; the prediction still runs on the genes that are present.

---

## Project structure

```
help_me_diagnost/
├── app.py                 # Flask application and API routes
├── train_lr_lasso.R       # LASSO logistic regression training script
├── errors.py              # User-facing error messages
├── requirements.txt       # Python dependencies
├── Dockerfile             # Production image (Python + R + Gunicorn)
├── templates/             # Jinja2 HTML templates
├── static/                # CSS and JavaScript
└── uploads/               # Temporary RData files during training (auto-cleaned)
```

---

## API routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Home — list registered models |
| `/model` | GET, POST | Register a new model |
| `/test` | GET, POST | Run a prediction on uploaded CSV |
| `/status/<task_id>` | GET | Poll training job status (JSON) |
| `/error?code=...` | GET | Display a friendly error page |

---

## Background knowledge

The original challenge expected familiarity with:

- **R** for data analysis and statistical modeling
- **Machine learning** basics (train/test splits, regularization, classification metrics)
- **Gene expression data** — RNA-seq counts or normalized expression values from resources like [TCGA](https://www.cancer.gov/tcga)

Participants were asked to balance predictive accuracy with **model interpretability** by surfacing the genes most relevant to subtype discrimination — exactly what LASSO logistic regression provides.

---

## Acknowledgements

- **Iberian Modeling Week 2026**, Lisbon
- **Problem 3** — Dr. Marta Lopes, NOVA School of Science and Technology, Portugal
- TCGA and the cancer genomics community for open expression datasets
