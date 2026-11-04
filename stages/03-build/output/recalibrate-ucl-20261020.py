"""Isolated identity repair, causal training and held-out calibration review."""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
sys.stdout.reconfigure(encoding='utf-8')
from models.data import canonical_matches, normalize_matches, team_key
from models.features import FEATURE_NAMES, build_feature_frame, build_live_features
from models.validation import chronological_split, probability_metrics
from models import train_model_v2 as trainer

RAW = ROOT / 'pipeline/data/raw/ucl_history_20261020'
OUT = Path(__file__).resolve().parent
CANDIDATE = ROOT / 'pipeline/models/model_store/candidates/ucl_recalibrated_20261020'
GROUPS = {
    'Fenerbahce': ['Fenerbahçe SK', 'Fenerbahçe'],
    'Slavia Praha': ['SK Slavia Praha', 'Slavia Prague'],
    'Sabah FK': ['Sabah FC', 'Sabah Masazir'],
    'Dortmund': ['Borussia Dortmund', 'Borussia D'],
    'Roma': ['AS Roma'], 'Slovan Bratislava': ['ŠK Slovan Bratislava', 'Slovan B'],
    'Porto': ['FC Porto'], 'PSV': ['PSV Eindhoven'], 'Liverpool': ['Liverpool FC'],
    'Villarreal': ['Villarreal CF'], 'Man City': ['Manchester City', 'Manchester City FC'],
    'AEK': ['PAE AEK', 'AEK Athens', 'AEK Athens FC'],
    'Paris SG': ['Paris Saint-Germain FC', 'Paris Saint-Germain', 'PSG'],
    'Barcelona': ['FC Barcelona'], 'Napoli': ['SSC Napoli'],
    'Bodø/Glimt': ['FK Bodø/Glimt', 'Bodo/Glimt', 'Bodo Glimt', 'Bodo'],
    'Stuttgart': ['VfB Stuttgart'],
    'Ath Madrid': ['Club Atlético de Madrid', 'Atletico', 'Atletico Madrid', 'Atlético Madrid'],
}
ALIASES = {team_key(alias): canonical for canonical, variants in GROUPS.items() for alias in [canonical, *variants]}
# Reviewed against same-day overlapping source records and known senior clubs.
# Keep this candidate-scoped: frozen production/candidate feature keys are untouched.
OPPONENT_GROUPS = '''
Vallecano|Rayo Vallecano|Rayo Vallecano de Madrid
Real Madrid|Real|Real Madrid CF
Ath Bilbao|Athletic Bilbao|Athletic Club
Betis|Real Betis|Real Betis Balompié
Sociedad|Real Sociedad|Real Sociedad de Fútbol
Milan|AC Milan
Alaves|Deportivo Alaves|Deportivo Alavés
Espanol|Espanyol|RCD Espanyol de Barcelona
Como|Como 1907
Cadiz|Cádiz
Sp Braga|Braga|Sporting Clube de Braga
Guimaraes|Vitoria de Guimaraes|Vitória SC
Famalicao|Famalicão|FC Famalicão
Sp Lisbon|Sporting CP|Sporting Clube de Portugal
Leganes|Club Deportivo Leganes|CD Leganés
Bournemouth|AFC Bournemouth
Oviedo|Real Oviedo
Elche|Elche CF
Valencia|Valencia CF
Osasuna|CA Osasuna
Mallorca|RCD Mallorca
Celta|RC Celta de Vigo
Bologna|Bologna FC 1909
Union Berlin|1. FC Union Berlin
Getafe|Getafe CF
Inter|FC Internazionale Milano
Levante|Levante UD
Sunderland|Sunderland AFC
Hoffenheim|TSG 1899 Hoffenheim
Werder Bremen|SV Werder Bremen
Fiorentina|ACF Fiorentina
M'gladbach|Borussia Mönchengladbach
Genoa|Genoa CFC
Sassuolo|US Sassuolo Calcio
Ein Frankfurt|Eintracht Frankfurt
Hamburg|Hamburger SV
St Pauli|FC St. Pauli 1910
Pisa|AC Pisa 1909
Verona|Hellas Verona FC
FC Koln|1. FC Köln|Koln
Parma|Parma Calcio 1913
Udinese|Udinese Calcio
Atalanta|Atalanta BC
Leeds|Leeds United FC
Bayern Munich|FC Bayern München|Bayern
Cremonese|US Cremonese
Freiburg|SC Freiburg
Leverkusen|Bayer 04 Leverkusen
Lazio|SS Lazio
Lecce|US Lecce
St Etienne|Saint Etienne|AS Saint-Étienne
Cagliari|Cagliari Calcio
Wolfsburg|VfL Wolfsburg
Heidenheim|1. FC Heidenheim 1846
Mainz|1. FSV Mainz 05
Augsburg|FC Augsburg
Rennes|Stade Rennais FC 1901
Lille|Lille OSC
Alverca|FC Alverca
Brest|Stade Brestois 29
Twente|FC Twente '65
Malaga|Málaga CF
Monaco|AS Monaco FC
Paderborn|SC Paderborn 07
Santander|Racing|Real Racing Club de Santander
Ipswich|Ipswich Town FC
Ajax|AFC Ajax
Le Havre|Le Havre AC
Nantes|FC Nantes
Zwolle|PEC Zwolle
Lorient|FC Lorient
Santa Clara|CD Santa Clara
For Sittard|Fortuna Sittard
Arouca|FC Arouca
Groningen|FC Groningen
Coventry|Coventry City FC
La Coruna|Deportivo|RC Deportivo La Coruña
Benfica|Sport Lisboa e Benfica
Heerenveen|SC Heerenveen
Frosinone|Frosinone Calcio
Lyon|Olympique Lyonnais
Metz|FC Metz
Auxerre|AJ Auxerre
Angers|Angers SCO
Estrela|CF Estrela da Amadora
Lens|Racing Club de Lens
Excelsior|SBV Excelsior
Academico Viseu|Académico de Viseu|Académico de Viseu FC
Utrecht|FC Utrecht
Casa Pia|Casa Pia AC
Marseille|Olympique de Marseille
Maritimo|CS Marítimo
Strasbourg|RC Strasbourg Alsace
Den Haag|ADO Den Haag
Buyuksehyr|Basaksehir|Istanbul Basaksehir
Rizespor|Çaykur Rizespor
Kasimpasa|Kasımpaşa
Ad. Demirspor|Adana Demirspor
Karagumruk|Fatih Karagümrük
Istanbulspor|İstanbulspor
Goztep|Göztepe
Bodrumspor|Bodrum
Eyupspor|Eyüpspor
Genclerbirligi|Gençlerbirliği
Ham-Kam|HamKam
Sandefjord|Sandefjord Fotball
Valerenga|Vålerenga
Tromso|Tromsø
Sarpsborg|Sarpsborg 08
Lillestrom|Lillestrøm
Mainz|Mainz 05
Wolves|Wolverhampton
Leverkusen|Bayer 04
Werder Bremen|Werder
FC Koln|Cologne
Bochum|VfL Bochum
M'gladbach|Borussia Mg
Heidenheim|1. FC Heidenheim
For Sittard|Fortuna
Luton|Luton Town
AZ|AZ Alkmaar
St Pauli|St. Pauli
Holstein Kiel|Holstein
Hamburg|Hamburger
Ein Frankfurt|Frankfurt
KFUM|KFUM Oslo
Nott'm Forest|Nottingham F.
Feyenoord|Feyenoord Rotterdam
Galatasaray|Galatasaray SK
Shakhtar Donetsk|FK Shakhtar Donetsk|Shakhtar
RB Leipzig|Leipzig
Club Brugge|Club Brugge KV|Brugge
Union Saint-Gilloise|Union SG|Royale Union Saint-Gilloise
Copenhagen|FC København|FC Copenhagen|FC Kobenhavn
Salzburg|FC Red Bull Salzburg|FC Salzburg|RB Salzburg
Dinamo Zagreb|GNK Dinamo Zagreb
Sparta Prague|AC Sparta Praha|Sparta Praha
Kairat Almaty|FC Kairat Almaty
LASK Linz|LASK
'''
for group in OPPONENT_GROUPS.strip().splitlines():
    canonical, *variants = group.split('|')
    ALIASES.update({team_key(n): canonical for n in [canonical, *variants]})


