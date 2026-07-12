from __future__ import annotations

import html
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable, cast
from urllib.parse import unquote, urlparse, urlunparse


WIKIPEDIA_ARTICLE_PREFIX = "/wiki/"
DISALLOWED_NAMESPACES = {
    "book",
    "category",
    "draft",
    "file",
    "help",
    "media",
    "mediawiki",
    "module",
    "portal",
    "special",
    "talk",
    "template",
    "topic",
    "user",
    "wikipedia",
}
@dataclass(frozen=True)
class ConversionSettings:
    width: str | int = "100%"
    height: str | int = "480px"


@dataclass(frozen=True)
class ConversionResult:
    html: str
    changed: bool
    match_count: int
    converted_count: int
    skipped_count: int


def is_wikipedia_url(url: str) -> bool:
    return normalize_wikipedia_url(url) is not None


def normalize_embed_url(url: str) -> str | None:
    normalized_wikipedia = normalize_wikipedia_url(url)
    if normalized_wikipedia is not None:
        return normalized_wikipedia

    candidate = url.strip()
    if not candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None
    return urlunparse(parsed)


def normalize_wikipedia_url(url: str) -> str | None:
    candidate = url.strip()
    if not candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None

    hostname = (parsed.hostname or "").lower()
    if not _is_wikipedia_hostname(hostname):
        return None

    path = parsed.path or ""
    if not path.startswith(WIKIPEDIA_ARTICLE_PREFIX):
        return None

    article = path[len(WIKIPEDIA_ARTICLE_PREFIX) :]
    if not article:
        return None

    decoded_article = unquote(article)
    if _is_disallowed_namespace(decoded_article):
        return None

    normalized_path = f"{WIKIPEDIA_ARTICLE_PREFIX}{article}"
    return urlunparse(("https", hostname, normalized_path, "", "", ""))


def build_embed_html(url: str, width: str | int = "100%", height: str | int = "480px") -> str:
    normalized = normalize_embed_url(url)
    if normalized is None:
        raise ValueError(f"Not a supported embeddable URL: {url}")

    parsed = urlparse(normalized)
    wrapper_style = _render_style("", width=_normalize_dimension(width), height=_normalize_dimension(height))
    attrs = [
        ('class', 'wiki-embed'),
        ('data-wiki-embed', '1'),
        ('data-url', normalized),
        ('style', wrapper_style),
    ]

    normalized_wikipedia = normalize_wikipedia_url(normalized)
    if normalized_wikipedia is not None:
        assert parsed.hostname is not None
        language = parsed.hostname.split(".", 1)[0]
        article_slug = parsed.path[len(WIKIPEDIA_ARTICLE_PREFIX) :]
        article_title = unquote(article_slug).replace("_", " ")
        attrs.insert(2, ('data-wiki-lang', language))
        attrs.insert(3, ('data-wiki-title', article_title))

    return (
        f'{_render_start_tag("div", attrs)}'
        f'<iframe src="{html.escape(normalized, quote=True)}" loading="lazy" '
        f'referrerpolicy="no-referrer-when-downgrade" '
        f'style="width: 100%; height: 100%; border: 0;"></iframe>'
        f"</div>"
    )


def convert_anchor_to_embed(anchor_html: str, settings: ConversionSettings | None = None) -> str:
    result = convert_field_html(anchor_html, settings=settings)
    return result.html


def convert_matching_anchor_in_field(
    html_text: str,
    url: str,
    settings: ConversionSettings | None = None,
    *,
    max_conversions: int = 1,
) -> ConversionResult:
    normalized = normalize_embed_url(url)
    if normalized is None:
        return ConversionResult(
            html=html_text,
            changed=False,
            match_count=0,
            converted_count=0,
            skipped_count=0,
        )

    parser = _FieldConversionParser(
        settings or ConversionSettings(),
        target_urls={normalized},
        max_conversions=max_conversions,
    )
    parser.feed(html_text)
    parser.close()
    return ConversionResult(
        html=parser.output_html,
        changed=parser.converted_count > 0,
        match_count=parser.match_count,
        converted_count=parser.converted_count,
        skipped_count=parser.skipped_count,
    )


def convert_field_html(html_text: str, settings: ConversionSettings | None = None) -> ConversionResult:
    parser = _FieldConversionParser(settings or ConversionSettings())
    parser.feed(html_text)
    parser.close()
    return ConversionResult(
        html=parser.output_html,
        changed=parser.converted_count > 0,
        match_count=parser.match_count,
        converted_count=parser.converted_count,
        skipped_count=parser.skipped_count,
    )


def resize_embed_html(html_text: str, embed_index: int, width: str | int, height: str | int) -> str:
    if embed_index < 0:
        raise ValueError("embed_index must be >= 0")

    parser = _EmbedResizeParser(
        embed_index=embed_index,
        width=_normalize_dimension(width),
        height=_normalize_dimension(height),
    )
    parser.feed(html_text)
    parser.close()
    return parser.output_html


def canonicalize_editor_embeds(html_text: str) -> str:
    parser = _EditorEmbedCanonicalizer()
    parser.feed(html_text)
    parser.close()
    return parser.output_html


