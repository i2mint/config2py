"""Extension-based codec registries for configuration file parsing.

This module provides a flexible pattern for encoding and decoding configuration files
based on their file extensions. It includes codecs for bytes <-> JSON-friendly Python types.

Examples:
    >>> # Basic usage
    >>> data = {'name': 'config2py', 'version': '1.0'}
    >>>
    >>> # Encode to bytes
    >>> encoded = encode_by_extension('config.json', data)
    >>> assert isinstance(encoded, bytes)
    >>>
    >>> # Decode from bytes
    >>> decoded = decode_by_extension('config.json', encoded)
    >>> assert decoded == data
    >>>
    >>> # Register custom codec
    >>> @register_decoder('.custom')
    ... def decode_custom(data: bytes) -> dict:
    ...     return {'custom': data.decode()}
    >>>
    >>> @register_encoder('.custom')
    ... def encode_custom(obj: dict) -> bytes:
    ...     return obj.get('custom', '').encode()

The module automatically registers codecs for standard formats (json, toml, ini, etc.)
and conditionally registers codecs that require third-party libraries (yaml, json5, etc.).
"""

from typing import Callable, TypeVar, Any, Optional
import json
import pickle
import csv
import io
from configparser import ConfigParser
from pathlib import Path

__all__ = [
    # Core functions
    "decode_by_extension",
    "encode_by_extension",
    "get_extension",
    # Registration functions
    "register_codec",
    "register_decoder",
    "register_encoder",
    # Registry access
    "list_registered_extensions",
    "is_extension_registered",
    "get_codec_info",
]

VT = TypeVar("VT")
EncodedT = TypeVar("EncodedT")

# --------------------------------------------------------------------------------------
# Core Registry
# --------------------------------------------------------------------------------------

EXTENSION_TO_DECODER: dict[str, Callable[[bytes], Any]] = {}
EXTENSION_TO_ENCODER: dict[str, Callable[[Any], bytes]] = {}

# Track which codecs require optional dependencies
_CODEC_DEPENDENCIES: dict[str, str] = {}


def get_extension(key: str) -> str:
    """Extract extension from a key (filename, path, etc.).

    Args:
        key: A string that may contain a file extension

    Returns:
        Extension without the dot, or empty string if no extension found

    Examples:
        >>> get_extension('config.json')
        'json'
        >>> get_extension('/path/to/data.yaml')
        'yaml'
        >>> get_extension('no_extension')
        ''
        >>> get_extension('.env')
        'env'
        >>> get_extension('/path/to/.env')
        'env'
    """
    if not key or "." not in key:
        return ""

    # Get the basename (last part of path)
    basename = Path(key).name

    # Handle dotfiles (e.g., .env, .gitignore)
    if basename.startswith(".") and basename.count(".") == 1:
        return basename.lstrip(".").lower()

    # Normal case: extract extension using Path.suffix
    suffix = Path(key).suffix
    return suffix.lstrip(".").lower() if suffix else ""


def decode_by_extension(key: str, data: bytes) -> Any:
    """Decode data based on key's extension.

    Args:
        key: Key or filename with extension
        data: Bytes to decode

    Returns:
        Decoded Python object

    Raises:
        ValueError: If no decoder registered for extension

    Examples:
        >>> data = b'{"key": "value"}'
        >>> decode_by_extension('config.json', data)
        {'key': 'value'}
    """
    ext = get_extension(key)
    ext_with_dot = f".{ext}" if ext else ""
    decoder = EXTENSION_TO_DECODER.get(ext_with_dot)
    if decoder is None:
        available = ", ".join(sorted(EXTENSION_TO_DECODER.keys()))
        raise ValueError(
            f"No decoder registered for extension: '{ext_with_dot}'. "
            f"Available: {available}"
        )
    return decoder(data)


