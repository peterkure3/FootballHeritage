"""Independently inspect saved model outputs and produce calibration evidence."""
import hashlib
import json
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
sys.stdout.reconfigure(encoding='utf-8')
OUT=Path(__file__).resolve().parent
from config import MODEL_DIR
from models.features import build_live_features
from models.validation import chronological_split,probability_metrics
from threadpoolctl import threadpool_limits

raw=json.loads((OUT/'ucl-active-model-20261020.json').read_text(encoding='utf-8'))
legacy=joblib.load(MODEL_DIR/'model_v2.0.0.pkl')
features=joblib.load(MODEL_DIR/'features_v2.0.0.pkl')
diagnostics=[]
for r in raw['matches']:
    if not r.get('probabilities') or not any(v==0 for v in r['probabilities'].values()):
        continue
    X=pd.DataFrame([r['features']],columns=features)
    pieces=[]
    reconstructed=[]
    for calibrated in legacy.calibrated_classifiers_:
        method='decision_function' if hasattr(calibrated.estimator,'decision_function') else 'predict_proba'
        p=getattr(calibrated.estimator,method)(X)[0]
        adjusted=np.array([c.predict([p[i]])[0] for i,c in enumerate(calibrated.calibrators)])
        reconstructed.append(adjusted/adjusted.sum())
        pieces.append([dict(class_index=i,response_method=method,base_response=float(p[i]),calibrated_value=float(c.predict([p[i]])[0]),
                            calibration_input_min=float(c.X_min_),calibration_input_max=float(c.X_max_)) for i,c in enumerate(calibrated.calibrators)])
    np.testing.assert_allclose(np.mean(reconstructed,axis=0),[r['probabilities'][c] for c in ['away_win','draw','home_win']],atol=1e-12)
    diagnostics.append(dict(home=r['home_team'],away=r['away_team'],raw=r['probabilities'],calibrators=pieces))
(OUT/'ucl-legacy-calibration-diagnostic-20261020.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
print(json.dumps({'legacy_zero_diagnostics':diagnostics}),flush=True)

review_path=OUT/'ucl-recalibration-review-20261020.json'
if review_path.exists():
    review=json.loads(review_path.read_text(encoding='utf-8'))
    directory=Path(review['candidate'])
    metrics=json.loads((directory/'metrics_v2.1.0.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((directory/'model_v2.1.0.pkl').read_bytes()).hexdigest()==metrics['model_sha256']
    assert hashlib.sha256((directory/'dataset.parquet').read_bytes()).hexdigest()==metrics['dataset_sha256']
    pred=pd.read_csv(OUT/'ucl-calibration-holdout-20261020.csv')
    classes=['away_win','draw','home_win']
    p=pred[classes].to_numpy()
    measured=probability_metrics(np.array([classes.index(x) for x in pred.actual]),p,classes)
    assert abs(measured['log_loss']-review['test']['log_loss'])<1e-12
    for name,expert in metrics['calibration_review'].items():
        assert pd.Timestamp(expert['calibration_fit_end'])<pd.Timestamp(expert['selection_start'])
    assert pd.Timestamp(metrics['data_report']['splits']['calibration']['end'])<pd.Timestamp(metrics['data_report']['splits']['test']['start'])
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,3,figsize=(12,4),constrained_layout=True)
        for axis,name in zip(axes,classes):
            axis.plot([0,1],[0,1],color='gray',linestyle='--',linewidth=1)
            for label,color in [('model','#126b5d'),('market','#b85c32')]:
                bins=review['market_comparison'][label]['calibration_bins'][name]
                axis.plot([b['mean_probability'] for b in bins],[b['observed_frequency'] for b in bins],marker='o',label=label,color=color)
            axis.set(title=name.replace('_',' ').title(),xlabel='Mean predicted probability',ylabel='Observed frequency',xlim=(0,1),ylim=(0,1))
            axis.legend()
        fig.suptitle('Held-out reliability: model and market on the same fixtures')
        fig.savefig(OUT/'ucl-calibration-reliability-20261020.png',dpi=170)
        plt.close(fig)
    except ImportError:
        print('Matplotlib unavailable; numerical reliability bins retained')
    print(json.dumps({'verified_candidate':str(directory),'test_samples':len(pred),'reproduced_log_loss':measured['log_loss'],'checks':'artifact checksums, metric reproduction, chronological separation passed'}),flush=True)
