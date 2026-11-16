"""Generate an academic Markdown report and typeset PDF from actual saved outputs."""
import json
from html import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from load_data import ROOT

def build_report():
    tables=ROOT/'reports/tables'
    read=lambda name: json.loads((tables/f'{name}.json').read_text())
    audit=read('data_audit');env=read('environment');pca=read('pca_variance')
    best=read('selection')['best_model'];baseline=read('baseline')
    counts=read('feature_counts')[best]
    metrics=pd.read_csv(tables/'test_metrics.csv',index_col=0)
    cv=pd.read_csv(tables/'cv_summary.csv',index_col=0)
    pred=pd.read_csv(tables/'test_predictions.csv')
    correct=int((pred.actual==pred[best]).sum());n=len(pred)
    # Wilson interval estimates binomial accuracy uncertainty under IID sampling.
    z=1.96;p=correct/n;denom=1+z*z/n
    mid=(p+z*z/(2*n))/denom;half=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/denom
    top=pd.read_csv(tables/'random_forest_gene_importance.csv').head(5)
    b=metrics.loc[best];c=cv.loc[best]
    provenance=json.loads((ROOT/'data/raw/provenance.json').read_text())
    title='Machine Learning-Based Cancer Classification Using Gene Expression Data'
    sections=[]
    def add(heading,text): sections.append((heading,text))
    add('Abstract',f'This project evaluated supervised classification of five cancer types using UCI dataset 401. The observed matrix contained {audit["samples"]} samples and {audit["features"]:,} expression features. A stratified split reserved {n} samples for testing and {env["train_samples"]} for training. Constant-gene removal and training-only ANOVA selection retained 500 genes. Logistic Regression, a radial-basis-function Support Vector Machine and Random Forest were compared using five-fold training cross-validation. {best} was selected by mean macro F1 ({c.cv_f1_macro_mean:.4f}, fold SD {c.cv_f1_macro_std:.4f}). Its held-out accuracy was {b.accuracy:.4f} and macro F1 was {b.f1_macro:.4f}. These are internal benchmark results, not evidence of clinical diagnostic utility. Anonymized gene identifiers prevent verified gene-level biological interpretation.')
    add('Introduction','Gene-expression measurements summarize transcript abundance across many genes. Computational analysis can compare these high-dimensional profiles and learn associations with known tumour classes. TCGA pan-cancer research provides a context for studying molecular similarities and differences across tumour types (The Cancer Genome Atlas Research Network, 2013). This project uses an educational expression benchmark to connect biological data handling with reproducible machine learning. It classifies existing tumour samples among five supplied labels; it does not detect cancer in healthy people.')
    add('Problem statement','There are many more measured genes than samples, so a model can fit incidental patterns and produce optimistic results if gene selection uses evaluation labels. The central problem is to compare three classifiers under a leakage-controlled protocol and assess how well they distinguish the supplied classes on held-out samples. The question is predictive discrimination within this dataset, rather than causal gene discovery or clinical diagnosis.')
    add('Aim and objectives','The aim is to analyse gene-expression data computationally and classify cancer types. Objectives are to validate dimensions and labels; audit missingness, duplicates and class imbalance; construct reproducible stratified splits; fit variance filtering, ANOVA selection and appropriate scaling within training folds; compare three algorithms with accuracy and macro precision, recall and F1; visualize class composition, PCA structure, performance and gene importance; preserve models and outputs; and critically interpret biological and computational limitations.')
    add('Literature background','The TCGA Pan-Cancer analysis project established a framework for comparing molecular measurements across cancer types (The Cancer Genome Atlas Research Network, 2013). This motivates expression-based classification but does not establish clinical performance for the present subset. Ambroise and McLachlan (2002) showed that gene selection outside cross-validation can bias error estimates in gene-expression classification. Accordingly, every learned transformation here belongs inside the training pipeline. Scikit-learn documents pipeline-based protection against preprocessing leakage (Scikit-learn developers, n.d.-a). Random Forest impurity importance quantifies contributions to fitted tree splits, and can be misleading with correlated or high-cardinality variables (Scikit-learn developers, n.d.-b). It is therefore used descriptively, not as a test of biological significance.')
    add('Dataset description',f'UCI dataset 401, contributed by Samuele Fiorini, is a subset of RNA-Seq HiSeq PANCAN expression data (Fiorini, 2016). Its five labels are BRCA (breast invasive carcinoma), KIRC (kidney renal clear cell carcinoma), COAD (colon adenocarcinoma), LUAD (lung adenocarcinoma) and PRAD (prostate adenocarcinoma). Rows represent samples; columns are anonymized gene measurements. Observed class counts were '+', '.join(f'{k}: {v}' for k,v in audit['class_counts'].items())+f'. The largest-to-smallest class ratio was {audit["majority_minority_ratio"]:.2f}. The data were retrieved using {provenance["method"]}. The requested API was attempted first; any failure is recorded in data/raw/provenance.json. No replacement or simulated data were used. The release is licensed CC BY 4.0 (Fiorini, 2016). Expression values were used as supplied; the available metadata did not establish a sufficiently detailed normalization recipe to justify claiming raw counts or adding another logarithmic transformation.')
    add('Methodology',f'Random seed 42 was fixed throughout. A stratified 80:20 split produced {env["train_samples"]} training and {n} test samples. Sample membership was saved. LabelEncoder was fitted on training labels; its integer mapping is only a coding scheme, not a biological ordering. The audit found {audit["missing_feature_values"]} missing feature values, {audit["missing_target_values"]} missing labels and {audit["duplicate_feature_rows_extra"]} extra duplicate expression rows. A median imputer is included inside each pipeline as a defensive step, but it changes no observed values when none are missing. Duplicate rows cause the loader to stop for investigation instead of silently splitting duplicate samples across sets. The cleaned export preserves supplied expression values and labels, without globally fitted scaling or selection.')
    add('Feature processing and model specifications',f'VarianceThreshold(0) removed genes constant in the relevant training partition; on the complete training subset {counts["after_variance"]:,} genes remained. SelectKBest with the ANOVA F statistic retained 500 genes, a prespecified computational choice rather than a claimed optimal count. ANOVA ranks individual associations and can miss interactions or retain correlated genes; its rankings are not multiple-testing-corrected biological discoveries. StandardScaler was fitted after selection for Logistic Regression and SVM. Random Forest used unscaled selected values. Logistic Regression used L2 regularization, C=1 and max_iter=5000; SVM used an RBF kernel, C=1 and gamma=scale; Random Forest used 300 trees, sqrt feature sampling and otherwise library defaults. No hyperparameter search was performed. Five stratified shuffled folds of the training set were used, and every fold refitted imputation, variance filtering, ANOVA selection, scaling and the classifier. The selected model maximized mean macro F1; exact ties favor Logistic Regression, then SVM, then Random Forest. The selection was recorded before test evaluation. All three frozen specifications were then evaluated once on the same test set, without changing the selection based on test results.')
    add('Metrics and visualization protocol','Accuracy is the proportion of correct predictions. Per-class precision is TP/(TP+FP), recall is TP/(TP+FN), and F1 is their harmonic mean. Macro scores average the five class scores equally, making minority classes visible despite imbalance. Confusion matrices use actual classes as rows and predicted classes as columns. A majority-class dummy classifier provides context. Cross-validation standard deviations describe fold variation, not confidence intervals. PCA used median imputation, constant-gene removal and scaling on training data, followed by a two-component randomized PCA with seed 42; held-out samples were only transformed. PCA used all nonconstant genes, separately from supervised ANOVA, and was not used as classifier input. Forest importance is mean decrease in impurity within the 500 selected features.')
    add('Results',f'The selected model, {best}, correctly classified {correct} of {n} held-out samples. Its accuracy was {b.accuracy:.4f}, macro precision {b.precision_macro:.4f}, macro recall {b.recall_macro:.4f}, and macro F1 {b.f1_macro:.4f}. A nominal 95% Wilson interval for its test accuracy was [{mid-half:.4f}, {mid+half:.4f}], conditional on independent, identically distributed test observations; it does not cover domain shift or all model-selection uncertainty. The majority-class baseline achieved accuracy {baseline["accuracy"]:.4f} and macro F1 {baseline["f1_macro"]:.4f}. PCA components explained {pca["PC1"]:.2%} and {pca["PC2"]:.2%} of training variance, totaling {sum(pca.values()):.2%}; the two-dimensional projection therefore omits much of the variation. Full model comparisons and per-class outcomes follow. Random Forest ranked '+', '.join(top.gene)+ ' highest by training impurity importance. These are anonymous identifiers, not verified gene symbols.')
    explanation={'Logistic Regression':'Its linear, regularized decision rule may match much of the discriminative structure in the ANOVA-selected features while limiting coefficient magnitude.',
                 'Support Vector Machine':'Its RBF similarity function can accommodate nonlinear relationships among standardized selected features.',
                 'Random Forest':'Its ensemble of trees can represent nonlinear thresholds and interactions among selected features.'}[best]
    add('Discussion',f'{best} was chosen because it had the highest training cross-validation mean macro F1 under the prespecified rule. {explanation} This is a plausible computational explanation, not a demonstrated cause of superiority: no ablation, repeated nested cross-validation or formal paired comparison was performed. Small score differences do not establish that one algorithm is generally better. Strong separation, if observed, indicates that the supplied profiles contain information associated with the class labels in this sample collection. It may reflect tissue identity as well as tumour biology; this study cannot disentangle these effects. PCA plots describe variance structure, not diagnostic validity. The anonymous forest-ranked features may be useful predictors within this pipeline, but importance does not prove a causal role, differential expression or therapeutic relevance. Computationally, reducing the feature space from 20,531 measurements to 500 reduces the number of classifier inputs and helps control an otherwise severe features-to-samples imbalance; the project does not experimentally prove that 500 is optimal.')
    add('Limitations','The dataset uses anonymized gene names, so no pathway enrichment, gene-function attribution or biomarker claim is justified without a verified identifier mapping. High machine-learning accuracy does not equal clinical usefulness. The sample size is small relative to gene count, making feature selection or other strong regularization necessary for a manageable, defensible analysis. A single random held-out split and five-fold internal validation do not establish transportability. Selecting among algorithms on cross-validation can make the selected CV result optimistic; the held-out test provides a separate internal check, not external validation. Fold variability is not a significance test. Patient, batch, centre, demographic, treatment and stage metadata were not available in the supplied feature/label tables for grouping or confounder adjustment; distinct expression rows do not prove independent patients. Tissue-of-origin and technical effects may contribute to predictions. The 500-gene choice and model defaults were not tuned or tested for stability. Impurity importance is training-derived and affected by correlation and split opportunities. No healthy controls, prospective validation, calibration, decision thresholds, clinical costs or outcome benefit were studied. Unknown classes cannot be recognized reliably by this closed-set classifier. Results must not be interpreted as medical diagnosis.')
    add('Conclusion',f'A reproducible workflow was completed for five-class cancer classification using the observed UCI expression data. Training-only preprocessing, stratified evaluation and saved sample membership make the comparison auditable. {best} was selected by cross-validation and achieved held-out accuracy {b.accuracy:.4f} with macro F1 {b.f1_macro:.4f}. The work demonstrates an academic application of machine learning to genomic measurements. Further work should validate on independent, well-annotated cohorts, evaluate grouped splits and feature stability, and obtain verified gene identifiers before drawing biological conclusions.')
    add('Reproducibility and saved artifacts','Run python src/load_data.py, then python src/analysis.py, then python src/build_report.py from the project root, or execute the annotated notebook. The raw snapshot and provenance, cleaned CSV, split membership, per-gene statistics, CV fold scores, test predictions, class-level reports, figures and fitted pipelines are saved locally. The selected model remains fitted only on the original training subset so that its saved state matches the reported test evaluation. Saved bundles include the label encoder and ordered feature names. Loading joblib files executes trusted Python serialization; use only the project artifacts you trust. Environment versions and configuration are recorded in reports/tables/environment.json and requirements-lock.txt. The attached course outline was treated as contextual material; this report follows the explicit project request.')
    refs=[
      'Ambroise, C., & McLachlan, G. J. (2002). Selection bias in gene extraction on the basis of microarray gene-expression data. Proceedings of the National Academy of Sciences, 99(10), 6562-6566. https://doi.org/10.1073/pnas.102102699',
      'Fiorini, S. (2016). Gene expression cancer RNA-Seq [Data set]. UCI Machine Learning Repository. https://doi.org/10.24432/C5R88H',
      'Scikit-learn developers. (n.d.-a). Common pitfalls and recommended practices. Scikit-learn. Retrieved September 23, 2026, from https://scikit-learn.org/stable/common_pitfalls.html',
      'Scikit-learn developers. (n.d.-b). Feature importances with a forest of trees. Scikit-learn. Retrieved September 23, 2026, from https://scikit-learn.org/stable/auto_examples/ensemble/plot_forest_importances.html',
      'The Cancer Genome Atlas Research Network. (2013). The Cancer Genome Atlas Pan-Cancer analysis project. Nature Genetics, 45, 1113-1120. https://doi.org/10.1038/ng.2764']
    add('References','\n\n'.join(refs))
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle',parent=styles['Title'],fontSize=24,leading=30,textColor=colors.HexColor('#153b50'),spaceAfter=22))
    styles.add(ParagraphStyle(name='FigureCaption',parent=styles['BodyText'],fontSize=8.5,leading=11,
                              textColor=colors.HexColor('#536874'),spaceBefore=4,spaceAfter=10,
                              alignment=TA_CENTER))
    styles['BodyText'].leading=14;styles['BodyText'].spaceAfter=9;styles['BodyText'].fontSize=10
    styles['Heading1'].textColor=colors.HexColor('#157a8c');styles['Heading1'].spaceBefore=15
    story=[Paragraph(title,styles['ReportTitle']),Paragraph('ACADEMIC BIOINFORMATICS PROJECT',styles['Heading2']),
           Paragraph('UCI dataset 401 | Reproducible Python analysis | 23 September 2026',styles['BodyText']),Spacer(1,16)]
    md=['# '+title,'Academic bioinformatics project | 23 September 2026']
    def table(frame,label):
        data=[list(frame.columns)]+[[str(v) for v in row] for row in frame.itertuples(index=False,name=None)]
        md.append('### '+label)
        md.append('| '+' | '.join(data[0])+' |\n|'+'|'.join(['---']*len(data[0]))+'|\n'+'\n'.join('| '+' | '.join(r)+' |' for r in data[1:]))
        story.append(Paragraph(label,styles['Heading2']))
        cells=[[Paragraph(escape(v),styles['BodyText']) for v in row] for row in data]
        t=Table(cells,repeatRows=1,colWidths=[6.9*inch/len(data[0])]*len(data[0]),hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e3eef2')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#157a8c')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f7f9')]),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6)]))
        story.extend([t,Spacer(1,10)])
    def figure(name,caption,width=6.8):
        from PIL import Image as PILImage
        path=ROOT/f'reports/figures/{name}.png'
        with PILImage.open(path) as im:w,h=im.size
        scale=min(width*inch/w,4.7*inch/h)
        story.extend([Image(str(path),width=w*scale,height=h*scale),Paragraph(caption,styles['FigureCaption']),Spacer(1,12)])
        md.append(f'![{caption}](figures/{name}.png)')
    for heading,body in sections:
        md.extend(['## '+heading,body]);story.append(Paragraph(heading,styles['Heading1']))
        for paragraph in body.split('\n\n'):story.append(Paragraph(escape(paragraph),styles['BodyText']))
        if heading=='Dataset description':figure('class_distribution','Figure 1. Observed sample counts by cancer class.')
        if heading=='Results':
            display=metrics[['accuracy','precision_macro','recall_macro','f1_macro']].map(lambda x:f'{x:.4f}').reset_index()
            display.columns=['Model','Accuracy','Precision (macro)','Recall (macro)','F1 (macro)'];table(display,'Table 1. Held-out test performance')
            d=cv[['cv_accuracy_mean','cv_precision_macro_mean','cv_recall_macro_mean','cv_f1_macro_mean','cv_f1_macro_std']].map(lambda x:f'{x:.4f}').reset_index()
            d.columns=['Model','CV accuracy','CV precision','CV recall','CV F1','F1 fold SD'];table(d,'Table 2. Training-only five-fold cross-validation')
            cr=read('classification_'+best.lower().replace(' ','_'))
            d=pd.DataFrame({k:cr[k] for k in audit['class_counts']}).T[['precision','recall','f1-score','support']]
            d['support']=d.support.astype(int).astype(str)
            for col in ['precision','recall','f1-score']:d[col]=d[col].map(lambda x:f'{x:.4f}')
            d=d.reset_index();d.columns=['Class','Precision','Recall','F1','Support'];table(d,'Table 3. Selected model: per-class test results')
            figure('model_comparison','Figure 2. Test scores and training CV macro F1; error bars show fold SD.')
            figure('pca_visualization','Figure 3. Training-fitted PCA, with the held-out set projected without refitting.')
            figure('confusion_'+best.lower().replace(' ','_'),'Figure 4. Selected model confusion matrix on the held-out test set.',5.3)
            figure('top_genes','Figure 5. Random Forest training impurity importance; anonymous feature identifiers.',5.5)
    (ROOT/'reports/academic_report.md').write_text('\n\n'.join(md),encoding='utf-8')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#536874'))
        canvas.drawString(43,28,'UCI 401 | Cancer classification | Academic research only')
        canvas.drawRightString(552,28,str(doc.page))
    path=ROOT/'output/pdf/academic_report.pdf'
    SimpleDocTemplate(str(path),pagesize=(595.28,841.89),leftMargin=43,rightMargin=43,topMargin=43,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
    print('Report generated:',path)

if __name__=='__main__':build_report()
