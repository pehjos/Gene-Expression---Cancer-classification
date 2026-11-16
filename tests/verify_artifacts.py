"""Check sample separation, metric accounting, pipeline state and model persistence."""
from pathlib import Path
import sys
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from predict import predict_frame

tables=ROOT/'reports/tables'
membership=pd.read_csv(tables/'split_membership.csv')
assert membership.row_position.is_unique and len(membership)==801
train=membership[membership.split=='train'];test=membership[membership.split=='test']
assert set(train.row_position).isdisjoint(test.row_position)
assert len(train)==640 and len(test)==161
metrics=pd.read_csv(tables/'test_metrics.csv',index_col=0)
pred=pd.read_csv(tables/'test_predictions.csv')
for name in metrics.index:
    assert np.isclose(accuracy_score(pred.actual,pred[name]),metrics.loc[name,'accuracy'])
    assert np.isclose(f1_score(pred.actual,pred[name],average='macro'),metrics.loc[name,'f1_macro'])
    cm=pd.read_csv(tables/('confusion_'+name.lower().replace(' ','_')+'.csv'),index_col=0)
    assert cm.to_numpy().sum()==161
folds=pd.read_csv(tables/'cv_fold_metrics.csv')
assert len(folds)==15 and folds.groupby('model').size().eq(5).all()
selection=json.loads((tables/'selection.json').read_text())
means=folds.groupby('model').f1_macro.mean()
assert np.isclose(means[selection['best_model']],means.max())
bundle=joblib.load(ROOT/'models/best_model.joblib')
pipe=bundle['pipeline']
assert pipe.n_features_in_==20531 and pipe['select'].get_support().sum()==500
X,y=pd.read_pickle(ROOT/'data/raw/uci401.pkl')
X_test=X.iloc[test.row_position.to_numpy()]
assert np.array_equal(predict_frame(X_test).to_numpy(),pred[selection['best_model']].to_numpy())
# Confirm scaling uses selected training values, not globally fitted values.
if pipe['scale']!='passthrough':
    selected=pipe[:3].transform(X.iloc[train.row_position.to_numpy()])
    np.testing.assert_allclose(pipe['scale'].mean_,selected.mean(axis=0),rtol=1e-10,atol=1e-10)
    assert pipe['scale'].n_samples_seen_==640
try:
    predict_frame(X_test.drop(columns=X_test.columns[0]))
    raise AssertionError('Missing feature was accepted')
except ValueError:
    pass
for name in ['class_distribution','pca_visualization','model_comparison','top_genes']:
    assert (ROOT/f'reports/figures/{name}.png').stat().st_size>1000
assert (ROOT/'output/pdf/academic_report.pdf').stat().st_size>1000
print('PASS: sample separation, metric reconciliation, CV selection, pipeline state, schema validation and model reload.')