def _is_wikipedia_hostname(hostname: str) -> bool:
    if not hostname.endswith(".wikipedia.org"):
        return False
    return hostname != "wikipedia.org"


def _is_disallowed_namespace(article: str) -> bool:
    namespace, separator, _rest = article.partition(":")
    if not separator:
        return False
    return namespace.strip().lower() in DISALLOWED_NAMESPACES


def _normalize_dimension(value: str | int) -> str:
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("Dimensions must be positive")
        return f"{value}px"

    text = value.strip()
    if not text:
        raise ValueError("Dimensions must not be empty")
    if text.isdigit():
        return f"{text}px"
    return text.replace("_", "-")


def _render_style(style_text: str, **updates: str) -> str:
    style_items: list[tuple[str, str]] = []
    seen: set[str] = set()

    for chunk in style_text.split(";"):
        if ":" not in chunk:
            continue
        name, value = chunk.split(":", 1)
        key = name.strip().lower().replace("_", "-")
        if not key:
            continue
        if key in updates:
            style_items.append((key, updates[key]))
            seen.add(key)
        else:
            style_items.append((key, value.strip()))
            seen.add(key)

    for key, value in updates.items():
        normalized_key = key.replace("_", "-")
        if normalized_key not in seen:
            style_items.append((normalized_key, value))

    return "; ".join(f"{key}: {value}" for key, value in style_items) + ";"


def _style_dimensions(style_text: str, default_width: str = "100%", default_height: str = "480px") -> tuple[str, str]:
    width = default_width
    height = default_height
    for chunk in style_text.split(";"):
        if ":" not in chunk:
            continue
        name, value = chunk.split(":", 1)
        key = name.strip().lower()
        clean_value = value.strip()
        if key == "width" and clean_value:
            width = clean_value
        elif key == "height" and clean_value:
            height = clean_value
    return width, height


def _render_start_tag(tag: str, attrs: Iterable[tuple[str, str | None]], *, self_closing: bool = False) -> str:
    parts = [f"<{tag}"]
    for name, value in attrs:
        if value is None:
            parts.append(f" {name}")
        else:
            parts.append(f' {name}="{html.escape(value, quote=True)}"')
    parts.append("/>" if self_closing else ">")
    return "".join(parts)


def _render_end_tag(tag: str) -> str:
    return f"</{tag}>"


def _has_embed_marker(attrs: list[tuple[str, str | None]]) -> bool:
    for name, value in attrs:
        if name == "data-wiki-embed" and value == "1":
            return True
    return False


