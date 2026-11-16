"""Step 1: fetch, validate and cache the official UCI dataset (no fitted preprocessing)."""
from pathlib import Path
import json
import hashlib
import io
import tarfile
import zipfile
import urllib.request
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from ucimlrepo import fetch_ucirepo

ROOT = Path(__file__).resolve().parents[1]

def prepare_folders():
    for folder in ['data/raw', 'data/processed', 'models', 'notebooks',
                   'reports/figures', 'reports/tables', 'output/pdf', 'tmp/pdfs']:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)

def load_data(refresh=False):
    """Use the requested API on first run; later runs reuse the exact local snapshot."""
    prepare_folders()
    cache = ROOT / 'data/raw/uci401.pkl'
    if cache.exists() and not refresh:
        X, y = pd.read_pickle(cache)
    else:
        method = 'ucimlrepo.fetch_ucirepo(id=401)'
        api_error = None
        try:
            dataset = fetch_ucirepo(id=401)
            X = dataset.data.features
            y = dataset.data.targets
        except Exception as exc:
            # Some UCI entries advertise the API but provide no API data_url.
            # Use only the official downloadable archive, never synthetic substitutes.
            api_error = f'{type(exc).__name__}: {exc}'
            print('Requested API could not load the data:', api_error, flush=True)
            url = 'https://archive.ics.uci.edu/static/public/401/gene%2Bexpression%2Bcancer%2Brna%2Bseq.zip'
            archive = ROOT / 'data/raw/uci401.zip'
            if not archive.exists():
                print('Downloading the official UCI archive...', flush=True)
                with urllib.request.urlopen(url, timeout=180) as response:
                    temporary = archive.with_suffix('.zip.part')
                    with temporary.open('wb') as output:
                        import shutil
                        shutil.copyfileobj(response, output)
                    temporary.replace(archive)
            with zipfile.ZipFile(archive) as z:
                member = next(n for n in z.namelist() if n.endswith('.tar.gz'))
                with tarfile.open(fileobj=io.BytesIO(z.read(member)), mode='r:gz') as tar:
                    # Read CSV members directly; do not extract archive paths.
                    data_member = next(m for m in tar.getmembers() if m.name.endswith('/data.csv'))
                    labels_member = next(m for m in tar.getmembers() if m.name.endswith('/labels.csv'))
                    X = pd.read_csv(tar.extractfile(data_member), index_col=0)
                    y = pd.read_csv(tar.extractfile(labels_member), index_col=0)
            method = 'Official UCI ZIP archive (API unavailable)'
        if X is None or y is None:
            raise ValueError('UCI returned no feature or target data.')
        pd.to_pickle((X, y), cache)
        provenance = {'dataset_id': 401, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                      'source': 'https://doi.org/10.24432/C5R88H',
                      'method': method, 'api_error': api_error,
                      'sha256': hashlib.sha256(cache.read_bytes()).hexdigest()}
        if method != 'ucimlrepo.fetch_ucirepo(id=401)':
            provenance['archive_url'] = url
            provenance['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
        (ROOT / 'data/raw/provenance.json').write_text(json.dumps(provenance, indent=2))
    y = y.squeeze('columns').rename('cancer_class') if isinstance(y, pd.DataFrame) else y.rename('cancer_class')
    if X.shape != (801, 20531) or set(y.unique()) != {'BRCA','KIRC','COAD','LUAD','PRAD'}:
        raise ValueError(f'Unexpected dataset schema: {X.shape}, {y.unique()}')
    if not X.index.equals(y.index) or y.isna().any():
        raise ValueError('Labels must be complete and aligned with sample rows.')
    if not all(pd.api.types.is_numeric_dtype(t) for t in X.dtypes):
        raise ValueError('Features must be numeric; investigate rather than silently coercing.')
    if np.isinf(X.to_numpy()).any():
        raise ValueError('Infinite measurements require source investigation.')
    duplicate = X.duplicated(keep=False)
    audit = {'samples': len(X), 'features': X.shape[1],
             'missing_feature_values': int(X.isna().sum().sum()),
             'missing_target_values': int(y.isna().sum()),
             'duplicate_feature_rows_extra': int(X.duplicated().sum()),
             'class_counts': {str(k): int(v) for k,v in y.value_counts().sort_index().items()},
             'majority_minority_ratio': float(y.value_counts().max()/y.value_counts().min())}
    # Stop if duplicates occur: random splitting could put identical samples in both sets.
    if duplicate.any():
        raise ValueError('Duplicate expression rows detected: investigate identities and use group splitting.')
    (ROOT / 'reports/tables/data_audit.json').write_text(json.dumps(audit, indent=2))
    statistics_path = ROOT / 'reports/tables/gene_summary_statistics.csv'
    cleaned_path = ROOT / 'data/processed/cleaned_expression.csv.gz'
    if refresh or not statistics_path.exists():
        X.describe().T.to_csv(statistics_path)
    if refresh or not cleaned_path.exists():
        pd.concat([X,y],axis=1).to_csv(cleaned_path, index_label='sample_id')
    print(json.dumps(audit, indent=2))
    print('\nFirst five genes - descriptive statistics:\n', X.iloc[:,:5].describe())
    print('\nLabels:', sorted(y.unique()))
    return X, y, audit

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    load_data(refresh=parser.parse_args().refresh)
