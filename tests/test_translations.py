"""strings.json and translations/*.json must stay in sync.

Checks, for every translations/<lang>.json against strings.json:
 - no orphaned keys (every key exists in strings.json),
 - no empty values,
 - the same {placeholders} in every message.

Only the maintained languages (COMPLETE) must also have every key. Community
translations may lag behind: Home Assistant falls back to English for missing
keys, and a new string should not need a translation nobody else can write.

Stdlib only; no Home Assistant needed.
"""

import json
import re
from pathlib import Path

import pytest

BASE = Path(__file__).parent.parent / "custom_components" / "bwt_perla"
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _flatten(node, prefix=""):
    flat = {}
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, f"{path}."))
        else:
            flat[path] = value
    return flat


def _load(path):
    return _flatten(json.loads(path.read_text(encoding="utf-8")))


STRINGS = _load(BASE / "strings.json")
TRANSLATIONS = {p.name: _load(p) for p in sorted((BASE / "translations").glob("*.json"))}
# Languages kept in sync with strings.json by the maintainers.
COMPLETE = {"en.json", "de.json"}


def test_translation_files_found():
    assert COMPLETE <= set(TRANSLATIONS)


@pytest.mark.parametrize("name", TRANSLATIONS)
def test_no_orphaned_keys(name):
    keys = set(TRANSLATIONS[name])
    assert sorted(keys - set(STRINGS)) == [], "not in strings.json (orphaned)"


@pytest.mark.parametrize("name", sorted(COMPLETE))
def test_complete_translations_have_all_keys(name):
    keys = set(TRANSLATIONS[name])
    assert sorted(set(STRINGS) - keys) == [], "missing from translation"


@pytest.mark.parametrize("name", ["strings.json", *TRANSLATIONS])
def test_no_empty_values(name):
    flat = STRINGS if name == "strings.json" else TRANSLATIONS[name]
    assert sorted(k for k, v in flat.items() if not str(v).strip()) == []


@pytest.mark.parametrize("name", TRANSLATIONS)
def test_same_placeholders(name):
    bad = {
        key: (sorted(PLACEHOLDER.findall(text)), sorted(PLACEHOLDER.findall(TRANSLATIONS[name][key])))
        for key, text in STRINGS.items()
        if key in TRANSLATIONS[name]
        and set(PLACEHOLDER.findall(text)) != set(PLACEHOLDER.findall(TRANSLATIONS[name][key]))
    }
    assert bad == {}
