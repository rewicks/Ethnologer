import unittest

from ethnologer import Language, LanguageFamily, HtmlParser


class TestEthnologer(unittest.TestCase):
    def test_language(self):
        language = Language("eng", parent_family=None)
        self.assertEqual(language.name, "eng")
        self.assertEqual(language.speakers, 0)
        self.assertSetEqual(language.typological_features, set())
        self.assertEqual(language.parent_family, None)

    def test_language_families_connect_each_other(self):
        family1 = LanguageFamily("Germanic", parent_family=None)
        family2 = LanguageFamily("Western Germanic", parent_family=family1)
        self.assertEqual(family1.daughter_families[0], family2)


class TestHtmlParser(unittest.TestCase):
    TEXT = """<div class="field field-name-field-autonym field-type-text field-label-inline clearfix">
          <div class="field-label">Autonym</div>
        <div class="field-items">
              <div class="field-item even">Auye</div>
          </div>
    </div>
    <div class="field field-name-field-population field-type-text-with-summary field-label-inline clearfix">
          <div class="field-label">Population</div>
        <div class="field-items">
              <div class="field-item even"><p>350 (1995 SIL). Ethnic population: 500 (2012 SIL).</p>
    </div>
          </div>
    </div>
    <div class="field field-name-field-region field-type-text-with-summary field-label-inline clearfix">
          <div class="field-label">Location</div>
        <div class="field-items">
              <div class="field-item even"><p>Papua province: Paniai regency, Napan sub-district; central highlands in Siriwo river area.</p>
    </div>
          </div>
    </div>
    """

    def test_remove_tags(self):
        text = "<p class='important'>This is an important piece of text.</p>"
        clean_text = "This is an important piece of text."
        self.assertEqual(HtmlParser.remove_tags(text), clean_text)

    def test_get_content(self):
        text = self.TEXT
        self.assertIn(
            "Ethnic population: 500", HtmlParser.get_label(text, "Population")
        )

    def test_get_typological_info(self):
        result = HtmlParser.get_label(self.TEXT, "Typology")
        print(result)


if __name__ == "__main__":
    unittest.main()
