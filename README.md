# Machine Learning-Based Cancer Classification Using Gene Expression Data

This project compares logistic regression, a support vector machine and a random forest for classifying five tumour types from RNA sequencing data (UCI dataset 401).

## Structure

```text
src/                 Data loading, analysis, prediction and reporting scripts
notebooks/           Jupyter notebook with saved outputs
data/raw/            Original UCI download, cached snapshot and provenance
data/processed/      Validated expression data with class labels (CSV.gz)
models/              Full trained pipelines and label encoders
reports/tables/      Audits, split IDs, fold scores, predictions and metrics
reports/figures/     Figures in PNG and SVG formats
reports/             Academic report in editable Markdown
output/pdf/          Typeset academic report
tests/               Integrity checks for saved results and model reload
```

## Reproducing the analysis

Use Python 3.12 or a compatible recent Python version. In a terminal at this project root:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python src/load_data.py
.venv/Scripts/python src/analysis.py
.venv/Scripts/python src/build_report.py
.venv/Scripts/python tests/verify_artifacts.py
```

For the exact installed versions see `requirements-lock.txt`. The initial dataset download needs internet access and roughly 70 MB of transfer; allow additional disk space for the cached matrix, cleaned CSV, models and figures.

On first load, the script calls `fetch_ucirepo(id=401)`. If the API cannot return the expression data, the script downloads the UCI ZIP archive. `data/raw/provenance.json` records the retrieval method and any API error. Re-runs use the cached snapshot. `python src/load_data.py --refresh` retries the API; remove or rename the downloaded ZIP if a new archive download is needed. Never use a cached pickle or joblib from an untrusted source.

## Notebook

Open `notebooks/cancer_classification.ipynb` in Jupyter or VS Code and select the project environment. The delivered notebook contains executed outputs. To regenerate its unexecuted source, run `python src/make_notebook.py`. Run its cells in order to recompute the entire project. The notebook calls the same documented functions as the command-line workflow.

## Experimental protocol

Seed 42; stratified 80:20 split; five training-only CV folds. Each pipeline independently fits median imputation, zero-variance filtering and ANOVA selection of 500 genes. Logistic Regression and RBF SVM standardize those genes. Random Forest uses 300 trees without scaling. Highest mean CV macro F1 determines the selected model, with a prespecified simplicity tie-break. Test scores are reported for all three algorithms without using them to revise that choice. There is no hyperparameter tuning. PCA is training-fitted and used only for visualization, using all nonconstant genes.

The cleaned export is validated, unscaled data. Learned preprocessing is stored in model pipelines. The selected model is trained on the 640-sample training subset, not refitted on all samples after evaluation. Results and package versions are in `reports/tables/`; per-fold precision and recall as well as F1 and accuracy are preserved.

## Prediction example

```powershell
.venv/Scripts/python src/predict.py expression_profiles.csv predictions.csv
```

Input must contain sample IDs in its first column and the same 20,531 gene columns with compatible expression preprocessing. The script rejects missing or additional features and restores training column order. This is a benchmark demonstration, not a clinical prediction service.

## Interpretation

Anonymized genes cannot support verified pathway claims. Feature importance is predictive association, not causation. Internal accuracy does not establish clinical benefit; there are no healthy controls or external validation cohorts.

## Attribution

Fiorini, S. (2016). *gene expression cancer RNA-Seq*. UCI Machine Learning Repository. https://doi.org/10.24432/C5R88H. Dataset license: CC BY 4.0. Literature and software references appear in the academic report.
