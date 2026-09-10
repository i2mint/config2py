# config2py.s_configparser

Data Object Layer for configparser standard lib.

### Functions

| `persist_after_operation`(method_func)                                                     |                                                                                                               |
|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| [`postprocess_ini_section_items`](#config2py.s_configparser.postprocess_ini_section_items)(items)      | Transform newline-separated string values into actual list of strings (assuming that intent)                  |
| [`preprocess_ini_section_items`](#config2py.s_configparser.preprocess_ini_section_items)(items)       | Transform list values into newline-separated strings, in view of writing the value to a ini formatted section |
| [`super_and_persist`](#config2py.s_configparser.super_and_persist)(super_cls, method_name) | To be able to do this:                                                                                        |

### Classes

| [`ConfigReader`](#config2py.s_configparser.ConfigReader)([defaults, dict_type, ...])   | A KvReader to read config files                  |
|---------------------------------------------------------------------------------------------|--------------------------------------------------|
| [`ConfigStore`](#config2py.s_configparser.ConfigStore)([defaults, dict_type, ...])    | Persister (read, write, delete) for ini configs. |

### *class* config2py.s_configparser.ConfigReader(defaults=None, dict_type=<class 'dict'>, allow_no_value=False, \*, delimiters=('=', ': '), comment_prefixes=('#', ';'), inline_comment_prefixes=None, strict=True, empty_lines_in_values=True, default_section='DEFAULT', interpolation=<object object>, converters=<object object>)

Bases: [`ConfigStore`](#config2py.s_configparser.ConfigStore)

A KvReader to read config files

```pycon
>>> from config2py.s_configparser import ConfigReader
>>>
>>> # from a (pretend) file
>>> from io import BytesIO, StringIO
>>> file_content_bytes = b'''
... [Paths]
... home_dir: /Users
... my_dir: %(home_dir)s/lumberjack
... my_pictures: %(my_dir)s/Pictures
...
... [Escape]
... gain: 80%%  # use a %% to escape the % sign (% is the only character that needs to be escaped)'''
>>> c = ConfigReader(file_content_bytes)  # get configs from the bytes
>>> list(c)
['DEFAULT', 'Paths', 'Escape']
>>> ######## From a (pretend) file (pointer) ########
>>> # Usually, you write your configs in a file and give ConfigReader the filepath, or open file pointer...
>>> pretend_file_pointer = StringIO(file_content_bytes.decode())
>>> c = ConfigReader(pretend_file_pointer)
>>> list(c)
['DEFAULT', 'Paths', 'Escape']
>>> c['Paths']  # gives you a configparser.Section object
<Section: Paths>
>>> # A configparser.Section is a mapping. Let's see the keys
>>> list(c['Paths'])
['home_dir', 'my_dir', 'my_pictures']
```

# >>> # here’s a quick way to see both keys and values. Note how the home_dir interpolation was performed!
# >>> dict(c[‘Paths’])
# {‘home_dir’: ‘/Users’, ‘my_dir’: ‘/Users/lumberjack’, ‘my_pictures’: ‘/Users/lumberjack/Pictures’}

```pycon
>>>
>>> ######## Get configs from a dict ########
>>> config_dict = {'section1': {'key1': 'value1'},
...                'section2': {'keyA': 'valueA', 'keyB': 'valueB'},
...                'section3': {'foo': 'x', 'bar': 'y','baz': 'z'}}
>>> c = ConfigReader(config_dict)
>>>
>>> assert list(c) == ['DEFAULT', 'section1', 'section2', 'section3']
>>> assert list(c['section3']) == ['foo', 'bar', 'baz']
>>>
>>> ######## Get configs from a string ########
>>> from config2py.s_configparser import _test_config_str
>>> c = ConfigReader(_test_config_str, allow_no_value=True)
>>> list(c)
['DEFAULT', 'Simple Values', 'All Values Are Strings', 'Multiline Values', 'No Values', 'You can use comments', 'Sections Can Be Indented']
>>> list(c['Simple Values'])
['key', 'spaces in keys', 'spaces in values', 'spaces around the delimiter', 'you can also use']
```

#### persist()

Persists the data (if not in a context manager).
Persists means to call

### *class* config2py.s_configparser.ConfigStore(defaults=None, dict_type=<class 'dict'>, allow_no_value=False, \*, delimiters=('=', ': '), comment_prefixes=('#', ';'), inline_comment_prefixes=None, strict=True, empty_lines_in_values=True, default_section='DEFAULT', interpolation=<object object>, converters=<object object>)

Bases: `Store`

Persister (read, write, delete) for ini configs.

You can read ini formated configurations with ConfigStore (though if you want to
just read, you should use ConfigReader instead – since ConfigReader disables
write and delete operations.

See ConfigReader for more examples of how to use ConfigStore.
We’ll mainly focus on write and delete operations here.

```pycon
>>> import os
>>> from config2py.s_configparser import ConfigStore, ConfigReader
>>> import tempfile
>>> temp_dir_path = tempfile.TemporaryDirectory().name
>>> if not os.path.exists(temp_dir_path):
...     os.makedirs(temp_dir_path)
>>> ini_filepath = os.path.join(temp_dir_path, 'config_store_test.ini')
>>> if os.path.isfile(ini_filepath):
...     os.remove(ini_filepath)
>>>
>>> os.path.isfile(ini_filepath)  # File doesn't exist
False
>>>
>>> s = ConfigStore(ini_filepath)
>>> list(s)  # There's always a default (by default empty)
['DEFAULT']
>>>
>>> os.path.isfile(ini_filepath)  # But the file still doesn't exist (the DEFAULT is virtual)
False
>>>
>>> # Now let's make a config
>>> s['nothing'] = {'special': 'about', 'number': 42}
>>> list(s)
['DEFAULT', 'nothing']
>>>
>>> os.path.isfile(ini_filepath)  # But NOW the file exists (ConfigStore will automatically write to file)
True
>>> s['add'] = {'more': 'sections'}
>>> list(s)
['DEFAULT', 'nothing', 'add']
```

```pycon
>>> # and yes, that config can now be read
>>> config_reader = ConfigReader(ini_filepath)
>>> list(config_reader)
['DEFAULT', 'nothing', 'add']
>>>
>>> config_reader['nothing']
<Section: nothing>
>>>
>>> dict(config_reader['nothing'])  # note that 42 is now a string (that's the ini format for you!)
{'special': 'about', 'number': '42'}
>>> dict(config_reader['DEFAULT'])  # and DEFAULT is empty
{}
```

You can delete sections

```pycon
>>> del s['add']
```

But you’ll need to refresh your reader to see the effect.

```pycon
>>> list(config_reader)
['DEFAULT', 'nothing', 'add']
>>> config_reader = ConfigReader(ini_filepath)
>>> list(config_reader)
['DEFAULT', 'nothing']
```

You can use `update` to write several sections at the same time.
Note that existing sections will be completely overwritten.

```pycon
>>> s.update({'nothing': {'like': 'you'}, 'new_section': {'a': 'b', 'c': 'd'}})
>>> ConfigReader(ini_filepath).to_dict()
{'DEFAULT': {}, 'nothing': {'like': 'you'}, 'new_section': {'a': 'b', 'c': 'd'}}
```

**Warning: On the other hand, updating a section will not persist the updates**

Updates are automatically persisted at the top level, as shown in the example above.
This means you can change a section entirely, but partial updates of a section
will not be persisted.

You’ll see the updated section in the store.

```pycon
>>> s['nothing'].update({'something': 'else'})
>>> dict(s['nothing'])
{'like': 'you', 'something': 'else'}
```

But it’s not automatically persisted

```pycon
>>> dict(ConfigReader(ini_filepath)['nothing'])
{'like': 'you'}
```

… unless you ask for it explicitly

```pycon
>>> s.persist()
>>> dict(ConfigReader(ini_filepath)['nothing'])
{'like': 'you', 'something': 'else'}
```

### TODO: Could make section updates auto-persistent by wrapping configparser.SectionProxy

For your convenience, the ConfigStore is also a context manager, that will,
you guessed, persist stuff when (and only when) you exit it.

```pycon
>>> ConfigReader(ini_filepath).to_dict()
{'DEFAULT': {}, 'nothing': {'like': 'you', 'something': 'else'}, 'new_section': {'a': 'b', 'c': 'd'}}
>>> with ConfigStore(ini_filepath) as s:
...     del s['new_section']  # that's usually immediately persisted. This time, it'll wait to be
...     del s['nothing']['something']  # delete the something field of nothing section
...     s['nothing'].update({'like': 'that', 'ever': 'happened'})  # update 'like' config and add an 'ever' one
>>> ConfigReader(ini_filepath).to_dict()
{'DEFAULT': {}, 'nothing': {'like': 'that', 'ever': 'happened'}}
```

#### *class* BasicInterpolation

Bases: `Interpolation`

Interpolation as implemented in the classic ConfigParser.

The option values can contain format strings which refer to other values in
the same section, or values in the special default section.

For example:

> something: %(dir)s/whatever

would resolve the “%(dir)s” to the value of dir.  All reference
expansions are done late, on demand. If a user needs to use a bare % in
a configuration file, she can escape it by writing %%. Other % usage
is considered a user error and raises `InterpolationSyntaxError`.

#### *class* ExtendedInterpolation

Bases: `Interpolation`

Advanced variant of interpolation, supports the syntax used by
`zc.buildout`. Enables interpolation between sections.

#### get(k, default=None)

Needed because the Store.get didn’t catch the NoSectionError

#### persist()

Persists the data (if not in a context manager).
Persists means to call

### config2py.s_configparser.postprocess_ini_section_items(items)

Transform newline-separated string values into actual list of strings (assuming that intent)

* **Return type:**
  [`Generator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Generator)

```pycon
>>> section_from_ini = {
...     'name': 'aspyre',
...     'keywords': '\n\tdocumentation\n\tpackaging\n\tpublishing'
... }
>>> section_for_python = dict(postprocess_ini_section_items(section_from_ini))
>>> section_for_python
{'name': 'aspyre', 'keywords': ['documentation', 'packaging', 'publishing']}
```

### config2py.s_configparser.preprocess_ini_section_items(items)

Transform list values into newline-separated strings, in view of writing the value to a ini formatted section

* **Return type:**
  [`Generator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Generator)

```pycon
>>> section = {
...     'name': 'aspyre',
...     'keywords': ['documentation', 'packaging', 'publishing']
... }
>>> for_ini = dict(preprocess_ini_section_items(section))
>>> print('keywords =' + for_ini['keywords'])
keywords =
    documentation
    packaging
    publishing
```

### config2py.s_configparser.super_and_persist(super_cls, method_name)

To be able to do this:

```text
__setitem__ = super_and_persist(ConfigParser, '__setitem__')
__delitem__ = super_and_persist(ConfigParser, '__delitem__')
```

in your class definition block.

I thought I needed to wrap more method this way, but as it turns out, I might not,
so I prefer open code.
