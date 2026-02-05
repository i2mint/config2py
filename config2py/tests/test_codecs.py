"""Tests for config2py.codecs module."""

import pytest
from config2py import codecs


class TestCodecRegistry:
    """Test codec registration and introspection."""

    def test_list_registered_extensions(self):
        """Test listing all registered extensions."""
        extensions = codecs.list_registered_extensions()
        assert isinstance(extensions, list)
        assert '.json' in extensions
        assert '.ini' in extensions
        assert '.csv' in extensions

    def test_is_extension_registered(self):
        """Test checking if extension is registered."""
        assert codecs.is_extension_registered('.json')
        assert codecs.is_extension_registered('json')  # without dot
        assert not codecs.is_extension_registered('.nonexistent')

    def test_get_codec_info(self):
        """Test getting codec information."""
        info = codecs.get_codec_info('.json')
        assert info['extension'] == '.json'
        assert info['has_encoder'] is True
        assert info['has_decoder'] is True
        assert info['dependency'] is None  # json is stdlib

    def test_get_extension(self):
        """Test extension extraction."""
        assert codecs.get_extension('config.json') == 'json'
        assert codecs.get_extension('/path/to/file.yaml') == 'yaml'
        assert codecs.get_extension('no_extension') == ''
        assert codecs.get_extension('file.tar.gz') == 'gz'


class TestJSONCodec:
    """Test JSON encoding/decoding."""

    def test_json_roundtrip(self):
        """Test JSON encode -> decode roundtrip."""
        data = {'name': 'test', 'value': 42, 'nested': {'key': 'value'}}
        encoded = codecs.encode_by_extension('config.json', data)
        assert isinstance(encoded, bytes)
        decoded = codecs.decode_by_extension('config.json', encoded)
        assert decoded == data

    def test_json_with_unicode(self):
        """Test JSON with unicode characters."""
        data = {'message': 'Hello 世界', 'emoji': '🎉'}
        encoded = codecs.encode_by_extension('data.json', data)
        decoded = codecs.decode_by_extension('data.json', encoded)
        assert decoded == data


class TestPickleCodec:
    """Test pickle encoding/decoding."""

    def test_pickle_roundtrip(self):
        """Test pickle encode -> decode roundtrip."""
        data = {'list': [1, 2, 3], 'tuple': (4, 5, 6), 'set': {7, 8, 9}}
        encoded = codecs.encode_by_extension('data.pkl', data)
        decoded = codecs.decode_by_extension('data.pkl', encoded)
        assert decoded == data

    def test_pickle_alias(self):
        """Test .pickle extension alias."""
        data = {'key': 'value'}
        encoded = codecs.encode_by_extension('data.pickle', data)
        decoded = codecs.decode_by_extension('data.pickle', encoded)
        assert decoded == data


class TestTextCodec:
    """Test plain text encoding/decoding."""

    def test_text_roundtrip(self):
        """Test text encode -> decode roundtrip."""
        text = "Hello, World!\nThis is a test."
        encoded = codecs.encode_by_extension('file.txt', text)
        decoded = codecs.decode_by_extension('file.txt', encoded)
        assert decoded == text


class TestLSVCodec:
    """Test line-separated values encoding/decoding."""

    def test_lsv_list_roundtrip(self):
        """Test LSV with list input."""
        data = ['apple', 'banana', 'cherry']
        encoded = codecs.encode_by_extension('data.lsv', data)
        decoded = codecs.decode_by_extension('data.lsv', encoded)
        assert decoded == data

    def test_lsv_aliases(self):
        """Test .list and .lines aliases."""
        data = ['one', 'two', 'three']

        # .list extension
        encoded = codecs.encode_by_extension('data.list', data)
        decoded = codecs.decode_by_extension('data.list', encoded)
        assert decoded == data

        # .lines extension
        encoded = codecs.encode_by_extension('data.lines', data)
        decoded = codecs.decode_by_extension('data.lines', encoded)
        assert decoded == data


class TestCSVCodec:
    """Test CSV encoding/decoding."""

    def test_csv_dict_list_roundtrip(self):
        """Test CSV with list of dicts."""
        data = [
            {'name': 'Alice', 'age': '30'},
            {'name': 'Bob', 'age': '25'},
        ]
        encoded = codecs.encode_by_extension('data.csv', data)
        decoded = codecs.decode_by_extension('data.csv', encoded)
        # CSV decoder returns all values as strings
        assert decoded == data

    def test_csv_empty(self):
        """Test CSV with empty data."""
        encoded = codecs.encode_by_extension('data.csv', [])
        assert encoded == b''


