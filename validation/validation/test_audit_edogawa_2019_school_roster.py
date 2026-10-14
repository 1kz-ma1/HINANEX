"""Synthetic C tests: independently inspect source row positions and counts."""
from pathlib import Path
import unittest

from audit_edogawa_2019_school_roster import (
    AuditError, PAGE, GROUPS, DETAILS, EXPECTED_SHA,
    source_observations, audited_number, audit, center_y,
)


def word(x,y,s):
    return (x,y-5.5,x+9,y+5.5,s,0,0,0)


def synthetic_columns():
    values=[]
    for n in range(1,43):
        y=111.84+(n-1)*13.32
        values += [word(50.3 if n<10 else 47.5,y,str(n)),
                   word(62.2,y,f"架空小学校{n}"),word(176.4,y,"3"),
                   word(213.5,y,"2"),word(234,y,"2"),word(254.5,y,"100%")]
    for n in range(1,22):
        if n==2:
            values.append(word(305,131.42,"2"))
            for y,label in [(125.16,"架空中学校２"),(138.48,"架空中学校２【夜間】")]:
                values += [word(316.3,y,label),word(431,y,"1"),word(468,y,"1"),
                           word(494,y,"2"),word(509,y,"50%")]
            continue
        y=111.84 if n==1 else 151.8+(n-3)*13.32
        values += [word(305 if n<10 else 302,y,str(n)),
                   word(316.3,y,f"架空中学校{n}"),
                   word(431,y,"1"),word(468,y,"1"),
                   word(494,y,"2"),word(509,y,"50%")]
    for n in range(1,3):
        y=458.1+(n-1)*13.32
        values += [word(305,y,str(n)),word(316.3,y,f"旧架空学校{n}"),
                   word(431,y,"1"),word(468,y,"1"),word(494,y,"2"),word(509,y,"50%")]
    return values


class IndependentRostersTests(unittest.TestCase):
    def test_categories_and_numbered_detail_counts(self):
        result=source_observations(synthetic_columns())
        self.assertEqual({k:len(v["names"]) for k,v in result.items()},DETAILS)
        self.assertEqual({k:len(v["markers"]) for k,v in result.items()},GROUPS)
        self.assertEqual([x[1] for x in result["junior_high"]["markers"]],list(range(1,22)))

    def test_c_cell_selection_is_independent_of_a_parser(self):
        words=synthetic_columns()
        self.assertEqual(audited_number(words,"elementary","evac",111.84),3)
        self.assertEqual(audited_number(words,"junior_high","evac",125.16),1)
        self.assertEqual(audited_number(words,"junior_high","percent",138.48),50)

    def test_missing_source_row_blocks(self):
        words=[w for w in synthetic_columns() if not
               (abs(center_y(w)-138.48)<0.5 and w[0]>=290)]
        with self.assertRaisesRegex(AuditError,"named row count"):
            source_observations(words)

    def test_duplicate_source_names_blocks(self):
        words=synthetic_columns()
        words.append(word(316.3,125.16,"架空中学校２"))
        with self.assertRaisesRegex(AuditError,"named row count"):
            source_observations(words)

    def test_ambiguous_number_cell_blocks(self):
        words=synthetic_columns()
        words.append(word(431,111.84,"99"))
        with self.assertRaisesRegex(AuditError,"ambiguous"):
            audited_number(words,"junior_high","evac",111.84)

    def test_no_implicit_2019_real_source_from_synthetic_pdf(self):
        with self.assertRaisesRegex(AuditError,"original bytes changed"):
            audit(b"%PDF-synthetic",b'{"asof_input_approved":false}')
        self.assertEqual(len(EXPECTED_SHA),64)
        self.assertEqual(PAGE,2)


if __name__=="__main__":
    unittest.main()
