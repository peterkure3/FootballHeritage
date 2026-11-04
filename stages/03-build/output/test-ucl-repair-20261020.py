import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

HERE=Path(__file__).resolve().parent


def load(name: str, file: str):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


repair=load('ucl_repair','recalibrate-ucl-20261020.py')
collector=load('ucl_collect','collect-ucl-history-20261020.py')
official=load('ucl_official','parse-ucl-official-20261020.py')


class RepairTests(unittest.TestCase):
    def test_aliases_merge_club_and_opponents(self):
        self.assertEqual(repair.reviewed_name('Paris Saint-Germain FC'),'Paris SG')
        self.assertEqual(repair.reviewed_name('Athletic Club'),'Ath Bilbao')
        self.assertEqual(repair.reviewed_name('Çaykur Rizespor'),'Rizespor')
        self.assertNotEqual(repair.reviewed_name('Sabah FA'),'Sabah FK')

    def test_duplicate_alias_fixture_becomes_one(self):
        rows=pd.DataFrame([
            dict(date='2026-10-17',home_team='SSC Napoli',away_team='AS Roma',home_score=2,away_score=1),
            dict(date='2026-10-17',home_team='Napoli',away_team='Roma',home_score=2,away_score=1)])
        combined=repair.canonical_matches([repair.normalize_reviewed(rows)])
        self.assertEqual(len(combined),1)

    def test_disagreeing_scores_are_rejected(self):
        rows=pd.DataFrame([
            dict(date='2026-10-17',home_team='Napoli',away_team='Roma',home_score=2,away_score=1),
            dict(date='2026-10-17',home_team='Napoli',away_team='Roma',home_score=1,away_score=2)])
        with self.assertRaisesRegex(ValueError,'conflicting'):
            repair.canonical_matches([repair.normalize_reviewed(rows)])

    def test_archive_excludes_today_future_and_extra_time(self):
        def row(date,score):
            return f'<tr><td class="date">{date}</td><td class="abr">CL</td><td class="leftteam">Napoli</td><td class="score">{score}</td><td class="rightteam">Roma</td></tr>'
        content=('<table>'+row('19.10.2026','2:1')+row('20.10.2026','1:0')+row('21.10.2026','3:0')+row('18.10.2026','2:1 aet')+'</table>').encode()
        rows,excluded=collector.parse_archive(content,'https://example.com')
        self.assertEqual(len(rows),1)
        self.assertEqual(len(excluded),1)
        self.assertEqual(rows[0]['home_score'],2)

    def test_official_slovan_seasons_and_orientation(self):
        rows=official.slovan_results((repair.RAW/'slovan_2025.html').read_bytes())
        self.assertEqual(len(rows),32)
        match=next(r for r in rows if r['date'].startswith('2025-07-26'))
        self.assertEqual(match['away_team'],'Slovan Bratislava')
        self.assertEqual((match['home_score'],match['away_score']),(2,2))
        self.assertTrue(all('league=NL-' in r['source_url'] for r in rows))

    def test_official_glimt_latest_match(self):
        rows=official.glimt_results((repair.RAW/'probe/glimt.txt').read_bytes())
        match=next(r for r in rows if r['date'].startswith('2026-10-17'))
        self.assertEqual(match['home_team'],'HamKam')
        self.assertEqual(match['away_team'],'Bodø/Glimt')
        self.assertEqual((match['home_score'],match['away_score']),(0,2))

    def test_calibration_choice_cannot_see_test_labels(self):
        rng=np.random.default_rng(7)
        X=pd.DataFrame(rng.normal(size=(180,len(repair.FEATURE_NAMES))),columns=repair.FEATURE_NAMES)
        X['odds_missing']=0
        y=np.tile(np.arange(3),60)
        dates=pd.Series(pd.date_range('2024-01-01',periods=180,tz='UTC'))
        base=LogisticRegression(max_iter=300).fit(X.iloc[:90],y[:90])
        def model():
            expert=lambda:SimpleNamespace(estimator=SimpleNamespace(estimator=base))
            return SimpleNamespace(market_=expert(),history_=expert())
        splits={'calibration':np.arange(90,150),'test':np.arange(150,180)}
        a=repair.calibration_review(model(),X,y,dates,splits)
        changed=y.copy()
        changed[150:]=(changed[150:]+1)%3
        b=repair.calibration_review(model(),X,changed,dates,splits)
        self.assertEqual(a,b)


if __name__=='__main__':
    unittest.main(verbosity=2)
