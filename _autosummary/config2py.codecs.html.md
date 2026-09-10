# config2py.codecs

Extension-based codec registries for configuration file parsing.

This module provides a flexible pattern for encoding and decoding configuration files
based on their file extensions. It includes codecs for bytes <-> JSON-friendly Python types.

### Examples

```pycon
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
```

The module automatically registers codecs for standard formats (json, toml, ini, etc.)
and conditionally registers codecs that require third-party libraries (yaml, json5, etc.).

### Functions

| [`decode_by_extension`](#config2py.codecs.decode_by_extension)(key, data)                | Decode data based on key's extension.                |
|------------------------------------------------------------------------------------------------|------------------------------------------------------|
| [`encode_by_extension`](#config2py.codecs.encode_by_extension)(key, obj)                 | Encode object based on key's extension.              |
| [`get_extension`](#config2py.codecs.get_extension)(key)                            | Extract extension from a key (filename, path, etc.). |
| [`register_codec`](#config2py.codecs.register_codec)(extension, \*[, encoder, ...]) | Register encoder and/or decoder for an extension.    |
| [`register_decoder`](#config2py.codecs.register_decoder)(extension, \*[, overwrite])  | Decorator to register a decoder function.            |
| [`register_encoder`](#config2py.codecs.register_encoder)(extension, \*[, overwrite])  | Decorator to register an encoder function.           |
| [`list_registered_extensions`](#config2py.codecs.list_registered_extensions)()                  | List all registered extensions.                      |
| [`is_extension_registered`](#config2py.codecs.is_extension_registered)(extension)            | Check if an extension has any codec registered.      |
| [`get_codec_info`](#config2py.codecs.get_codec_info)(extension)                     | Get information about a registered codec.            |

### config2py.codecs.decode_by_extension(key, data)

Decode data based on key’s extension.

* **Parameters:**
  * **key** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Key or filename with extension
  * **data** ([`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes)) – Bytes to decode
* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)
* **Returns:**
  Decoded Python object
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If no decoder registered for extension

### Examples

```pycon
>>> data = b'{"key": "value"}'
>>> decode_by_extension('config.json', data)
{'key': 'value'}
```

### config2py.codecs.encode_by_extension(key, obj)

Encode object based on key’s extension.

* **Parameters:**
  * **key** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Key or filename with extension
  * **obj** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – Python object to encode
* **Return type:**
  [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes)
* **Returns:**
  Encoded bytes
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If no encoder registered for extension

### Examples

```pycon
>>> obj = {'key': 'value'}
>>> encoded = encode_by_extension('config.json', obj)
>>> assert b'"key"' in encoded
```

### config2py.codecs.get_codec_info(extension)

Get information about a registered codec.

* **Parameters:**
  **extension** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – File extension (with or without leading dot)
* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  Dictionary with codec information

### Examples

```pycon
>>> info = get_codec_info('.json')
>>> info['has_encoder']
True
>>> info['has_decoder']
True
```

### config2py.codecs.get_extension(key)

Extract extension from a key (filename, path, etc.).

* **Parameters:**
  **key** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – A string that may contain a file extension
* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)
* **Returns:**
  Extension without the dot, or empty string if no extension found

### Examples

```pycon
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
```

### config2py.codecs.is_extension_registered(extension)

Check if an extension has any codec registered.

* **Parameters:**
  **extension** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – File extension (with or without leading dot)
* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)
* **Returns:**
  True if decoder or encoder is registered

### Examples

```pycon
>>> is_extension_registered('.json')
True
>>> is_extension_registered('.nonexistent')
False
```

### config2py.codecs.list_registered_extensions()

List all registered extensions.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]
* **Returns:**
  Sorted list of registered extensions

### Examples

```pycon
>>> extensions = list_registered_extensions()
>>> '.json' in extensions
True
```

### config2py.codecs.register_codec(extension, , encoder=None, decoder=None, overwrite=False, dependency=None)

Register encoder and/or decoder for an extension.

* **Parameters:**
  * **extension** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – File extension (with or without leading dot)
  * **encoder** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes)]]) – Function to encode objects to bytes
  * **decoder** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`bytes`](https://docs.python.org/3/library/stdtypes.html#bytes)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – Function to decode bytes to objects
  * **overwrite** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Whether to overwrite existing codec
  * **dependency** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]) – Optional package name required for this codec
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If codec already registered and overwrite=False

### Examples

```pycon
>>> def my_encoder(obj): return str(obj).encode()
>>> def my_decoder(data): return eval(data.decode())
>>> register_codec('.custom', encoder=my_encoder, decoder=my_decoder, overwrite=True)
```

### config2py.codecs.register_decoder(extension, , overwrite=False)

Decorator to register a decoder function.

* **Parameters:**
  * **extension** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – File extension (with or without leading dot)
  * **overwrite** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Whether to overwrite existing decoder
* **Returns:**
  Decorator function

### Examples

```pycon
>>> @register_decoder('.custom', overwrite=True)
... def decode_custom(data: bytes) -> dict:
...     return {'data': data.decode()}
```

### config2py.codecs.register_encoder(extension, , overwrite=False)

Decorator to register an encoder function.

* **Parameters:**
  * **extension** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – File extension (with or without leading dot)
  * **overwrite** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Whether to overwrite existing encoder
* **Returns:**
  Decorator function

### Examples

```pycon
>>> @register_encoder('.custom', overwrite=True)
... def encode_custom(obj: dict) -> bytes:
...     return obj.get('data', '').encode()
```
