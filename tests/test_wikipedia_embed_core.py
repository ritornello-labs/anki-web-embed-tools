from __future__ import annotations

import unittest

from wikipedia_embed_core import (
    ConversionSettings,
    build_embed_html,
    canonicalize_editor_embeds,
    convert_anchor_to_embed,
    convert_field_html,
    convert_matching_anchor_in_field,
    normalize_embed_url,
    is_wikipedia_url,
    normalize_wikipedia_url,
    resize_embed_html,
)


class NormalizeWikipediaUrlTest(unittest.TestCase):
    def test_normalizes_scheme_and_removes_fragment_and_query(self) -> None:
        self.assertEqual(
            normalize_wikipedia_url("http://en.wikipedia.org/wiki/Lazio?oldformat=true#History"),
            "https://en.wikipedia.org/wiki/Lazio",
        )

    def test_accepts_non_english_wikipedia_domains(self) -> None:
        self.assertEqual(
            normalize_wikipedia_url("https://it.wikipedia.org/wiki/Lazio"),
            "https://it.wikipedia.org/wiki/Lazio",
        )

    def test_rejects_non_wikipedia_hosts(self) -> None:
        self.assertIsNone(normalize_wikipedia_url("https://example.com/wiki/Lazio"))

    def test_rejects_non_article_namespaces(self) -> None:
        self.assertIsNone(normalize_wikipedia_url("https://en.wikipedia.org/wiki/File:Map_of_Italy.png"))
        self.assertIsNone(normalize_wikipedia_url("https://en.wikipedia.org/wiki/Special:Random"))

    def test_is_wikipedia_url_uses_same_rules(self) -> None:
        self.assertTrue(is_wikipedia_url("https://en.wikipedia.org/wiki/Lazio"))
        self.assertFalse(is_wikipedia_url("https://wikipedia.org/wiki/Lazio"))

    def test_normalize_embed_url_accepts_generic_http_urls(self) -> None:
        self.assertEqual(
            normalize_embed_url("https://example.com/embed?id=1"),
            "https://example.com/embed?id=1",
        )


class BuildEmbedHtmlTest(unittest.TestCase):
    def test_builds_canonical_embed_html(self) -> None:
        html = build_embed_html("https://en.wikipedia.org/wiki/Lazio")
        self.assertIn('class="wiki-embed"', html)
        self.assertIn('data-wiki-embed="1"', html)
        self.assertIn('data-wiki-lang="en"', html)
        self.assertIn('data-wiki-title="Lazio"', html)
        self.assertIn('data-url="https://en.wikipedia.org/wiki/Lazio"', html)
        self.assertIn('style="width: 100%; height: 480px;"', html)
        self.assertIn('<iframe src="https://en.wikipedia.org/wiki/Lazio"', html)

    def test_builds_dimensions_from_numeric_values(self) -> None:
        html = build_embed_html("https://en.wikipedia.org/wiki/Lazio", width=800, height=600)
        self.assertIn('style="width: 800px; height: 600px;"', html)

    def test_builds_generic_embed_html(self) -> None:
        html = build_embed_html("https://example.com/embed?id=1", width="75%", height="600px")
        self.assertIn('data-url="https://example.com/embed?id=1"', html)
        self.assertNotIn('data-wiki-lang=', html)
        self.assertNotIn('data-wiki-title=', html)

class ConvertAnchorToEmbedTest(unittest.TestCase):
    def test_converts_single_anchor_html(self) -> None:
        converted = convert_anchor_to_embed(
            '<a href="https://en.wikipedia.org/wiki/Lazio">Lazio</a>',
            settings=ConversionSettings(width="75%", height="520px"),
        )
        self.assertIn('data-wiki-embed="1"', converted)
        self.assertIn('style="width: 75%; height: 520px;"', converted)
        self.assertNotIn("<a ", converted)


