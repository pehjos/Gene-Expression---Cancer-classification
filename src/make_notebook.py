"""Build the explained, executable notebook from the shared analysis functions."""
from pathlib import Path
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]
nb=nbf.v4.new_notebook()
cells=[]
def md(text):cells.append(nbf.v4.new_markdown_cell(text))
def code(text):cells.append(nbf.v4.new_code_cell(text))
md('# Machine Learning-Based Cancer Classification Using Gene Expression Data\n\nThe analysis compares three classifiers on RNA sequencing profiles from five tumour types in UCI dataset 401.')
md('## 1. Analysis setup\nThe notebook uses the preprocessing and evaluation functions in the project scripts. The split and randomized algorithms use seed 42.')
code("from pathlib import Path\nimport sys\nROOT = Path.cwd()\nif not (ROOT / 'src').exists(): ROOT = ROOT.parent\nsys.path.insert(0, str(ROOT / 'src'))\nimport json, platform\nfrom importlib.metadata import version\nimport pandas as pd\nfrom IPython.display import display, Image\nfrom analysis import *\nfrom load_data import prepare_folders\nprepare_folders()\nprint('Project directories are ready.')")
md('## 2. Data source and quality checks\nExpression values and tumour labels come from UCI dataset 401. The loader uses the UCI download archive when the API cannot return the data and records how the dataset was retrieved. Cached runs reuse the same snapshot. The audit checks dimensions, label alignment, missing values, finite numeric values and duplicate expression rows. Descriptive statistics are observational; no fitted preprocessing uses the complete dataset.')
code("X, y, audit = load_data()\ndisplay(X.iloc[:5, :8])\ndisplay(y.value_counts().rename('count').to_frame())\ndisplay(X.iloc[:, :8].describe().T)")
md('## 3. Stratified split and label encoding\nWe reserve 20% of samples as a test set. Stratification approximately preserves class proportions. LabelEncoder learns the five names from training labels and maps them to integer codes. These codes are categories, not ordered cancer severity. Split membership and label mapping are saved.')
code("X_train, X_test, y_train, y_test, encoder = prepare_split(X, y)\nprint('Train:', X_train.shape, 'Test:', X_test.shape)\nprint(dict(enumerate(encoder.classes_)))")
md('## 4. Preprocessing and model definitions\nEach pipeline contains training-fitted median imputation, removal of constant genes and ANOVA selection of 500 genes. Logistic Regression and SVM also standardize selected features; Random Forest does not require scaling. Keeping these operations inside the pipeline prevents leakage during cross-validation. The 500-gene choice and model settings were fixed before evaluation; there is no test-driven tuning.')
code("models = build_models()\nfor name, model in models.items():\n    print(name)\n    display(model)")
md('## 5. Cross-validation and model selection\nFive stratified training folds estimate accuracy and macro precision, recall and F1. Macro averages give every class equal weight. Every fold fits its own preprocessing. We choose the largest mean macro F1; exact ties favor Logistic Regression, then SVM, then Random Forest. Test results play no part in this decision.')
code("folds, cv_summary, best = compare_cv(X_train, y_train, models)\ndisplay(folds)\ndisplay(cv_summary)\nprint('Selected model:', best)")
md('## 6. Held-out evaluation\nEach model is fitted on the training set and evaluated on the same held-out samples. The saved results include per-class metrics, confusion matrices and sample-level predictions. Cross-validation fold SD measures fold variability; it is not a confidence interval or proof of superiority.')
code("fitted, metrics = evaluate_models(X_train, X_test, y_train, y_test, encoder, models)\ndisplay(metrics)\nfor name in models:\n    slug = name.lower().replace(' ', '_')\n    print(name)\n    display(pd.read_csv(TABLES / f'confusion_{slug}.csv', index_col=0))")
md('## 7. PCA and feature importance\nPCA is a separate unsupervised view of all nonconstant genes. Its scaling and components are fitted only on training data; test points are projected. The two PCs are not used as classifier features. The Random Forest plot reports training impurity importance among selected genes. Anonymous feature names cannot establish gene functions, causal drivers or biomarkers.')
code("make_visualizations(X_train, X_test, y_train, y_test, encoder, y, fitted, metrics, cv_summary, best)\nfor name in ['class_distribution', 'pca_visualization', 'model_comparison', 'confusion_' + best.lower().replace(' ', '_'), 'top_genes']:\n    display(Image(filename=str(FIGURES / (name + '.png')), width=850))")
md('## 8. Analysis settings and outputs\nThe environment file records Python and package versions, the random seed, the split sizes and the number of selected genes.')
code("environment = {'python': platform.python_version(), 'packages': {p: version(p) for p in ['numpy','pandas','scikit-learn','matplotlib','seaborn','ucimlrepo','joblib']}, 'seed': SEED, 'test_size': .2, 'cv_folds': 5, 'selected_genes': K_GENES, 'train_samples': len(X_train), 'test_samples': len(X_test)}\n(TABLES / 'environment.json').write_text(json.dumps(environment, indent=2))\nfrom build_report import build_report\nbuild_report()")
md('## 9. Interpretation and limitations\nHigh internal accuracy shows association with supplied labels, not clinical utility. Tissue identity, batch effects and other unmeasured factors may contribute. The cohort lacks healthy controls and an independent external validation set. Anonymous gene labels prevent verified pathway or gene-function interpretation. Many more genes than samples make dimensionality control important, but this experiment does not prove that 500 genes is optimal. A single split and five folds do not demonstrate general superiority.')
nb.cells=cells
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}}
path=ROOT/'notebooks/cancer_classification.ipynb';path.parent.mkdir(exist_ok=True)
nbf.write(nb,path)
print(path)
