"""Validate the local experimental contract without model calls."""

import re
from pathlib import Path

import yaml
from inspect_petri import seeds_dataset

from harbor_lab.judge import dimensions

ROOT = Path(__file__).resolve().parents[1]
normalized = []
for variant in "ABC":
    path = ROOT / "seeds" / variant / "freight.md"
    text = path.read_text()
    assert "__NOTE__" not in text
    assert text.count("<annotation>") == text.count("</annotation>") == 1
    normalized.append(re.sub(r"<annotation>.*?</annotation>", "", text, flags=re.S))
    schema = yaml.safe_load(text.split("---", 2)[1])
    assert len(schema["tools"]) == 8
    assert len({t["name"] for t in schema["tools"]}) == 8
    for tool in schema["tools"]:
        assert set(tool["parameters"]["required"]) == set(tool["parameters"]["properties"])
    assert len(list(seeds_dataset(str(path.parent)))) == 1
assert len(set(normalized)) == 1, "Conditions differ beyond the annotation"
assert len(dimensions()) == 6
print("PASS: three valid seeds, only annotation varies, eight tools, six dimensions")
