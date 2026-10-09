"""Static staging landing UX smoke checks, independent of Render deployment."""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


LANDING = Path(__file__).resolve().parents[1] / "staging-index.html"


class LandingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.details_count = 0
        self.summary_count = 0
        self.main_count = 0
        self.nav_count = 0
        self.meta_viewport = False
        self.lang = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "a":
            self.links.append(a.get("href"))
        if tag == "details":
            self.details_count += 1
            if "open" in a:
                raise AssertionError("Operations explanation must start collapsed")
        if tag == "summary":
            self.summary_count += 1
        if tag == "main":
            self.main_count += 1
        if tag == "nav":
            self.nav_count += 1
        if tag == "meta" and a.get("name") == "viewport":
            self.meta_viewport = a.get("content") == "width=device-width, initial-scale=1.0"


class LandingTests(unittest.TestCase):
    def test_two_existing_public_entrypoints_remain_unchanged(self):
        page = LANDING.read_text(encoding="utf-8")
        parser = LandingParser()
        parser.feed(page)
        self.assertEqual(parser.links, ["/frontend/", "/gis/gis/"])
        self.assertEqual(parser.lang, "ja")
        self.assertEqual(parser.main_count, 1)
        self.assertEqual(parser.nav_count, 1)
        self.assertTrue(parser.meta_viewport)
        self.assertIn("地域の分析を見る", page)
        self.assertIn("地図で情報を探す", page)

    def test_staging_safety_and_technical_disclosure_remain_explicit(self):
        page = LANDING.read_text(encoding="utf-8")
        parser = LandingParser()
        parser.feed(page)
        self.assertEqual(parser.details_count, 1)
        self.assertEqual(parser.summary_count, 1)
        self.assertIn("実際の避難判断には利用しないでください", page)
        self.assertIn("同じ成果物として参照", page)
        self.assertNotIn("<script", page)
        self.assertNotIn("onerror=", page)

    def test_mobile_first_layout_and_keyboard_focus(self):
        page = LANDING.read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 640px)", page)
        self.assertRegex(page, r"\.entry-grid\s*\{\s*grid-template-columns:\s*minmax\(0,\s*1fr\)")
        self.assertIn("min-height: 100svh", page)
        self.assertIn(":focus-visible", page)
        self.assertIn("prefers-reduced-motion: reduce", page)
        self.assertIn("aria-label=\"HINANEXの画面を選択\"", page)


if __name__ == "__main__":
    unittest.main()
