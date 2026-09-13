"""The migration only repairs an explicit offline copy and never guesses mixed data."""

import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

PATH = Path(__file__).parents[1] / 'tools/migrate_orientation_statistics.py'
SPEC = importlib.util.spec_from_file_location('angle_migration', PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
ID = 'sensor.test_orientation_pitch'


class StatisticsRepairTests(unittest.TestCase):
    def database(self, path):
        c = sqlite3.connect(path)
        c.execute('CREATE TABLE statistics_meta(id INTEGER PRIMARY KEY,statistic_id TEXT,unit_of_measurement TEXT,source TEXT)')
        c.execute('INSERT INTO statistics_meta VALUES (1,?,NULL,?)', (ID,'recorder'))
        for table in M.TABLES:
            c.execute(f'CREATE TABLE {table}(metadata_id INTEGER,start_ts REAL,mean REAL,min REAL,max REAL,state REAL,sum REAL)')
            c.execute(f'INSERT INTO {table} VALUES (1,0,100,-20,120,NULL,NULL)')
            c.execute(f'INSERT INTO {table} VALUES (1,7200,10,-2,12,NULL,NULL)')
        c.commit()
        return c

    def test_dry_run_and_copy_preserve_source_and_new_samples(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d)/'source.db', Path(d)/'repaired.db'
            c = self.database(src)
            plan = M.inspect(c,[ID],3600,7200)
            self.assertEqual(plan[0]['tables']['statistics'],{'raw':1,'degrees':1,'ambiguous':0})
            M.repair_copy(src,dst,[ID],3600,7200)
            self.assertEqual(c.execute('SELECT mean FROM statistics ORDER BY start_ts').fetchall(),[(100.0,),(10.0,)])
            self.assertIsNone(c.execute('SELECT unit_of_measurement FROM statistics_meta').fetchone()[0])
            with sqlite3.connect(dst) as repaired:
                self.assertEqual(repaired.execute('SELECT mean,min,max,state FROM statistics ORDER BY start_ts').fetchall(),[(10.0,-2.0,12.0,None),(10.0,-2.0,12.0,None)])
                self.assertEqual(repaired.execute('SELECT unit_of_measurement FROM statistics_meta').fetchone()[0],'°')
                with self.assertRaisesRegex(ValueError,'already migrated'):
                    M.inspect(repaired,[ID],3600,7200)
            with self.assertRaisesRegex(ValueError,'new, separate'):
                M.repair_copy(src,src,[ID],3600,7200)
            c.close()

    def test_mixed_bucket_refuses_copy_repair(self):
        with tempfile.TemporaryDirectory() as d:
            src,dst=Path(d)/'source.db',Path(d)/'copy.db'
            c=self.database(src)
            with self.assertRaisesRegex(ValueError,'Mixed/ambiguous'):
                M.repair_copy(src,dst,[ID],1800,7200)
            with sqlite3.connect(dst) as copy:
                self.assertEqual(copy.execute('SELECT mean FROM statistics ORDER BY start_ts').fetchone()[0],100)
                self.assertIsNone(copy.execute("SELECT name FROM sqlite_master WHERE name='gardena_angle_migration'").fetchone())
            c.close()

    def test_boundaries_and_metadata_are_validated(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.database(Path(d)/'test.db')
            for ids,raw,deg in (([],3600,7200),([ID,ID],3600,7200),([ID],7200,3600),(['missing'],3600,7200)):
                with self.assertRaises(ValueError):
                    M.inspect(c,ids,raw,deg)
            c.execute('UPDATE statistics_meta SET unit_of_measurement=?',('°',))
            self.assertEqual(M.inspect(c,[ID],3600,7200)[0]['tables']['statistics']['raw'],1)
            c.execute('UPDATE statistics_meta SET unit_of_measurement=?',('V',))
            with self.assertRaises(ValueError):
                M.inspect(c,[ID],3600,7200)
            with self.assertRaises(ValueError):
                M.timestamp('2026-09-12T20:00:00')
            self.assertEqual(M.timestamp('1970-01-01T00:00:00Z'),0)
            c.close()