def reviewed_name(name: str) -> str:
    return ALIASES.get(team_key(name), name)


def normalize_reviewed(frame: pd.DataFrame) -> pd.DataFrame:
    result = normalize_matches(frame)
    for side in ['home', 'away']:
        result[side + '_team'] = result[side + '_team'].map(reviewed_name)
    return normalize_matches(result)


def prepare() -> pd.DataFrame:
    base = normalize_reviewed(trainer.load_training_data())
    leagues = normalize_reviewed(pd.read_csv(RAW / 'league_results.csv', low_memory=False))
    archive = pd.read_csv(RAW / 'archives.csv')
    # League scores have no extra time. Cup/European archive scores remain captured
    # but are not silently assumed to be 90-minute outcomes.
    safe = {'ENG', 'EPL', 'ESP', 'GER', 'BNDL', 'ITA', 'FRA', 'POR', 'HOL', 'NED', 'TUR', 'CZE', 'GRE', 'AZER', 'NOR', 'SVK'}
    usable_archive = archive[archive.competition.isin(safe)].copy()
    usable_archive['score_basis'] = 'domestic_league_regulation'
    frames = [base, normalize_reviewed(usable_archive), leagues]
    if (RAW / 'official_results.csv').exists():
        frames.append(normalize_reviewed(pd.read_csv(RAW / 'official_results.csv')))
    if (RAW / 'europe_results.csv').exists():
        frames.append(normalize_reviewed(pd.read_csv(RAW / 'europe_results.csv')))
    joined = pd.concat(frames, ignore_index=True)
    keys = ['fixture_day', 'home_key', 'away_key']
    conflicts = joined.groupby(keys).result.nunique().gt(1)
    bad = set(conflicts[conflicts].index)
    mask = pd.Series([tuple(r) in bad for r in joined[keys].itertuples(index=False, name=None)], index=joined.index)
    joined.loc[mask].to_csv(RAW / 'result_conflicts_quarantined.csv', index=False)
    # Never silently choose a winner between disagreeing result sources.
    data = canonical_matches([joined.loc[~mask]])
    data = data[data.date.lt(pd.Timestamp('2026-10-20', tz='UTC')) & data.result.notna()].copy()
    duplicate_appearances = []
    for name in GROUPS:
        key = team_key(name)
        appearances = data[data.home_key.eq(key) | data.away_key.eq(key)]
        if appearances.fixture_day.duplicated().any():
            duplicate_appearances.append(appearances[appearances.fixture_day.duplicated(keep=False)])
    if duplicate_appearances:
        pd.concat(duplicate_appearances).drop_duplicates().to_csv(RAW/'unresolved_identity_duplicates.csv',index=False)
        raise ValueError('Multiple senior matches on one day; inspect unresolved_identity_duplicates.csv')
    data.to_parquet(RAW / 'repaired_dataset.parquet', index=False)
    coverage = []
    for name in GROUPS:
        key = team_key(name)
        rows = data[(data.home_key.eq(key) | data.away_key.eq(key)) & data.date.ge(pd.Timestamp('2023-07-01', tz='UTC'))]
        recent = rows.tail(5)
        form = ''.join('D' if r.result == 'draw' else 'W' if (r.home_key == key) == (r.result == 'home_win') else 'L' for r in recent.itertuples())
        coverage.append(dict(team=name, games=len(rows), first=rows.date.min(), last=rows.date.max(),
                             form=form, by_competition=rows.groupby('competition').size().to_dict(),
                             by_season=rows.groupby(rows.date.map(lambda d: f'{d.year if d.month >= 7 else d.year-1}')).size().to_dict()))
    report = dict(created_at=datetime.now(timezone.utc).isoformat(), fixtures=len(data),
                  aliases=ALIASES, source_conflict_fixtures=len(bad), conflict_rows=int(mask.sum()),
                  archive_rows=len(archive), safe_archive_rows=len(usable_archive),
                  excluded_archive_competitions=archive.loc[~archive.competition.isin(safe)].groupby('competition').size().to_dict(),
                  coverage=coverage, note='Captured archives are not proof of exhaustive all-competition history. Ambiguous regulation scores excluded.')
    (OUT / 'ucl-history-review-20261020.json').write_text(json.dumps(report, indent=2, default=str, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['aliases']}, default=str, ensure_ascii=False), flush=True)
    return data


