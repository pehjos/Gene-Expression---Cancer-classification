"""Reproducible training, evaluation and figures; all learned steps stay inside pipelines."""
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'tmp/matplotlib'))
import platform
import time
from importlib.metadata import version
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import VarianceThreshold, SelectKBest, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.svm import SVC
from threadpoolctl import threadpool_limits
from load_data import ROOT, load_data

SEED = 42
K_GENES = 500
TABLES = ROOT / 'reports/tables'
FIGURES = ROOT / 'reports/figures'

def save_figure(name):
    plt.tight_layout()
    plt.savefig(FIGURES / f'{name}.png', dpi=220, bbox_inches='tight')
    plt.savefig(FIGURES / f'{name}.svg', bbox_inches='tight')
    plt.close()

def build_models():
    """ANOVA selects 500 genes using training labels; forests need no scaling."""
    algorithms = {
        'Logistic Regression': LogisticRegression(C=1.0, max_iter=5000, random_state=SEED),
        'Support Vector Machine': SVC(C=1.0, kernel='rbf', gamma='scale', random_state=SEED),
        'Random Forest': RandomForestClassifier(n_estimators=300, max_features='sqrt',
                                                random_state=SEED, n_jobs=2),
    }
    return {name: Pipeline([
        ('imputer', SimpleImputer(strategy='median', keep_empty_features=True)),
        ('variance', VarianceThreshold(threshold=0.0)),
        ('select', SelectKBest(score_func=f_classif, k=K_GENES)),
        ('scale', 'passthrough' if name == 'Random Forest' else StandardScaler()),
        ('classifier', model)]) for name,model in algorithms.items()}

def prepare_split(X, y):
    """Hold out 20% before learning preprocessing; encode names from training labels."""
    train, test = train_test_split(np.arange(len(X)), test_size=0.20, stratify=y, random_state=SEED)
    encoder = LabelEncoder().fit(y.iloc[train])
    y_train, y_test = encoder.transform(y.iloc[train]), encoder.transform(y.iloc[test])
    pd.DataFrame({'row_position': np.r_[train,test],
                  'sample_id': X.index.to_numpy()[np.r_[train,test]],
                  'split': ['train']*len(train)+['test']*len(test)}).to_csv(TABLES/'split_membership.csv',index=False)
    (TABLES/'label_mapping.json').write_text(json.dumps({c:int(i) for i,c in enumerate(encoder.classes_)},indent=2))
    return X.iloc[train], X.iloc[test], y_train, y_test, encoder

def compare_cv(X_train,y_train,models):
    """Refit the whole pipeline independently in each stratified training fold."""
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    scoring={'accuracy':'accuracy','precision_macro':'precision_macro',
             'recall_macro':'recall_macro','f1_macro':'f1_macro'}
    rows=[]
    for name,pipeline in models.items():
        print(f'Cross-validation: {name}',flush=True)
        with threadpool_limits(limits=2):
            scores=cross_validate(pipeline,X_train,y_train,cv=cv,scoring=scoring,n_jobs=1,error_score='raise')
        for fold in range(5):
            rows.append({'model':name,'fold':fold+1,
                         **{metric:float(scores['test_'+metric][fold]) for metric in scoring},
                         'fit_seconds':float(scores['fit_time'][fold])})
    folds=pd.DataFrame(rows)
    folds.to_csv(TABLES/'cv_fold_metrics.csv',index=False)
    summary=folds.groupby('model')[list(scoring)].agg(['mean','std'])
    summary.columns=['cv_'+a+'_'+b for a,b in summary.columns]
    # Prespecified tie rule favors the simpler linear model, then SVM, then forest.
    summary['tie_priority']=[list(models).index(name) for name in summary.index]
    summary=summary.sort_values(['cv_f1_macro_mean','tie_priority'],ascending=[False,True])
    summary.to_csv(TABLES/'cv_summary.csv')
    best=summary.index[0]
    (TABLES/'selection.json').write_text(json.dumps({'best_model':best,
        'criterion':'Highest training-only five-fold mean macro F1; exact ties: Logistic Regression, SVM, Random Forest',
        'selected_before_test_evaluation':True},indent=2))
    return folds,summary,best