class TestTSVCodec:
    """Test TSV encoding/decoding."""

    def test_tsv_roundtrip(self):
        """Test TSV encode -> decode roundtrip."""
        data = [
            {'col1': 'value1', 'col2': 'value2'},
            {'col1': 'value3', 'col2': 'value4'},
        ]
        encoded = codecs.encode_by_extension('data.tsv', data)
        decoded = codecs.decode_by_extension('data.tsv', encoded)
        assert decoded == data

    def test_tsv_tab_alias(self):
        """Test .tab extension alias."""
        data = [{'a': '1', 'b': '2'}]
        encoded = codecs.encode_by_extension('data.tab', data)
        decoded = codecs.decode_by_extension('data.tab', encoded)
        assert decoded == data


class TestINICodec:
    """Test INI/CFG encoding/decoding."""

    def test_ini_roundtrip(self):
        """Test INI encode -> decode roundtrip."""
        data = {
            'section1': {'key1': 'value1', 'key2': 'value2'},
            'section2': {'key3': 'value3'},
        }
        encoded = codecs.encode_by_extension('config.ini', data)
        decoded = codecs.decode_by_extension('config.ini', encoded)
        assert decoded == data

    def test_cfg_alias(self):
        """Test .cfg extension."""
        data = {'database': {'host': 'localhost', 'port': '5432'}}
        encoded = codecs.encode_by_extension('config.cfg', data)
        decoded = codecs.decode_by_extension('config.cfg', encoded)
        assert decoded == data

    def test_conf_alias(self):
        """Test .conf extension."""
        data = {'settings': {'debug': 'true'}}
        encoded = codecs.encode_by_extension('app.conf', data)
        decoded = codecs.decode_by_extension('app.conf', encoded)
        assert decoded == data


class TestXMLCodec:
    """Test XML encoding/decoding (if available)."""

    def test_xml_roundtrip(self):
        """Test XML encode -> decode roundtrip."""
        if not codecs.is_extension_registered('.xml'):
            pytest.skip("XML codec not available")

        data = {'config': {'setting1': 'value1', 'setting2': 'value2'}}
        encoded = codecs.encode_by_extension('config.xml', data)
        decoded = codecs.decode_by_extension('config.xml', encoded)
        # Basic structure should match
        assert 'config' in decoded


class TestENVCodec:
    """Test .env file encoding/decoding."""

    def test_env_roundtrip(self):
        """Test .env encode -> decode roundtrip."""
        data = {
            'DATABASE_URL': 'postgresql://localhost/db',
            'API_KEY': 'secret123',
            'DEBUG': 'true',
        }
        encoded = codecs.encode_by_extension('.env', data)
        decoded = codecs.decode_by_extension('.env', encoded)
        assert decoded == data

    def test_env_with_spaces(self):
        """Test .env with values containing spaces."""
        data = {'MESSAGE': 'Hello World', 'PATH': '/usr/bin:/usr/local/bin'}
        encoded = codecs.encode_by_extension('.env', data)
        decoded = codecs.decode_by_extension('.env', encoded)
        # Values should be preserved (quotes may be added/removed)
        assert 'MESSAGE' in decoded
        assert 'PATH' in decoded


class TestPropertiesCodec:
    """Test .properties file encoding/decoding."""

    def test_properties_roundtrip(self):
        """Test .properties encode -> decode roundtrip."""
        data = {
            'app.name': 'MyApp',
            'app.version': '1.0.0',
            'server.port': '8080',
        }
        encoded = codecs.encode_by_extension('config.properties', data)
        decoded = codecs.decode_by_extension('config.properties', encoded)
        assert decoded == data