def calibration_review(model, X: pd.DataFrame, y: np.ndarray, dates: pd.Series, splits: dict) -> dict:
    report = {}
    calibration = splits['calibration']
    days = pd.to_datetime(dates.iloc[calibration], utc=True).dt.normalize()
    distinct = np.sort(days.unique())
    boundary = distinct[int(len(distinct) * .7)]
    cal_fit = calibration[days.lt(boundary).to_numpy()]
    cal_select = calibration[days.ge(boundary).to_numpy()]
    assert dates.iloc[cal_fit].max() < dates.iloc[cal_select].min()
    for expert_name in ['market', 'history']:
        expert = getattr(model, expert_name + '_')
        base = expert.estimator.estimator
        fit, select, full = cal_fit, cal_select, calibration
        if expert_name == 'market':
            fit, select, full = [ix[X.iloc[ix].odds_missing.eq(0).to_numpy()] for ix in [fit, select, full]]
        if any(set(y[ix]) != {0, 1, 2} for ix in [fit, select, full]):
            raise ValueError('Insufficient class coverage for calibration review')
        choices = {'uncalibrated': base}
        for method in ['sigmoid', 'isotonic']:
            candidate = CalibratedClassifierCV(FrozenEstimator(base), method=method)
            candidate.fit(X.iloc[fit], y[fit])
            choices[method] = candidate
        scores = {label: probability_metrics(y[select], c.predict_proba(X.iloc[select]), ['away_win', 'draw', 'home_win']) for label,c in choices.items()}
        selected = min(scores, key=lambda label: scores[label]['log_loss'])
        final = base
        if selected != 'uncalibrated':
            final = CalibratedClassifierCV(FrozenEstimator(base), method=selected)
            final.fit(X.iloc[full], y[full])
        setattr(model, expert_name + '_', final)
        report[expert_name] = dict(selected=selected, selection_scores=scores, fit_samples=len(fit), selection_samples=len(select),
                                   calibration_fit_end=str(dates.iloc[fit].max()), selection_start=str(dates.iloc[select].min()))
    return report