def evaluate_models(X_train,X_test,y_train,y_test,encoder,models):
    """Evaluate the frozen model specifications once; save complete fitted pipelines."""
    rows=[]; fitted={}; predictions=pd.DataFrame({'sample_id':X_test.index,'actual':encoder.inverse_transform(y_test)})
    for name,pipeline in models.items():
        print(f'Final training and test evaluation: {name}',flush=True)
        start=time.perf_counter()
        with threadpool_limits(limits=2):
            pipeline.fit(X_train,y_train)
        pred=pipeline.predict(X_test)
        precision,recall,f1,_=precision_recall_fscore_support(y_test,pred,average='macro',zero_division=0)
        rows.append({'model':name,'accuracy':accuracy_score(y_test,pred),'precision_macro':precision,
                     'recall_macro':recall,'f1_macro':f1,'fit_seconds':time.perf_counter()-start})
        slug=name.lower().replace(' ','_')
        cm=confusion_matrix(y_test,pred,labels=np.arange(len(encoder.classes_)))
        pd.DataFrame(cm,index=encoder.classes_,columns=encoder.classes_).to_csv(TABLES/f'confusion_{slug}.csv')
        report=classification_report(y_test,pred,target_names=encoder.classes_,output_dict=True,zero_division=0)
        (TABLES/f'classification_{slug}.json').write_text(json.dumps(report,indent=2))
        predictions[name]=encoder.inverse_transform(pred)
        fitted[name]=pipeline
        joblib.dump({'pipeline':pipeline,'label_encoder':encoder,'feature_names':list(X_train.columns),
                     'training_samples':len(X_train),'seed':SEED},ROOT/f'models/{slug}.joblib',compress=3)
        plt.figure(figsize=(6,5))
        sns.heatmap(cm,annot=True,fmt='d',cmap='Blues',xticklabels=encoder.classes_,yticklabels=encoder.classes_,cbar=False)
        plt.xlabel('Predicted class');plt.ylabel('Actual class');plt.title(f'{name}\nHeld-out test samples')
        save_figure(f'confusion_{slug}')
    predictions.to_csv(TABLES/'test_predictions.csv',index=False)
    metrics=pd.DataFrame(rows).set_index('model')
    metrics.to_csv(TABLES/'test_metrics.csv')
    baseline=DummyClassifier(strategy='most_frequent').fit(X_train,y_train).predict(X_test)
    (TABLES/'baseline.json').write_text(json.dumps({'accuracy':accuracy_score(y_test,baseline),
        'f1_macro':precision_recall_fscore_support(y_test,baseline,average='macro',zero_division=0)[2]},indent=2))
    return fitted,metrics

