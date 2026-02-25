import slac_db.config
import slac_db.write
import difflib
import os
from pathlib import Path
import unittest

class TestCompareToLCLSTools(unittest.TestCase):
    def setUp(self):
        self.data_location = (
            Path(__file__).parent / "test_data"
        )

    def test_difflib(self):
        def get_files(p):
            return set([f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f))])
        def compare_files(test, original):
            with open(test, "r") as t, open(original, "r") as o:
                r = difflib.SequenceMatcher(None, t.readlines(), o.readlines()).ratio()
            if r != 1.0:
                with open(test, "r") as t, open(original, "r") as o:
                    print(test, end=' ')
                    print(r)
                    for line in difflib.ndiff(t.readlines(), o.readlines()):
                        print(line, end=' ')

        slac_db_yaml_loc = slac_db.config.yaml()
        lcls_tools_yaml_loc = (
            Path(__file__).parent / "test_data" / "lcls-tools-yaml"
        )
        slac_yamls = get_files(slac_db_yaml_loc)
        lcls_yamls = get_files(lcls_tools_yaml_loc)
        for s, l in zip(slac_yamls, lcls_yamls):
            compare_files(slac_db_yaml_loc / s, lcls_tools_yaml_loc / l)
        assert False