def encode_by_extension(key: str, obj: Any) -> bytes:
    """Encode object based on key's extension.

    Args:
        key: Key or filename with extension
        obj: Python object to encode

    Returns:
        Encoded bytes

    Raises:
        ValueError: If no encoder registered for extension

    Examples:
        >>> obj = {'key': 'value'}
        >>> encoded = encode_by_extension('config.json', obj)
        >>> assert b'"key"' in encoded
    """
    ext = get_extension(key)
    ext_with_dot = f".{ext}" if ext else ""
    encoder = EXTENSION_TO_ENCODER.get(ext_with_dot)
    if encoder is None:
        available = ", ".join(sorted(EXTENSION_TO_ENCODER.keys()))
        raise ValueError(
            f"No encoder registered for extension: '{ext_with_dot}'. "
            f"Available: {available}"
        )
    return encoder(obj)


# --------------------------------------------------------------------------------------
# Registration Functions
# --------------------------------------------------------------------------------------


def register_codec(
    extension: str,
    *,
    encoder: Optional[Callable[[Any], bytes]] = None,
    decoder: Optional[Callable[[bytes], Any]] = None,
    overwrite: bool = False,
    dependency: Optional[str] = None,
):
    """Register encoder and/or decoder for an extension.

    Args:
        extension: File extension (with or without leading dot)
        encoder: Function to encode objects to bytes
        decoder: Function to decode bytes to objects
        overwrite: Whether to overwrite existing codec
        dependency: Optional package name required for this codec

    Raises:
        ValueError: If codec already registered and overwrite=False

    Examples:
        >>> def my_encoder(obj): return str(obj).encode()
        >>> def my_decoder(data): return eval(data.decode())
        >>> register_codec('.custom', encoder=my_encoder, decoder=my_decoder, overwrite=True)
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    extension = extension.lower()

    if not overwrite:
        if encoder and extension in EXTENSION_TO_ENCODER:
            raise ValueError(f"Encoder for '{extension}' already registered")
        if decoder and extension in EXTENSION_TO_DECODER:
            raise ValueError(f"Decoder for '{extension}' already registered")

    if encoder:
        EXTENSION_TO_ENCODER[extension] = encoder
    if decoder:
        EXTENSION_TO_DECODER[extension] = decoder
    if dependency:
        _CODEC_DEPENDENCIES[extension] = dependency


def register_decoder(extension: str, *, overwrite: bool = False):
    """Decorator to register a decoder function.

    Args:
        extension: File extension (with or without leading dot)
        overwrite: Whether to overwrite existing decoder

    Returns:
        Decorator function

    Examples:
        >>> @register_decoder('.custom', overwrite=True)
        ... def decode_custom(data: bytes) -> dict:
        ...     return {'data': data.decode()}
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    extension = extension.lower()

    def decorator(func: Callable[[bytes], Any]) -> Callable:
        if not overwrite and extension in EXTENSION_TO_DECODER:
            raise ValueError(f"Decoder for '{extension}' already registered")
        EXTENSION_TO_DECODER[extension] = func
        return func

    return decorator


def register_encoder(extension: str, *, overwrite: bool = False):
    """Decorator to register an encoder function.

    Args:
        extension: File extension (with or without leading dot)
        overwrite: Whether to overwrite existing encoder

    Returns:
        Decorator function

    Examples:
        >>> @register_encoder('.custom', overwrite=True)
        ... def encode_custom(obj: dict) -> bytes:
        ...     return obj.get('data', '').encode()
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    extension = extension.lower()

    def decorator(func: Callable[[Any], bytes]) -> Callable:
        if not overwrite and extension in EXTENSION_TO_ENCODER:
            raise ValueError(f"Encoder for '{extension}' already registered")
        EXTENSION_TO_ENCODER[extension] = func
        return func

    return decorator


# --------------------------------------------------------------------------------------
# Registry Introspection
# --------------------------------------------------------------------------------------


def list_registered_extensions() -> list[str]:
    """List all registered extensions.

    Returns:
        Sorted list of registered extensions

    Examples:
        >>> extensions = list_registered_extensions()
        >>> '.json' in extensions
        True
    """
    all_extensions = set(EXTENSION_TO_DECODER.keys()) | set(EXTENSION_TO_ENCODER.keys())
    return sorted(all_extensions)


def is_extension_registered(extension: str) -> bool:
    """Check if an extension has any codec registered.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        True if decoder or encoder is registered

    Examples:
        >>> is_extension_registered('.json')
        True
        >>> is_extension_registered('.nonexistent')
        False
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    extension = extension.lower()
    return extension in EXTENSION_TO_DECODER or extension in EXTENSION_TO_ENCODER