class TestCustomCodecRegistration:
    """Test custom codec registration."""

    def test_register_codec_function(self):
        """Test registering codec via function."""

        def custom_encoder(obj):
            return f"CUSTOM:{obj}".encode()

        def custom_decoder(data):
            return data.decode().replace('CUSTOM:', '')

        codecs.register_codec(
            '.custom',
            encoder=custom_encoder,
            decoder=custom_decoder,
            overwrite=True,
        )

        data = "test data"
        encoded = codecs.encode_by_extension('file.custom', data)
        decoded = codecs.decode_by_extension('file.custom', encoded)
        assert decoded == data

        # Cleanup
        del codecs.EXTENSION_TO_ENCODER['.custom']
        del codecs.EXTENSION_TO_DECODER['.custom']

    def test_register_codec_decorator(self):
        """Test registering codec via decorators."""

        @codecs.register_encoder('.test')
        def encode_test(obj):
            return f"TEST:{obj}".encode()

        @codecs.register_decoder('.test')
        def decode_test(data):
            return data.decode().replace('TEST:', '')

        data = "hello"
        encoded = codecs.encode_by_extension('data.test', data)
        decoded = codecs.decode_by_extension('data.test', encoded)
        assert decoded == data

        # Cleanup
        del codecs.EXTENSION_TO_ENCODER['.test']
        del codecs.EXTENSION_TO_DECODER['.test']

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate codec raises error."""
        # JSON is already registered
        with pytest.raises(ValueError, match="already registered"):
            codecs.register_codec('.json', encoder=lambda x: b'')

    def test_register_with_overwrite(self):
        """Test that overwrite=True allows replacing codec."""

        def new_encoder(obj):
            return b'NEW'

        # This should not raise
        codecs.register_codec(
            '.json',
            encoder=new_encoder,
            overwrite=True,
        )

        # Restore original
        codecs.register_codec(
            '.json',
            encoder=lambda obj: codecs.json.dumps(
                obj, indent=2, ensure_ascii=False
            ).encode('utf-8'),
            overwrite=True,
        )


class TestErrorHandling:
    """Test error handling."""

    def test_unknown_extension_encoder(self):
        """Test encoding with unknown extension raises error."""
        with pytest.raises(ValueError, match="No encoder registered"):
            codecs.encode_by_extension('file.unknown', {})

    def test_unknown_extension_decoder(self):
        """Test decoding with unknown extension raises error."""
        with pytest.raises(ValueError, match="No decoder registered"):
            codecs.decode_by_extension('file.unknown', b'')


class TestConditionalCodecs:
    """Test conditionally available codecs."""

    def test_toml_if_available(self):
        """Test TOML codec if available."""
        if not codecs.is_extension_registered('.toml'):
            pytest.skip("TOML codec not available")

        data = {'table': {'key': 'value', 'number': 42}}

        has_encoder = '.toml' in codecs.EXTENSION_TO_ENCODER
        has_decoder = '.toml' in codecs.EXTENSION_TO_DECODER

        if has_encoder and has_decoder:
            encoded = codecs.encode_by_extension('config.toml', data)
            decoded = codecs.decode_by_extension('config.toml', encoded)
            assert decoded == data
        elif has_decoder:
            # tomllib (3.11+) or tomli available for reading, but no tomli_w for writing
            toml_bytes = b'[table]\nkey = "value"\nnumber = 42\n'
            decoded = codecs.decode_by_extension('config.toml', toml_bytes)
            assert decoded == data

    def test_yaml_if_available(self):
        """Test YAML codec if available."""
        if not codecs.is_extension_registered('.yaml'):
            pytest.skip("YAML codec not available")

        data = {'key': 'value', 'list': [1, 2, 3], 'nested': {'a': 'b'}}
        encoded = codecs.encode_by_extension('config.yaml', data)
        decoded = codecs.decode_by_extension('config.yaml', encoded)
        assert decoded == data

    def test_yml_alias_if_available(self):
        """Test .yml alias if YAML available."""
        if not codecs.is_extension_registered('.yml'):
            pytest.skip("YAML codec not available")

        data = {'test': 'data'}
        encoded = codecs.encode_by_extension('config.yml', data)
        decoded = codecs.decode_by_extension('config.yml', encoded)
        assert decoded == data

    def test_json5_if_available(self):
        """Test JSON5 codec if available."""
        if not codecs.is_extension_registered('.json5'):
            pytest.skip("JSON5 codec not available")

        data = {'key': 'value', 'number': 123}
        encoded = codecs.encode_by_extension('config.json5', data)
        decoded = codecs.decode_by_extension('config.json5', encoded)
        assert decoded == data