def make_visualizations(X_train,X_test,y_train,y_test,encoder,y,models,metrics,cv_summary,best):
    sns.set_theme(style='whitegrid',context='notebook',palette='colorblind')
    counts=y.value_counts().sort_index()
    ax=counts.plot.bar(figsize=(7,4),color=sns.color_palette('colorblind',5),rot=0)
    ax.bar_label(ax.containers[0]);plt.ylabel('Number of samples');plt.xlabel('Cancer class')
    plt.title('Cancer-class distribution | UCI 401');save_figure('class_distribution')
    # PCA is unsupervised and uses all nonconstant genes, not the ANOVA-selected genes.
    # Both standardization and PCA are learned on the training subset only.
    pca_pipe=Pipeline([('imputer',SimpleImputer(strategy='median',keep_empty_features=True)),
                       ('variance',VarianceThreshold()),('scale',StandardScaler()),
                       ('pca',PCA(n_components=2,svd_solver='randomized',random_state=SEED))])
    with threadpool_limits(limits=2):
        train_pc=pca_pipe.fit_transform(X_train)
        test_pc=pca_pipe.transform(X_test)
    ev=pca_pipe['pca'].explained_variance_ratio_
    fig,axes=plt.subplots(1,2,figsize=(12,4.7),sharex=True,sharey=True)
    for ax,pc,labels,title in [(axes[0],train_pc,y_train,'Training samples'),(axes[1],test_pc,y_test,'Held-out samples')]:
        sns.scatterplot(x=pc[:,0],y=pc[:,1],hue=encoder.inverse_transform(labels),hue_order=encoder.classes_,s=30,alpha=.8,ax=ax)
        ax.set(title=title,xlabel=f'PC1 ({ev[0]:.1%} variance)',ylabel=f'PC2 ({ev[1]:.1%} variance)')
    save_figure('pca_visualization')
    pd.DataFrame(np.vstack([train_pc,test_pc]),columns=['PC1','PC2']).assign(
        sample_id=list(X_train.index)+list(X_test.index),split=['train']*len(X_train)+['test']*len(X_test),
        cancer_class=encoder.inverse_transform(np.r_[y_train,y_test])).to_csv(TABLES/'pca_coordinates.csv',index=False)
    (TABLES/'pca_variance.json').write_text(json.dumps({'PC1':float(ev[0]),'PC2':float(ev[1])},indent=2))
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    metrics[['accuracy','precision_macro','recall_macro','f1_macro']].plot.bar(ax=axes[0],rot=15)
    axes[0].set(title='Held-out test performance',ylabel='Score',ylim=(0,1.08),xlabel='')
    axes[0].legend(['Accuracy','Macro precision','Macro recall','Macro F1'],fontsize=8,loc='lower left')
    cv_summary['cv_f1_macro_mean'].plot.bar(yerr=cv_summary['cv_f1_macro_std'],ax=axes[1],rot=15,capsize=4)
    axes[1].set(title='Training cross-validation: macro F1',ylabel='Mean +/- fold standard deviation',ylim=(0,1.08),xlabel='')
    save_figure('model_comparison')
    rf=models['Random Forest']
    surviving=np.asarray(X_train.columns)[rf['variance'].get_support()]
    selected=surviving[rf['select'].get_support()]
    importance=pd.DataFrame({'gene':selected,'importance':rf['classifier'].feature_importances_}).sort_values('importance',ascending=False)
    importance.to_csv(TABLES/'random_forest_gene_importance.csv',index=False)
    top=importance.head(20).iloc[::-1]
    plt.figure(figsize=(8,7));plt.barh(top.gene,top.importance,color='#157a8c')
    plt.xlabel('Mean decrease in impurity');plt.title('Top 20 selected genes | Random Forest\nPredictive importance is not biological causation')
    save_figure('top_genes')
    selection={name:{'after_variance':int(model['variance'].get_support().sum()),'after_anova':int(model['select'].get_support().sum())} for name,model in models.items()}
    (TABLES/'feature_counts.json').write_text(json.dumps(selection,indent=2))
    joblib.dump(pca_pipe,ROOT/'models/pca_visualization.joblib',compress=3)
    joblib.dump({'pipeline':models[best],'label_encoder':encoder,'feature_names':list(X_train.columns),
                 'model_name':best,'seed':SEED,'training_samples':len(X_train)},ROOT/'models/best_model.joblib',compress=3)

def run():
    X,y,audit=load_data()
    X_train,X_test,y_train,y_test,encoder=prepare_split(X,y)
    models=build_models()
    folds,summary,best=compare_cv(X_train,y_train,models)
    fitted,metrics=evaluate_models(X_train,X_test,y_train,y_test,encoder,models)
    make_visualizations(X_train,X_test,y_train,y_test,encoder,y,fitted,metrics,summary,best)
    environment={'python':platform.python_version(),'packages':{p:version(p) for p in
        ['numpy','pandas','scikit-learn','matplotlib','seaborn','ucimlrepo','joblib']},
        'seed':SEED,'test_size':.2,'cv_folds':5,'selected_genes':K_GENES,
        'train_samples':len(X_train),'test_samples':len(X_test)}
    (TABLES/'environment.json').write_text(json.dumps(environment,indent=2))
    print('\nSelected using training CV:',best,'\n',metrics)
    return {'audit':audit,'cv_summary':summary,'metrics':metrics,'best_model':best}

if __name__=='__main__':
    run()