def get_codec_info(extension: str) -> dict[str, Any]:
    """Get information about a registered codec.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        Dictionary with codec information

    Examples:
        >>> info = get_codec_info('.json')
        >>> info['has_encoder']
        True
        >>> info['has_decoder']
        True
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    extension = extension.lower()

    return {
        "extension": extension,
        "has_encoder": extension in EXTENSION_TO_ENCODER,
        "has_decoder": extension in EXTENSION_TO_DECODER,
        "dependency": _CODEC_DEPENDENCIES.get(extension),
    }


# --------------------------------------------------------------------------------------
# Standard Library Codecs (Always Available)
# --------------------------------------------------------------------------------------

# JSON - Most common config format
register_codec(
    ".json",
    encoder=lambda obj: json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8"),
    decoder=lambda data: json.loads(data.decode("utf-8")),
)

# Pickle - Python object serialization (not text-based, but useful)
register_codec(
    ".pkl",
    encoder=pickle.dumps,
    decoder=pickle.loads,
)
register_codec(".pickle", encoder=pickle.dumps, decoder=pickle.loads)

# Plain text
register_codec(
    ".txt",
    encoder=lambda obj: str(obj).encode("utf-8"),
    decoder=lambda data: data.decode("utf-8"),
)


# Line-separated values (LSV) - one value per line
def _lsv_encoder(obj: Any) -> bytes:
    """Encode list/iterable to line-separated values."""
    if isinstance(obj, (list, tuple)):
        return "\n".join(str(item) for item in obj).encode("utf-8")
    elif isinstance(obj, str):
        return obj.encode("utf-8")
    else:
        return str(obj).encode("utf-8")


def _lsv_decoder(data: bytes) -> list[str]:
    """Decode line-separated values to list."""
    text = data.decode("utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


register_codec(".lsv", encoder=_lsv_encoder, decoder=_lsv_decoder)
register_codec(".list", encoder=_lsv_encoder, decoder=_lsv_decoder)
register_codec(".lines", encoder=_lsv_encoder, decoder=_lsv_decoder)


# CSV - Comma-separated values
def _csv_encoder(obj: Any) -> bytes:
    """Encode list of dicts or list of lists to CSV."""
    output = io.StringIO()

    if not obj:
        return b""

    if isinstance(obj, dict):
        # Single dict - treat as one row
        obj = [obj]

    if isinstance(obj[0], dict):
        # List of dicts
        fieldnames = list(obj[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(obj)
    else:
        # List of lists/tuples
        writer = csv.writer(output)
        writer.writerows(obj)

    return output.getvalue().encode("utf-8")


def _csv_decoder(data: bytes) -> list[dict[str, str]]:
    """Decode CSV to list of dicts."""
    text = data.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


register_codec(".csv", encoder=_csv_encoder, decoder=_csv_decoder)


# TSV - Tab-separated values
def _tsv_encoder(obj: Any) -> bytes:
    """Encode list of dicts or list of lists to TSV."""
    output = io.StringIO()

    if not obj:
        return b""

    if isinstance(obj, dict):
        obj = [obj]

    if isinstance(obj[0], dict):
        fieldnames = list(obj[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(obj)
    else:
        writer = csv.writer(output, delimiter="\t")
        writer.writerows(obj)

    return output.getvalue().encode("utf-8")


def _tsv_decoder(data: bytes) -> list[dict[str, str]]:
    """Decode TSV to list of dicts."""
    text = data.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return list(reader)


register_codec(".tsv", encoder=_tsv_encoder, decoder=_tsv_decoder)
register_codec(".tab", encoder=_tsv_encoder, decoder=_tsv_decoder)


# INI/CFG - ConfigParser format
def _ini_encoder(obj: dict) -> bytes:
    """Encode dict to INI format."""
    config = ConfigParser()
    for section, values in obj.items():
        config[section] = {k: str(v) for k, v in values.items()}
    output = io.StringIO()
    config.write(output)
    return output.getvalue().encode("utf-8")


def _ini_decoder(data: bytes) -> dict[str, dict[str, str]]:
    """Decode INI format to nested dict."""
    config = ConfigParser()
    config.read_string(data.decode("utf-8"))
    return {section: dict(config[section]) for section in config.sections()}


register_codec(".ini", encoder=_ini_encoder, decoder=_ini_decoder)
register_codec(".cfg", encoder=_ini_encoder, decoder=_ini_decoder)
register_codec(".conf", encoder=_ini_encoder, decoder=_ini_decoder)

# XML - Basic XML support using ElementTree
try:
    import xml.etree.ElementTree as ET

    def _xml_encoder(obj: dict) -> bytes:
        """Encode dict to simple XML format."""

        def dict_to_xml(tag: str, d: dict) -> ET.Element:
            """Convert dict to XML element."""
            elem = ET.Element(tag)
            for key, val in d.items():
                child = ET.SubElement(elem, key)
                if isinstance(val, dict):
                    for k, v in val.items():
                        subchild = ET.SubElement(child, k)
                        subchild.text = str(v)
                elif isinstance(val, (list, tuple)):
                    for item in val:
                        item_elem = ET.SubElement(child, "item")
                        item_elem.text = str(item)
                else:
                    child.text = str(val)
            return elem

        root = dict_to_xml("root", obj)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _xml_decoder(data: bytes) -> dict:
        """Decode XML to dict."""

        def xml_to_dict(elem: ET.Element) -> dict:
            """Convert XML element to dict."""
            result = {}
            for child in elem:
                if len(child) == 0:
                    # Leaf node
                    result[child.tag] = child.text
                else:
                    # Has children
                    if child.tag not in result:
                        result[child.tag] = {}
                    child_dict = xml_to_dict(child)
                    if isinstance(result[child.tag], dict):
                        result[child.tag].update(child_dict)
                    else:
                        result[child.tag] = child_dict
            return result

        root = ET.fromstring(data)
        return xml_to_dict(root)

    register_codec(".xml", encoder=_xml_encoder, decoder=_xml_decoder)
except ImportError:
    pass

# --------------------------------------------------------------------------------------
# TOML - Conditionally available based on Python version
# --------------------------------------------------------------------------------------

# Try Python 3.11+ built-in tomllib for reading
try:
    import tomllib

    register_codec(
        ".toml",
        decoder=lambda data: tomllib.loads(data.decode("utf-8")),
    )
except ImportError:
    # Try tomli for older Python versions
    try:
        import tomli

        register_codec(
            ".toml",
            decoder=lambda data: tomli.loads(data.decode("utf-8")),
            dependency="tomli",
        )
    except ImportError:
        pass

# Try tomli_w for TOML writing (not in stdlib)
try:
    import tomli_w

    # Register encoder (or update if decoder already registered)
    if ".toml" in EXTENSION_TO_DECODER:
        EXTENSION_TO_ENCODER[".toml"] = lambda obj: tomli_w.dumps(obj).encode("utf-8")
    else:
        register_codec(
            ".toml",
            encoder=lambda obj: tomli_w.dumps(obj).encode("utf-8"),
            dependency="tomli_w",
        )
except ImportError:
    pass

# --------------------------------------------------------------------------------------
# Third-Party Codecs (Conditionally Registered)
# --------------------------------------------------------------------------------------

# YAML - Requires PyYAML
try:
    import yaml

    def _yaml_encoder(obj: Any) -> bytes:
        """Encode object to YAML."""
        return yaml.dump(obj, default_flow_style=False, allow_unicode=True).encode(
            "utf-8"
        )

    def _yaml_decoder(data: bytes) -> Any:
        """Decode YAML to Python object."""
        return yaml.safe_load(data.decode("utf-8"))

    register_codec(
        ".yaml", encoder=_yaml_encoder, decoder=_yaml_decoder, dependency="pyyaml"
    )
    register_codec(
        ".yml", encoder=_yaml_encoder, decoder=_yaml_decoder, dependency="pyyaml"
    )
except ImportError:
    pass

# ENV - Environment files (requires python-dotenv for full support)
try:
    from dotenv import dotenv_values

    def _env_encoder(obj: dict) -> bytes:
        """Encode dict to .env format."""
        lines = []
        for key, value in obj.items():
            # Quote values with spaces or special chars
            if isinstance(value, str) and (
                " " in value or '"' in value or "'" in value
            ):
                value = f'"{value}"'
            lines.append(f"{key}={value}")
        return "\n".join(lines).encode("utf-8")

    def _env_decoder(data: bytes) -> dict:
        """Decode .env file to dict."""
        # Write to temp StringIO for dotenv_values
        return dotenv_values(stream=io.StringIO(data.decode("utf-8")))

    register_codec(
        ".env", encoder=_env_encoder, decoder=_env_decoder, dependency="python-dotenv"
    )
except ImportError:
    # Fallback simple .env parser without dotenv
    def _env_encoder_simple(obj: dict) -> bytes:
        """Simple .env encoder without python-dotenv."""
        lines = []
        for key, value in obj.items():
            if isinstance(value, str) and (
                " " in value or '"' in value or "'" in value
            ):
                value = f'"{value}"'
            lines.append(f"{key}={value}")
        return "\n".join(lines).encode("utf-8")

    def _env_decoder_simple(data: bytes) -> dict:
        """Simple .env decoder without python-dotenv."""
        result = {}
        for line in data.decode("utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    result[key] = value
        return result

    register_codec(".env", encoder=_env_encoder_simple, decoder=_env_decoder_simple)

# JSON5 - More lenient JSON (requires json5 package)
try:
    import json5

    register_codec(
        ".json5",
        encoder=lambda obj: json5.dumps(obj, indent=2).encode("utf-8"),
        decoder=lambda data: json5.loads(data.decode("utf-8")),
        dependency="json5",
    )
except ImportError:
    pass

# Properties files (Java-style)
try:
    from jproperties import Properties

    def _properties_encoder(obj: dict) -> bytes:
        """Encode dict to .properties format."""
        props = Properties()
        for key, value in obj.items():
            props[key] = str(value)
        output = io.BytesIO()
        props.store(output, encoding="utf-8")
        return output.getvalue()

    def _properties_decoder(data: bytes) -> dict:
        """Decode .properties file to dict."""
        props = Properties()
        props.load(io.BytesIO(data), encoding="utf-8")
        return {k: v.data for k, v in props.items()}

    register_codec(
        ".properties",
        encoder=_properties_encoder,
        decoder=_properties_decoder,
        dependency="jproperties",
    )
except ImportError:
    # Fallback simple properties parser
    def _properties_encoder_simple(obj: dict) -> bytes:
        """Simple .properties encoder."""
        lines = []
        for key, value in obj.items():
            # Escape special characters
            value_str = str(value).replace("\\", "\\\\").replace("\n", "\\n")
            lines.append(f"{key}={value_str}")
        return "\n".join(lines).encode("utf-8")

    def _properties_decoder_simple(data: bytes) -> dict:
        """Simple .properties decoder."""
        result = {}
        for line in data.decode("utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("!"):
                if "=" in line or ":" in line:
                    # Support both = and : as separators
                    sep = "=" if "=" in line else ":"
                    key, _, value = line.partition(sep)
                    key = key.strip()
                    value = value.strip()
                    # Unescape
                    value = value.replace("\\n", "\n").replace("\\\\", "\\")
                    result[key] = value
        return result

    register_codec(
        ".properties",
        encoder=_properties_encoder_simple,
        decoder=_properties_decoder_simple,
    )
