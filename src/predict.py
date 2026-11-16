"""Predict supplied benchmark-compatible profiles with the saved training pipeline."""
import argparse
import joblib
import pandas as pd
from load_data import ROOT

def predict_frame(frame, model_path=None):
    bundle=joblib.load(model_path or ROOT/'models/best_model.joblib')
    expected=bundle['feature_names']
    missing=set(expected)-set(frame.columns)
    extra=set(frame.columns)-set(expected)
    if missing or extra:
        raise ValueError(f'Feature schema mismatch: {len(missing)} missing, {len(extra)} extra columns')
    encoded=bundle['pipeline'].predict(frame.loc[:,expected])
    return pd.Series(bundle['label_encoder'].inverse_transform(encoded),index=frame.index,name='predicted_class')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_csv',help='CSV with sample IDs in the first column and all original gene columns')
    parser.add_argument('output_csv')
    args=parser.parse_args()
    predict_frame(pd.read_csv(args.input_csv,index_col=0)).to_csv(args.output_csv,index_label='sample_id')
