import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bdreg.measure import cross_references, measure  # noqa: E402


def test_definitions_are_not_counted_as_obligations():
    m = measure('"licence" shall mean a licence. The Controller shall keep a register.')
    assert m.definitional == 1
    assert m.obligations == 1


def test_prohibitions_are_not_double_counted():
    m = measure("No person shall trade. A trader shall not sell. Goods must not be hidden.")
    assert m.prohibitions == 3
    assert m.obligations == 0


def test_permission_excludes_may_not_and_fine_may_extend():
    m = measure("The Board may exempt. A person may not appeal. Fine which may extend to Tk 100.")
    assert m.permissions == 1
    assert m.prohibitions == 1
    assert m.penalties == 1


def test_binding_per_1000_words():
    m = measure("You must pay. " * 10)  # 30 words, 10 obligations
    assert m.binding == 10
    assert round(m.binding_per_1000, 1) == 333.3


def test_bangla_lexicon():
    text = "নিবন্ধন ব্যতীত ব্যবসা করা যাইবে না। ব্যবসায়ী প্রতিবেদন দাখিল করিবে। সরকার ফি নির্ধারণ করিতে পারিবে।"
    m = measure(text, language="bn")
    assert (m.prohibitions, m.obligations, m.permissions) == (1, 1, 1)


def test_cross_references_roman_and_arabic():
    refs = cross_references("as in the Penal Code (Act No. XLV of 1860) and Ordinance No. 7 of 1975")
    assert refs == [("45", 1860), ("7", 1975)]