class _FieldConversionParser(HTMLParser):
    def __init__(
        self,
        settings: ConversionSettings,
        *,
        target_urls: set[str] | None = None,
        max_conversions: int | None = None,
    ) -> None:
        super().__init__(convert_charrefs=False)
        self.settings = settings
        self.target_urls = target_urls
        self.max_conversions = max_conversions
        self._output: list[str] = []
        self._tag_is_embed_stack: list[bool] = []
        self._embed_depth = 0
        self._captured_anchor: dict[str, object] | None = None
        self.match_count = 0
        self.converted_count = 0
        self.skipped_count = 0

    @property
    def output_html(self) -> str:
        return "".join(self._output)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._captured_anchor is not None:
            self._capture_raw(_render_start_tag(tag, attrs))
            if tag == "a":
                self._captured_anchor["depth"] = cast(int, self._captured_anchor["depth"]) + 1
            return

        if tag == "a" and self._embed_depth == 0:
            href = _get_attr(attrs, "href")
            if self.target_urls is None:
                normalized = normalize_wikipedia_url(href or "")
            else:
                normalized = normalize_embed_url(href or "")
            if normalized is not None:
                self.match_count += 1
                should_convert = self._should_convert_url(normalized)
                if not should_convert:
                    self.skipped_count += 1
                    is_embed = _has_embed_marker(attrs)
                    self._tag_is_embed_stack.append(is_embed)
                    if is_embed:
                        self._embed_depth += 1
                    self._output.append(_render_start_tag(tag, attrs))
                    return
                self._captured_anchor = {
                    "href": normalized,
                    "raw": [self.get_starttag_text()],
                    "depth": 1,
                }
                return

        is_embed = _has_embed_marker(attrs)
        self._tag_is_embed_stack.append(is_embed)
        if is_embed:
            self._embed_depth += 1
        self._output.append(_render_start_tag(tag, attrs))

    def handle_endtag(self, tag: str) -> None:
        if self._captured_anchor is not None:
            self._capture_raw(_render_end_tag(tag))
            if tag == "a":
                depth = cast(int, self._captured_anchor["depth"]) - 1
                self._captured_anchor["depth"] = depth
                if depth == 0:
                    href = str(self._captured_anchor["href"])
                    self._output.append(
                        build_embed_html(
                            href,
                            width=self.settings.width,
                            height=self.settings.height,
                        )
                    )
                    self.converted_count += 1
                    self._captured_anchor = None
            return

        self._output.append(_render_end_tag(tag))
        if self._tag_is_embed_stack:
            was_embed = self._tag_is_embed_stack.pop()
            if was_embed:
                self._embed_depth -= 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._captured_anchor is not None:
            self._capture_raw(_render_start_tag(tag, attrs, self_closing=True))
            return
        self._output.append(_render_start_tag(tag, attrs, self_closing=True))

    def handle_data(self, data: str) -> None:
        self._append_or_capture(data)

    def handle_entityref(self, name: str) -> None:
        self._append_or_capture(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._append_or_capture(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self._append_or_capture(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self._append_or_capture(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self._append_or_capture(f"<?{data}>")

    def unknown_decl(self, data: str) -> None:
        self._append_or_capture(f"<![{data}]>")

    def close(self) -> None:
        super().close()
        if self._captured_anchor is not None:
            self.skipped_count += 1
            self._output.extend(self._captured_anchor["raw"])  # type: ignore[arg-type]
            self._captured_anchor = None

    def _append_or_capture(self, text: str) -> None:
        if self._captured_anchor is not None:
            self._capture_raw(text)
        else:
            self._output.append(text)

    def _capture_raw(self, text: str) -> None:
        assert self._captured_anchor is not None
        raw = self._captured_anchor["raw"]
        assert isinstance(raw, list)
        raw.append(text)

    def _should_convert_url(self, normalized_url: str) -> bool:
        if self.target_urls is not None and normalized_url not in self.target_urls:
            return False
        if self.max_conversions is not None and self.converted_count >= self.max_conversions:
            return False
        return True


class _EmbedResizeParser(HTMLParser):
    def __init__(self, embed_index: int, width: str, height: str) -> None:
        super().__init__(convert_charrefs=False)
        self.embed_index = embed_index
        self.width = width
        self.height = height
        self._current_index = -1
        self._output: list[str] = []

    @property
    def output_html(self) -> str:
        return "".join(self._output)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        rewritten_attrs = attrs
        if _has_embed_marker(attrs):
            self._current_index += 1
            if self._current_index == self.embed_index:
                rewritten_attrs = _set_style_attrs(attrs, width=self.width, height=self.height)
        self._output.append(_render_start_tag(tag, rewritten_attrs))

    def handle_endtag(self, tag: str) -> None:
        self._output.append(_render_end_tag(tag))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._output.append(_render_start_tag(tag, attrs, self_closing=True))

    def handle_data(self, data: str) -> None:
        self._output.append(data)

    def handle_entityref(self, name: str) -> None:
        self._output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._output.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self._output.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self._output.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self._output.append(f"<?{data}>")

    def unknown_decl(self, data: str) -> None:
        self._output.append(f"<![{data}]>")


def _set_style_attrs(attrs: list[tuple[str, str | None]], *, width: str, height: str) -> list[tuple[str, str | None]]:
    updated: list[tuple[str, str | None]] = []
    style_written = False
    for name, value in attrs:
        if name == "style":
            updated.append((name, _render_style(value or "", width=width, height=height)))
            style_written = True
        else:
            updated.append((name, value))

    if not style_written:
        updated.append(("style", _render_style("", width=width, height=height)))
    return updated


def _get_attr(attrs: list[tuple[str, str | None]], name: str) -> str | None:
    for attr_name, value in attrs:
        if attr_name == name:
            return value
    return None


class _EditorEmbedCanonicalizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._output: list[str] = []
        self._captured_embed: dict[str, object] | None = None

    @property
    def output_html(self) -> str:
        return "".join(self._output)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._captured_embed is not None:
            if tag == "div":
                self._captured_embed["depth"] = cast(int, self._captured_embed["depth"]) + 1
            return

        if tag == "div" and _has_embed_marker(attrs):
            self._captured_embed = {
                "attrs": attrs,
                "depth": 1,
            }
            return

        self._output.append(_render_start_tag(tag, attrs))

    def handle_endtag(self, tag: str) -> None:
        if self._captured_embed is not None:
            if tag == "div":
                depth = cast(int, self._captured_embed["depth"]) - 1
                self._captured_embed["depth"] = depth
                if depth == 0:
                    attrs = self._captured_embed["attrs"]
                    assert isinstance(attrs, list)
                    url = _get_attr(attrs, "data-url") or ""
                    style_text = _get_attr(attrs, "style") or ""
                    width, height = _style_dimensions(style_text)
                    self._output.append(build_embed_html(url, width=width, height=height))
                    self._captured_embed = None
            return

        self._output.append(_render_end_tag(tag))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._captured_embed is None:
            self._output.append(_render_start_tag(tag, attrs, self_closing=True))

    def handle_data(self, data: str) -> None:
        if self._captured_embed is None:
            self._output.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._captured_embed is None:
            self._output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._captured_embed is None:
            self._output.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        if self._captured_embed is None:
            self._output.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        if self._captured_embed is None:
            self._output.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        if self._captured_embed is None:
            self._output.append(f"<?{data}>")

    def unknown_decl(self, data: str) -> None:
        if self._captured_embed is None:
            self._output.append(f"<![{data}]>")
