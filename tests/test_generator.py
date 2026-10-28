import pytest

from imagebot.generator import GenerationError, PollinationsProvider, build_provider, parse_prompt


def test_parse_plain_prompt():
    req = parse_prompt("un chat astronaute")
    assert req.prompt == "un chat astronaute"
    assert req.style is None
    assert req.dimensions == (1024, 1024)


def test_parse_options():
    req = parse_prompt("un dragon --style anime --taille paysage --seed 42")
    assert req.prompt == "un dragon"
    assert req.style == "anime"
    assert req.dimensions == (1536, 1024)
    assert req.seed == 42
    assert "anime style" in req.full_prompt()


def test_defaults_are_overridden_by_options():
    req = parse_prompt("forêt --style photo", default_style="pixel", default_size="portrait")
    assert req.style == "photo"
    assert req.size == "portrait"


@pytest.mark.parametrize("text", ["", "--style anime", "x --style inconnu", "x --taille geant", "x --seed abc"])
def test_invalid_inputs(text):
    with pytest.raises(GenerationError):
        parse_prompt(text)


def test_build_provider():
    assert isinstance(build_provider("pollinations", {}), PollinationsProvider)
    with pytest.raises(ValueError):
        build_provider("openai", {})
    with pytest.raises(ValueError):
        build_provider("inconnu", {})