class ConvertFieldHtmlTest(unittest.TestCase):
    def test_converts_all_eligible_wikipedia_links(self) -> None:
        result = convert_field_html(
            (
                '<div><a href="https://en.wikipedia.org/wiki/Lazio">Lazio</a></div>'
                '<p><a href="https://it.wikipedia.org/wiki/Sicilia">Sicilia</a></p>'
            )
        )

        self.assertTrue(result.changed)
        self.assertEqual(result.match_count, 2)
        self.assertEqual(result.converted_count, 2)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(result.html.count('data-wiki-embed="1"'), 2)
        self.assertNotIn("<a ", result.html)

    def test_preserves_non_wikipedia_links_and_surrounding_html(self) -> None:
        result = convert_field_html(
            '<div>Before <a href="https://example.com/wiki/Lazio">outside</a> after</div>'
        )

        self.assertFalse(result.changed)
        self.assertEqual(result.match_count, 0)
        self.assertIn('<a href="https://example.com/wiki/Lazio">outside</a>', result.html)
        self.assertIn("Before ", result.html)
        self.assertIn(" after", result.html)

    def test_does_not_reconvert_existing_embeds(self) -> None:
        result = convert_field_html(
            (
                '<div data-wiki-embed="1" style="width: 100%; height: 480px;">'
                '<iframe src="https://en.wikipedia.org/wiki/Lazio"></iframe>'
                "</div>"
                '<a href="https://en.wikipedia.org/wiki/Sicily">Sicily</a>'
            )
        )

        self.assertEqual(result.match_count, 1)
        self.assertEqual(result.converted_count, 1)
        self.assertEqual(result.html.count('data-wiki-embed="1"'), 2)

    def test_malformed_anchor_falls_back_without_conversion(self) -> None:
        result = convert_field_html('<a href="https://en.wikipedia.org/wiki/Lazio">Lazio')
        self.assertFalse(result.changed)
        self.assertEqual(result.match_count, 1)
        self.assertEqual(result.converted_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.html, '<a href="https://en.wikipedia.org/wiki/Lazio">Lazio')

    def test_converts_only_targeted_matching_link(self) -> None:
        result = convert_matching_anchor_in_field(
            (
                '<a href="https://en.wikipedia.org/wiki/Lazio">Lazio</a> '
                '<a href="https://en.wikipedia.org/wiki/Sicily">Sicily</a>'
            ),
            "https://en.wikipedia.org/wiki/Sicily",
        )
        self.assertTrue(result.changed)
        self.assertEqual(result.match_count, 2)
        self.assertEqual(result.converted_count, 1)
        self.assertEqual(result.skipped_count, 1)
        self.assertIn('<a href="https://en.wikipedia.org/wiki/Lazio">Lazio</a>', result.html)
        self.assertIn('data-url="https://en.wikipedia.org/wiki/Sicily"', result.html)

    def test_converts_only_first_matching_target_by_default(self) -> None:
        result = convert_matching_anchor_in_field(
            (
                '<a href="https://en.wikipedia.org/wiki/Lazio">Lazio 1</a> '
                '<a href="https://en.wikipedia.org/wiki/Lazio">Lazio 2</a>'
            ),
            "https://en.wikipedia.org/wiki/Lazio",
        )
        self.assertEqual(result.converted_count, 1)
        self.assertEqual(result.skipped_count, 1)
        self.assertIn("Lazio 2</a>", result.html)

    def test_converts_targeted_generic_link(self) -> None:
        result = convert_matching_anchor_in_field(
            (
                '<a href="https://example.com/embed?id=1">Example</a> '
                '<a href="https://en.wikipedia.org/wiki/Lazio">Lazio</a>'
            ),
            "https://example.com/embed?id=1",
        )
        self.assertTrue(result.changed)
        self.assertEqual(result.converted_count, 1)
        self.assertIn('data-url="https://example.com/embed?id=1"', result.html)
        self.assertIn('<a href="https://en.wikipedia.org/wiki/Lazio">Lazio</a>', result.html)


class ResizeEmbedHtmlTest(unittest.TestCase):
    def test_resizes_targeted_embed_by_index(self) -> None:
        html = (
            build_embed_html("https://en.wikipedia.org/wiki/Lazio")
            + build_embed_html("https://en.wikipedia.org/wiki/Sicily", width=640, height=360)
        )

        updated = resize_embed_html(html, embed_index=1, width="90%", height=700)

        self.assertIn('data-url="https://en.wikipedia.org/wiki/Lazio" style="width: 100%; height: 480px;"', updated)
        self.assertIn('data-url="https://en.wikipedia.org/wiki/Sicily" style="width: 90%; height: 700px;"', updated)

    def test_rejects_negative_embed_index(self) -> None:
        with self.assertRaises(ValueError):
            resize_embed_html(build_embed_html("https://en.wikipedia.org/wiki/Lazio"), -1, 500, 400)


class CanonicalizeEditorEmbedTest(unittest.TestCase):
    def test_converts_decorated_editor_embed_back_to_canonical_embed(self) -> None:
        editor_html = (
            '<div class="wiki-embed wiki-embed-editor-live" data-wiki-embed="1" '
            'data-wiki-lang="en" data-wiki-title="Lazio" '
            'data-url="https://en.wikipedia.org/wiki/Lazio" '
            'data-wiki-editor-selected="1" contenteditable="false" '
            'style="width: 88%; height: 610px; position: relative; box-shadow: 0 0 0 2px #4c9ffe;">'
            '<iframe src="https://en.wikipedia.org/wiki/Lazio" loading="lazy" '
            'referrerpolicy="no-referrer-when-downgrade" '
            'style="width: 100%; height: 100%; border: 0;"></iframe>'
            '<div class="wiki-embed-editor-ui"><button type="button">W+</button></div>'
            '</div>'
        )
        canonical = canonicalize_editor_embeds(editor_html)
        self.assertIn('data-wiki-embed="1"', canonical)
        self.assertNotIn('data-wiki-editor-selected="1"', canonical)
        self.assertNotIn('wiki-embed-editor-ui', canonical)
        self.assertIn('style="width: 88%; height: 610px;"', canonical)
        self.assertIn("<iframe ", canonical)

    def test_preserves_other_html_around_embed(self) -> None:
        editor_html = (
            '<div class="wiki-embed" data-wiki-embed="1" '
            'data-url="https://en.wikipedia.org/wiki/Lazio" '
            'style="width: 100%; height: 480px; position: relative;">'
            '<iframe src="https://en.wikipedia.org/wiki/Lazio"></iframe>'
            '<div class="wiki-embed-editor-ui">editor buttons</div>'
            '</div>'
        )
        canonical = canonicalize_editor_embeds(f"<div>before</div>{editor_html}<div>after</div>")
        self.assertIn("<div>before</div>", canonical)
        self.assertIn("<div>after</div>", canonical)


if __name__ == "__main__":
    unittest.main()