def train(data: pd.DataFrame) -> None:
    if CANDIDATE.exists():
        raise ValueError('Candidate already exists; refusing overwrite')
    trainer.load_training_data = lambda: data
    metrics = trainer.train_model(output_dir=CANDIDATE, trees=120, threads=2)
    X, fixtures = build_feature_frame(data)
    splits = chronological_split(fixtures.date)
    classes = ['away_win', 'draw', 'home_win']
    y = np.array([classes.index(v) for v in fixtures.result])
    model = joblib.load(CANDIDATE / 'model_v2.1.0.pkl')
    test = splits['test']
    with threadpool_limits(limits=2):
        review = calibration_review(model, X, y, fixtures.date, splits)
        predictions = model.predict_proba(X.iloc[test])
    metrics['calibration_review'] = review
    metrics['fixed_sigmoid_test'] = metrics['test']
    metrics['test'] = probability_metrics(y[test], predictions, classes)
    metrics['status'] = 'reviewed_candidate_not_promoted'
    covered = X.iloc[test].odds_missing.eq(0).to_numpy()
    market = X.iloc[test][['fair_away_prob','fair_draw_prob','fair_home_prob']].to_numpy()[covered]
    metrics['market_comparison'] = {'model': probability_metrics(y[test][covered], predictions[covered], classes),
                                    'market': probability_metrics(y[test][covered], market, classes)}
    labels = y[test][covered]
    delta = -np.log(np.clip(predictions[covered][np.arange(len(labels)),labels], 1e-15, 1)) + np.log(np.clip(market[np.arange(len(labels)),labels],1e-15,1))
    day_losses = pd.DataFrame({'day':fixtures.iloc[test].date.dt.normalize().to_numpy()[covered], 'delta':delta}).groupby('day').delta.agg(['sum','count'])
    rng = np.random.default_rng(42)
    draws = rng.integers(0,len(day_losses),size=(1000,len(day_losses)))
    boot = day_losses['sum'].to_numpy()[draws].sum(axis=1) / day_losses['count'].to_numpy()[draws].sum(axis=1)
    metrics['model_minus_market_log_loss'] = dict(mean=float(delta.mean()), day_block_bootstrap_95=np.quantile(boot,[.025,.975]).tolist(), interpretation='Negative favors model; exploratory interval, no guarantee')
    metrics['test_boundary_probabilities'] = int(((predictions <= 0) | (predictions >= 1)).sum())
    metrics['identity_map'] = ALIASES
    joblib.dump(model, CANDIDATE / 'model_v2.1.0.pkl')
    metrics['model_sha256'] = hashlib.sha256((CANDIDATE / 'model_v2.1.0.pkl').read_bytes()).hexdigest()
    (CANDIDATE / 'metrics_v2.1.0.json').write_text(json.dumps(metrics,indent=2,default=str),encoding='utf-8')
    # Reload both artifacts and reproduce every held-out probability.
    loaded = joblib.load(CANDIDATE / 'model_v2.1.0.pkl')
    with threadpool_limits(limits=2):
        np.testing.assert_allclose(loaded.predict_proba(X.iloc[test]),predictions,rtol=1e-12,atol=1e-12)
    pd.DataFrame(predictions,columns=classes).assign(date=fixtures.iloc[test].date.to_numpy(),actual=fixtures.iloc[test].result.to_numpy()).to_csv(OUT/'ucl-calibration-holdout-20261020.csv',index=False)
    old = json.loads((OUT/'ucl-active-model-20261020.json').read_text(encoding='utf-8'))
    previews = []
    for row in old['matches']:
        if pd.Timestamp(row['date'],tz='UTC') < pd.Timestamp('2026-10-20T19:00:00Z'):
            continue
        item = dict(home=row['home_team'],away=row['away_team'])
        odds = row.get('input_mean_odds')
        live = build_live_features(data,reviewed_name(item['home']),reviewed_name(item['away']),pd.Timestamp('2026-10-20T19:00:00Z'),odds)
        with threadpool_limits(limits=2):
            p = loaded.predict_proba(live)[0]
        item.update(probabilities=dict(zip(classes,p.tolist())),odds_input=odds,
                    raw_active_probabilities=row.get('probabilities'),market_features_used=odds is not None,
                    features=live.iloc[0].to_dict())
        if odds is None:
            item['pricing_withheld'] = 'History-only expert; no stored complete prematch prices for EV'
        else:
            item.update(best_stored_prices=row['best_stored_prices'],gross_ev={c:float(p[i])*row['best_stored_prices'][c]-1 for i,c in enumerate(classes)})
        previews.append(item)
    summary = dict(candidate=str(CANDIDATE),generated_at=datetime.now(timezone.utc).isoformat(), test=metrics['test'],
                   fixed_sigmoid_test=metrics['fixed_sigmoid_test'],market_comparison=metrics['market_comparison'],
                   calibration_selection={k:v['selected'] for k,v in review.items()},
                   model_minus_market_log_loss=metrics['model_minus_market_log_loss'],
                   test_boundary_probabilities=metrics['test_boundary_probabilities'],previews=previews,
                   active_model_replaced=False,model_sha256=metrics['model_sha256'])
    (OUT/'ucl-recalibration-review-20261020.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'previews'},default=str),flush=True)
    print(json.dumps([{k:v for k,v in p.items() if k != 'features'} for p in previews],default=str),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--candidate-name',default='ucl_recalibrated_20261020')
    args = parser.parse_args()
    if not re.fullmatch(r'ucl_[a-z0-9_]+',args.candidate_name):
        parser.error('Candidate name must be a plain ucl_ identifier')
    CANDIDATE = CANDIDATE.with_name(args.candidate_name)
    prepared = prepare()
    if not args.prepare_only:
        train(prepared)
