"""Coverage-pass tests for ``config2py.codecs``: registration edge cases, the
line/csv/tsv/xml codecs and the optional-dependency ones (skipped when absent)."""

import pytest

from config2py import codecs as c


@pytest.fixture
def clean_registry():
    enc, dec = dict(c.EXTENSION_TO_ENCODER), dict(c.EXTENSION_TO_DECODER)
    yield
    c.EXTENSION_TO_ENCODER.clear()
    c.EXTENSION_TO_ENCODER.update(enc)
    c.EXTENSION_TO_DECODER.clear()
    c.EXTENSION_TO_DECODER.update(dec)


def test_register_decoder_and_encoder_decorators(clean_registry):
    @c.register_decoder("zzx")
    def dec(data):
        return data.decode()

    @c.register_encoder(".ZZX")
    def enc(obj):
        return str(obj).encode()

    assert c.decode_by_extension("a.zzx", b"hi") == "hi"
    assert c.encode_by_extension("a.zzx", 5) == b"5"
    with pytest.raises(ValueError):
        c.register_decoder(".zzx")(dec)
    with pytest.raises(ValueError):
        c.register_encoder(".zzx")(enc)
    c.register_decoder(".zzx", overwrite=True)(dec)


def test_register_codec_no_overwrite(clean_registry):
    c.register_codec("zzy", encoder=lambda o: b"", decoder=lambda d: 1)
    with pytest.raises(ValueError, match="Encoder"):
        c.register_codec(".zzy", encoder=lambda o: b"")
    with pytest.raises(ValueError, match="Decoder"):
        c.register_codec(".zzy", decoder=lambda d: 1)


def test_get_codec_info_normalizes_extension():
    assert c.get_codec_info("JSON") == c.get_codec_info(".json")
    assert c.is_extension_registered("JSON")
    assert ".json" in c.list_registered_extensions()


def test_lsv_roundtrip_and_encoder_branches():
    assert c.encode_by_extension("x.lsv", ["a", "b"]) == b"a\nb"
    assert c._lsv_encoder("abc") == b"abc"
    assert c._lsv_encoder(12) == b"12"


@pytest.mark.parametrize("ext", [".csv", ".tsv"])
def test_csv_tsv_encoders(ext):
    rows = [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
    assert (
        c.decode_by_extension("t" + ext, c.encode_by_extension("t" + ext, rows)) == rows
    )
    assert c.encode_by_extension("t" + ext, []) == b""
    # a single dict is treated as one row
    one = c.encode_by_extension("t" + ext, {"a": "1"})
    assert c.decode_by_extension("t" + ext, one) == [{"a": "1"}]
    # list of lists, no header
    lol = c.encode_by_extension("t" + ext, [["x", "y"], ["1", "2"]])
    assert b"x" in lol and lol.count(b"\n") == 2


def test_ini_roundtrip():
    obj = {"sec": {"k": "v"}}
    assert c.decode_by_extension("a.ini", c.encode_by_extension("a.ini", obj)) == obj


def test_xml_roundtrip_shapes():
    if ".xml" not in c.EXTENSION_TO_ENCODER:
        pytest.skip("xml codec not registered")
    data = c.encode_by_extension("a.xml", {"a": "1", "sub": {"x": "2"}, "l": [1, 2]})
    assert b"<a>1</a>" in data and b"<item>1</item>" in data and b"<x>2</x>" in data
    assert isinstance(c.decode_by_extension("a.xml", data), dict)


def test_toml_roundtrip():
    pytest.importorskip("tomli_w")
    obj = {"a": 1, "t": {"b": "x"}}
    assert c.decode_by_extension("a.toml", c.encode_by_extension("a.toml", obj)) == obj


@pytest.mark.parametrize("ext", [".yaml", ".yml"])
def test_yaml_roundtrip(ext):
    pytest.importorskip("yaml")
    obj = {"a": [1, 2], "b": {"c": "d"}}
    assert (
        c.decode_by_extension("a" + ext, c.encode_by_extension("a" + ext, obj)) == obj
    )


def test_env_roundtrip():
    obj = {"A": "1", "B": "two words"}
    out = c.decode_by_extension("x.env", c.encode_by_extension("x.env", obj))
    assert out["A"] == "1" and out["B"] == "two words"


def test_json5_roundtrip():
    pytest.importorskip("json5")
    obj = {"a": 1}
    assert (
        c.decode_by_extension("a.json5", c.encode_by_extension("a.json5", obj)) == obj
    )


def test_unknown_extension_errors():
    with pytest.raises(Exception):
        c.decode_by_extension("a.nope_not_registered", b"")
