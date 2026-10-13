"""
Utility functions for config2py.

"""

import re
import errno
import os
import stat
import sys
import ast
from collections import ChainMap, namedtuple
from pathlib import Path
from functools import partial
from typing import Optional, Union, Any, Set, Literal, get_args
from collections.abc import Callable
from types import SimpleNamespace
import getpass

from dol import process_path

from i2 import mk_sentinel  # TODO: Only i2 dependency. Consider replacing.

# def mk_sentinel(name):  # TODO: Only i2 dependency. Here's replacement, but not picklable
#     return type(name, (), {'__repr__': lambda self: name})()

DFLT_APP_NAME = "config2py"

SECRET_LOOKING_PATTERN = re.compile(
    r"secret|token|pass|pwd|api|key|credential|auth|private", re.IGNORECASE
)


def looks_like_secret(text: str) -> bool:
    """True if ``text`` (typically a prompt naming a config key) looks secret.

    It errs on the side of masking: a false positive only means the user doesn't see
    what they type, while a false negative echoes a secret to the terminal. It is a
    plain substring match on the whole prompt, so ``KEYS_DIR`` or ``AUTHOR`` also
    match, as would a custom prompt template mentioning "key". Pass an explicit
    ``mask_input`` (or your own predicate) when that matters.

    >>> looks_like_secret("Enter a value for OPENAI_API_KEY: ")
    True
    >>> looks_like_secret("Enter a value for github_token: ")
    True
    >>> looks_like_secret("Enter a value for DATA_DIR: ")
    False
    """
    return bool(SECRET_LOOKING_PATTERN.search(text))


# The default for ``ask_user_for_input``'s ``mask_input``: either a bool, or a
# ``prompt -> bool`` predicate deciding per prompt. Masking only secret-looking prompts
# (rather than all of them) keeps non-secret values, such as the file paths the
# README suggests storing, visible while being typed (see i2mint/config2py#13).
DFLT_MASKING_INPUT = looks_like_secret

not_found = mk_sentinel("not_found")
no_default = mk_sentinel("no_default")


def owner_only_opener(path, flags, *, follow_symlinks=True, dir_fd=None):
    """An ``opener`` for ``open`` that creates (or re-tightens) ``path`` as ``0o600``.

    With ``follow_symlinks=False`` a symlink at ``path`` is refused (``OSError``,
    ``ELOOP``) instead of followed -- through ``O_NOFOLLOW`` where the platform has
    it (which only covers the last path component), else by an ``islink`` check; a file
    with several hard links is refused too, and left untouched. ``dir_fd`` makes
    ``path`` relative to that open folder (POSIX; see ``secure_open``'s ``beneath``).
    Opening a symlink *you* control is fine; one planted by someone else in a folder
    they can write to would redirect (and ``chmod``) a file of theirs choosing
    (see https://github.com/i2mint/config2py/issues/45).

    - *New* file: the restrictive mode is applied atomically at creation via
      ``os.open``, so there is no window where the file briefly exists with the
      process's default umask (commonly world-readable, ``0o644``).
    - *Pre-existing* file with looser permissions: ``os.open``'s ``mode`` argument
      is a POSIX no-op in this case (only consulted when a new file is actually
      created), so an explicit ``os.fchmod`` re-tightens it -- on the open file
      descriptor, not the path, so it's not subject to a TOCTOU swap either.
    """
    truncate = False
    if not follow_symlinks:
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        elif dir_fd is None and os.path.islink(path):  # Windows: no O_NOFOLLOW
            raise OSError(errno.ELOOP, "Refusing to follow a symlink", os.fspath(path))
        # Truncate only after checking for a hardlink (a second name for a file
        # someone else chose), so refusing it leaves the file intact.
        truncate = bool(flags & os.O_TRUNC)
        flags &= ~os.O_TRUNC
    fd = os.open(path, flags, 0o600, dir_fd=dir_fd)
    try:
        if not follow_symlinks:
            if os.fstat(fd).st_nlink > 1:
                raise OSError(
                    errno.EMLINK, "Refusing a file with several hard links", path
                )
            if truncate:
                os.ftruncate(fd, 0)
    except BaseException:
        os.close(fd)
        raise
    if hasattr(os, "fchmod"):  # POSIX only -- Windows ACLs aren't unix mode bits
        try:
            os.fchmod(fd, 0o600)  # re-tighten if the file already existed
        except BaseException:
            os.close(fd)
            raise
    return fd


def secure_open(path, mode="w", *, follow_symlinks=True, beneath=None, **open_kwargs):
    """``open(path, mode, **open_kwargs)`` with owner-only (``0o600``) permissions.

    The file is created (or re-tightened) by ``owner_only_opener``. Being the builtin
    ``open``, it honors ``encoding``, ``newline``, and binary modes (``O_BINARY`` on
    Windows). Pass ``encoding=`` explicitly for text: the default is the locale's.

    The ``mode`` is honored as is (``"a"`` appends; before #35 every mode truncated).
    Any mode, including ``"r"``, sets the file's permissions to ``0o600``.

    A symlink at ``path`` is followed (like ``open``) unless ``follow_symlinks=False``,
    which raises ``OSError`` instead (see ``owner_only_opener``). With
    ``follow_symlinks=False`` and ``beneath=<folder>`` (a folder ``path`` is inside),
    a symlink at *any* folder between ``beneath`` and the file is refused too (not
    ``beneath`` itself, nor the folders above it: those are yours to choose). On POSIX
    each folder is opened relative to its parent with ``O_NOFOLLOW``, so the check
    can't be raced; elsewhere it is an ``islink`` check
    (see https://github.com/i2mint/config2py/issues/51).

    Intended for files that may hold secrets (see i2mint/config2py#15).

    >>> import tempfile, os
    >>> path = tempfile.mktemp()
    >>> with secure_open(path, "w") as f:
    ...     _ = f.write("secret")
    >>> # Unix mode bits aren't meaningful on Windows -- os.stat there reports 0o666
    >>> # regardless of what secure_open does, so only assert the mode on POSIX.
    >>> oct(os.stat(path).st_mode & 0o777) if os.name == "posix" else "0o600"
    '0o600'
    >>> os.remove(path)
    """
    if follow_symlinks or beneath is None:
        opener = owner_only_opener
        if not follow_symlinks:
            opener = partial(owner_only_opener, follow_symlinks=False)
        return open(path, mode, opener=opener, **open_kwargs)
    return _open_beneath(path, mode, beneath, open_kwargs)


def _open_beneath(path, mode, beneath, open_kwargs):
    """``secure_open(path, follow_symlinks=False, beneath=beneath)``."""
    if os.fspath(path).endswith((os.sep, os.altsep or os.sep)):
        raise IsADirectoryError(errno.EISDIR, "Not a file path", os.fspath(path))
    relative = os.path.relpath(os.path.abspath(path), os.path.abspath(beneath))
    parts = relative.split(os.sep)
    if parts[0] == os.pardir:
        raise ValueError(f"{os.fspath(path)!r} is not inside {os.fspath(beneath)!r}")
    *folders, name = parts
    if not (hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd):
        folder = os.path.abspath(beneath)  # no dir_fd (Windows): check, then open
        for part in folders:
            folder = os.path.join(folder, part)
            if os.path.islink(folder) or getattr(os.path, "isjunction", bool)(folder):
                raise OSError(errno.ELOOP, "Refusing to follow a symlink", folder)
        return open(
            path,
            mode,
            opener=partial(owner_only_opener, follow_symlinks=False),
            **open_kwargs,
        )
    # O_PATH (Linux): walking a folder needs only search permission, not read
    dir_flags = getattr(os, "O_PATH", os.O_RDONLY) | os.O_NOFOLLOW
    dir_flags |= getattr(os, "O_DIRECTORY", 0)
    dir_fd = os.open(os.path.abspath(beneath), dir_flags & ~os.O_NOFOLLOW)
    try:
        for part in folders:  # ``part`` is a symlink => OSError (ELOOP / ENOTDIR)
            next_fd = os.open(part, dir_flags, dir_fd=dir_fd)
            os.close(dir_fd)
            dir_fd = next_fd
        opener = partial(owner_only_opener, follow_symlinks=False, dir_fd=dir_fd)
        return open(name, mode, opener=opener, **open_kwargs)
    finally:
        os.close(dir_fd)


def tighten_mode(path, mode, *, strict=False) -> bool:
    """Set ``path``'s permission bits to ``mode``, only if they differ. POSIX only.

    Returns ``True`` if ``path`` ends up with ``mode``. A failing ``chmod`` (read-only
    file system, a path owned by someone else) raises if ``strict``, and otherwise
    only warns and returns ``False``: tightening is best-effort hardening, and must not
    make, for example, ``import config2py`` crash
    (see https://github.com/i2mint/config2py/issues/35).
    """
    if os.name != "posix":
        return True
    try:
        if os.stat(path).st_mode & 0o777 == mode:
            return True
        os.chmod(path, mode)
        return True
    except OSError as error:
        if strict:
            raise
        _warn_not_tightened(f"{path!r} to {oct(mode)}: {error}")
        return False


def _warn_not_tightened(what):
    import warnings
    from config2py.errors import Config2PyWarning

    warnings.warn(
        f"config2py could not tighten the permissions of {what}",
        Config2PyWarning,
        stacklevel=3,
    )


def secure_makedirs(dirpath, *, exist_ok=True):
    """``os.makedirs(dirpath, mode=0o700)``, re-tightening the mode if it already exists.

    ``os.makedirs(..., mode=0o700, exist_ok=True)`` alone won't re-tighten an existing
    directory's mode, so this follows up with ``tighten_mode`` (which warns, rather
    than raises, if that isn't possible). Intended for directories that may hold
    config/secret files (see i2mint/config2py#15).
    """
    os.makedirs(dirpath, mode=0o700, exist_ok=exist_ok)
    tighten_mode(dirpath, 0o700)


_warned_unsafe_folders: Set[str] = set()  # each folder is warned about once


def _is_private_group(gid: int) -> bool:
    """True if only the current user is in group ``gid`` (a "user-private group", as on
    Debian-style systems, where a ``umask 002`` makes every folder group-writable).
    Without the ``grp``/``pwd`` modules (not POSIX), nothing is private."""
    try:
        import grp
        import pwd

        me = pwd.getpwuid(os.geteuid()).pw_name
        members = set(grp.getgrgid(gid).gr_mem) - {me}
        primary_of_others = {p.pw_name for p in pwd.getpwall() if p.pw_gid == gid} - {
            me
        }
        return gid in (os.getegid(), *os.getgroups()) and not (
            members or primary_of_others
        )
    except (ImportError, KeyError, OSError):
        return False


def _loose_permissions(st) -> bool:
    """True if ``st`` (a folder's ``os.stat``) is writable by its group or by others."""
    return bool(
        st.st_mode & stat.S_IWOTH
        or (st.st_mode & stat.S_IWGRP and not _is_private_group(st.st_gid))
    )


def _ancestor_problem(dirpath) -> Optional[str]:
    """The first ancestor of ``dirpath`` (symlinks resolved) that another user could
    use to swap the folder for a symlink, or ``None``. Like ssh's ``StrictModes``,
    which checks every folder up to the root. A sticky folder (``/tmp``) is fine
    even if others can write to it: they can't rename or remove entries they
    don't own. An ancestor on another filesystem than the folder (the other side of
    a mount point, e.g. a host user's folder bind-mounted into a container, seen by
    root) is only checked for being writable, not for being owned by another user
    (see https://github.com/i2mint/config2py/issues/56)."""
    ancestor = os.path.realpath(dirpath)
    try:
        folder_dev = os.stat(ancestor).st_dev
    except OSError:
        folder_dev = None
    while True:
        parent = os.path.dirname(ancestor)
        if parent == ancestor:
            return None
        ancestor = parent
        try:
            st = os.stat(ancestor)
        except OSError:
            continue
        problems = []
        across_mount = folder_dev is not None and st.st_dev != folder_dev
        if st.st_uid not in (os.geteuid(), 0) and not across_mount:
            problems.append("owned by another user")
        if _loose_permissions(st) and not st.st_mode & stat.S_ISVTX:
            problems.append("writable by its group or by others")
        if problems:
            return f"under {ancestor!r}, which is {' and '.join(problems)}"


def unsafe_folder_reason(
    dirpath, *, check_ancestors: bool = True, ignore_sticky: bool = False
) -> Optional[str]:
    """Why a folder isn't safe to keep secrets in, or ``None`` if it looks fine.

    Like ssh's ``StrictModes``: a folder owned by someone other than the current user
    (or root), or writable by its group or by others, lets those users plant a
    symlink or a file there to redirect or read what config2py writes. A group the
    current user is alone in does not count as "its group". With ``check_ancestors``
    (the default) the folders above it are checked the same way (those who can write
    to a parent can swap the folder itself for a symlink), except that a sticky
    parent, such as ``/tmp``, is fine, and a parent on another filesystem than the
    folder is not checked for its owner. ``ignore_sticky`` also accepts the folder
    itself being sticky (as ``/tmp`` is), for a file kept directly in a shared folder.
    POSIX only (``None`` elsewhere); a missing folder is ``None`` too.

    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:  # created 0o700
    ...     unsafe_folder_reason(d, check_ancestors=False)
    >>> unsafe_folder_reason("/no/such/folder")
    """
    if not hasattr(os, "geteuid"):
        return None
    try:
        st = os.stat(dirpath)
    except OSError:
        return None
    problems = []
    if st.st_uid not in (os.geteuid(), 0):
        problems.append("owned by another user")
    if _loose_permissions(st) and not (ignore_sticky and st.st_mode & stat.S_ISVTX):
        problems.append("writable by its group or by others")
    if problems:
        return " and ".join(problems)
    return _ancestor_problem(dirpath) if check_ancestors else None


def check_folder_is_private(
    dirpath,
    *,
    on_unsafe: str = "warn",
    stacklevel: int = 2,
    check_ancestors: bool = True,
    ignore_sticky: bool = False,
):
    """Check ``dirpath`` with ``unsafe_folder_reason``, and act on a problem.

    :param on_unsafe: ``"warn"`` (the default) issues an
        ``InsecureConfigFolderWarning`` (once per folder), ``"raise"`` raises
        ``PermissionError``, ``"ignore"`` skips the check. Fix a folder you own with
        ``chmod 700``
        (see https://github.com/i2mint/config2py/issues/45).
    :param check_ancestors: Also check the folders above ``dirpath``.
    :param ignore_sticky: Accept ``dirpath`` itself being sticky (like ``/tmp``).
    """
    from config2py.errors import InsecureConfigFolderWarning, validate_on_missing

    validate_on_missing(on_unsafe, name="on_unsafe")  # the options of ``on_missing``
    if on_unsafe == "ignore":
        return
    key = os.path.realpath(dirpath)
    if on_unsafe == "warn" and key in _warned_unsafe_folders:
        return  # warned once already: don't look again
    reason = unsafe_folder_reason(
        dirpath, check_ancestors=check_ancestors, ignore_sticky=ignore_sticky
    )
    if reason is None:
        return
    msg = (
        f"Config folder {os.fspath(dirpath)!r} is {reason}, so others could plant "
        "a symlink or file there and redirect or read the values stored in it. "
        "Use a folder only you can write to (chmod 700), or pass "
        "on_unsafe_folder='ignore' if this is intended."
    )
    if on_unsafe == "raise":
        raise PermissionError(msg)
    if key not in _warned_unsafe_folders:
        import warnings

        warnings.warn(msg, InsecureConfigFolderWarning, stacklevel=stacklevel + 1)
        _warned_unsafe_folders.add(key)  # after the warn: under -W error it can repeat


def always_true(x: Any) -> bool:
    """Function that just returns True."""
    return True


def identity(x: Any) -> Any:
    """Function that just returns its argument."""
    return x


def is_not_empty(x: Any) -> bool:
    """Function that returns True if x is not empty."""
    return bool(x)


# Note: Why subclassing ChainMap works, but subclassing dict doesn't.
# The `EnvironmentVariables` class inherits from `collections.ChainMap` and wraps
# `os.environ`, providing a dynamic view of the environment variables without exposing
# sensitive data. Unlike a regular `dict` copy, which creates a static snapshot,
# `ChainMap` maintains a live reference to `os.environ`, so any changes to the
# environment—whether through `os.environ['KEY'] = 'value'` or external updates—are
# immediately reflected in `EnvironmentVariables`. Overriding `__repr__` ensures that
# printing the object (e.g., in a REPL or log) hides the actual contents,
# preserving confidentiality while retaining full read/write functionality.
class EnvironmentVariables(ChainMap):
    """
    Class to wrap environment variables, hiding values from ``repr``/``print`` only.

    ``__repr__`` is overridden to avoid printing secrets to a REPL or log, but values
    are still reachable through normal ``Mapping`` operations -- ``dict(envvar)``,
    ``envvar.items()``/``.values()``, ``pickle.dumps(envvar)``, or a structured logger
    that walks the mapping. Treat this as UI-level redaction, not access control (see
    i2mint/config2py#16).
    """

    def __init__(self):
        """Wrap ``os.environ`` as the (only) mapping in the chain."""
        super().__init__(os.environ)

    def __repr__(self):
        """Return a fixed, value-free label so secrets aren't printed."""
        return "EnvironmentVariables"


envvar = EnvironmentVariables()


def _stdin_is_a_terminal() -> bool:
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except (AttributeError, ValueError):  # exotic or closed stdin
        return False


def _inferred_masked_prompt_func() -> Callable[[str], str]:
    """The function to read a response with when masking was *inferred* by a predicate.

    The stdlib's ``getpass.getpass`` reads the controlling terminal, not ``sys.stdin``:
    with piped input it would ignore the pipe (or block waiting on the terminal).
    Before masking became the default for secret-looking prompts, such prompts read
    stdin with ``input``, so when stdin isn't a terminal we keep doing that (there's
    no terminal echo of piped data anyway). A ``getpass.getpass`` replaced by a
    frontend (e.g. Jupyter's masked widget, where stdin is never a terminal) is always
    used. An explicit ``mask_input=True`` doesn't come here: it always uses
    ``getpass.getpass``, which deliberately reads the terminal (like ``sudo``).
    """
    getpass_func = getpass.getpass
    is_stdlib_getpass = getattr(getpass_func, "__module__", None) == "getpass"
    if is_stdlib_getpass and not _stdin_is_a_terminal():
        return input
    return getpass_func


# TODO: Make this into an open-closed mini-framework
def ask_user_for_input(
    prompt: str,
    default: str = "",
    *,
    mask_input: bool | Callable[[str], bool] = DFLT_MASKING_INPUT,
    masking_toggle_str: str = None,
    egress: Callable = identity,
) -> str:
    """
    Ask the user for input, optionally masking, validating and transforming the input.

    :param prompt: Prompt to display to the user
    :param default: Default value to return if the user enters nothing
    :param mask_input: Whether to mask the user's input: a bool, or a
        ``prompt -> bool`` predicate. The default, ``looks_like_secret``, masks
        prompts that mention something secret-looking (``API_KEY``, ``TOKEN``,
        ``PASSWORD``, ...) and echoes the others. When masking is decided by a
        predicate and stdin is piped (not a terminal), the response is read from
        stdin, as it was before this default existed. An explicit ``True`` always
        uses ``getpass.getpass``, which reads the terminal even when stdin is piped.
    :param masking_toggle_str: String to toggle input masking. If ``None``, no toggle
        is available. If not ``None`` (a common choice is the empty string)
        the user can enter this string to toggle input masking.
    :param egress: Function to apply to the user's response before returning it.
        This can be used to validate the response, for example.
    :return: The user's response (or the default value if the user entered nothing)
    """
    masking_is_inferred = callable(mask_input)
    if masking_is_inferred:
        mask_input = bool(mask_input(prompt))
    _original_prompt = prompt
    if prompt[-1] != " ":  # pragma: no cover
        prompt = prompt + " "
    if masking_toggle_str is not None:
        prompt = (
            f"{prompt}\n"
            f"    (Input masking is {'ENABLED' if mask_input else 'DISABLED'}. "
            f"Enter '{masking_toggle_str}' (without quotes) to toggle input masking)\n"
        )
    if default not in {""}:
        prompt = prompt + f" [{default}]: "
    if mask_input:
        if masking_is_inferred:
            _prompt_func = _inferred_masked_prompt_func()
        else:
            _prompt_func = getpass.getpass
    else:
        _prompt_func = input

    response = _prompt_func(prompt)

    if masking_toggle_str is not None and response == masking_toggle_str:
        return ask_user_for_input(
            _original_prompt,
            default,
            mask_input=not mask_input,
            masking_toggle_str=masking_toggle_str,
        )

    return egress(response or default)


# Note: Could be made more efficient, but this is good enough (for now)
def extract_variable_declarations(
    string: str, expand: dict | bool | None = None
) -> dict:
    """
    Reads the contents of a config file, extracting Unix-style environment variable
    declarations of the form
    `export {NAME}={value}`, returning a dictionary of `{NAME: value, ...}` pairs.

    See issue for more info and applications:
    https://github.com/i2mint/config2py/issues/2

    :param string: String to extract variable declarations from
    :param expand: An optional dictionary of variable names and values to use to
        expand variables that are referenced (i.e. ``$NAME`` is a reference to ``NAME``
        variable) in the values of config variables.
        If ``True``, ``expand`` is replaced with an empty dictionary, which means we
        want to expand variables recursively, but we have no references to seed the
        expansion with. If ``False``, ``expand`` is replaced with ``None``, indicating
        that we don't want to expand any variables.

    :return: A dictionary of variable names and values.

    >>> config = 'export ENVIRONMENT="dev"\\nexport PORT=8080\\nexport DEBUG=true'
    >>> extract_variable_declarations(config)
    {'ENVIRONMENT': 'dev', 'PORT': '8080', 'DEBUG': 'true'}

    >>> config = 'export PATH="$PATH:/usr/local/bin"\\nexport EDITOR="nano"'
    >>> extract_variable_declarations(config)
    {'PATH': '$PATH:/usr/local/bin', 'EDITOR': 'nano'}

    The ``expand`` argument can be used to expand variables in the values of other.

    Let's add a reference to the ``PATH`` variable in the ``EDITOR`` variable:

    >>> config = 'export PATH="$PATH:/usr/local/bin"\\nexport EDITOR="nano $PATH"'

    If you specify a value for ``PATH`` in the ``expand`` argument, you'll see it
    reflected in the ``PATH`` variable (self reference) and the ``EDITOR`` variable.
    (Note if you changed the order of ``PATH`` and ``EDITOR`` in the ``config``,
    you wouldn't get the same thing though.)

    >>> extract_variable_declarations(config, expand={'PATH': '/root'})
    {'PATH': '/root:/usr/local/bin', 'EDITOR': 'nano /root:/usr/local/bin'}

    If you specify ``expand={}``, the first ``PATH`` variable will not be expanded,
    since PATH is not in the expand dictionary. But the second ``PATH`` variable,
    referenced in the definition of ``EDITOR`` will be expanded, since it is in the
    expand dictionary.

    >>> extract_variable_declarations(config, expand={})
    {'PATH': '$PATH:/usr/local/bin', 'EDITOR': 'nano $PATH:/usr/local/bin'}

    """
    if expand is True:
        # If expand is True, we'll use an empty dictionary as the expand dictionary
        # This means we want variables to be expanded recursively, but we have no
        # references to seed the expansion with.
        expand = {}
    elif expand is False:
        # If expand is False, we don't want to expand any variables.
        expand = None

    env_vars = {}
    pattern = re.compile(r"^export\s+([A-Za-z0-9_]+)=(.*)$")
    lines = string.split("\n")
    for line in lines:
        line = line.strip()
        match = pattern.match(line)
        if match:
            name = match.group(1)
            value = match.group(2).strip('"')
            if expand is not None:
                for key, val in expand.items():
                    value = value.replace(f"${key}", val)
                env_vars[name] = value
                expand = dict(expand, **env_vars)
            else:
                env_vars[name] = value
    return env_vars


def create_directories(dirpath, max_dirs_to_make=None):
    """
    Create directories up to a specified limit.

    Parameters:
        dirpath (str): The directory path to create.
        max_dirs_to_make (int, optional): The maximum number of directories to
            create. If None, there's no limit.

    Returns:
        bool: True if the directory was created successfully, False otherwise.

    Raises:
        ValueError: If max_dirs_to_make is negative.

    Examples:

        >>> import tempfile, shutil
        >>> temp_dir = tempfile.mkdtemp()
        >>> target_dir = os.path.join(temp_dir, 'a', 'b', 'c')
        >>> create_directories(target_dir, max_dirs_to_make=2)
        False
        >>> create_directories(target_dir, max_dirs_to_make=3)
        True
        >>> os.path.isdir(target_dir)
        True
        >>> shutil.rmtree(temp_dir)  # Cleanup

        >>> temp_dir = tempfile.mkdtemp()
        >>> target_dir = os.path.join(temp_dir, 'a', 'b', 'c', 'd')
        >>> create_directories(target_dir)
        True
        >>> os.path.isdir(target_dir)
        True
        >>> shutil.rmtree(temp_dir)  # Cleanup
    """
    if max_dirs_to_make is not None and max_dirs_to_make < 0:
        raise ValueError("max_dirs_to_make must be non-negative or None")

    if os.path.exists(dirpath):
        return True

    if max_dirs_to_make is None:
        secure_makedirs(dirpath)
        return True

    # Calculate the number of directories to create
    dirs_to_make = []
    current_path = dirpath

    while not os.path.exists(current_path):
        dirs_to_make.append(current_path)
        current_path, _ = os.path.split(current_path)

    if len(dirs_to_make) > max_dirs_to_make:
        return False

    # Create directories from the top level down
    for dir_to_make in reversed(dirs_to_make):
        os.mkdir(dir_to_make, mode=0o700)

    return True


#: Declarative description of where a given folder kind lives on a platform.
#:
#: ``env_var`` is the platform-standard environment variable that, when set,
#: names the *root* folder.  ``default_path`` is the root to use when that
#: variable is absent (``~`` is expanded).  ``subpath`` is a relative path
#: appended to the root; it exists because some platform standards place a
#: folder kind *inside* another kind's root rather than under its own variable
#: (e.g. Windows cache lives at ``%LOCALAPPDATA%\\Temp``).
FolderSpec = namedtuple(
    "FolderSpec", ["env_var", "default_path", "subpath"], defaults=("",)
)

#: Roots of the per-user Windows app folders, used when %APPDATA%/%LOCALAPPDATA%/
#: %TEMP% are absent (e.g. some service accounts). ``~`` is expanded at resolution
#: time. These are spelled as Windows literals on purpose: they describe the
#: Windows convention, so they must not be built with the *running* platform's
#: separator (that would produce '~/AppData/Roaming' when read from POSIX).
_WINDOWS_ROAMING_DEFAULT = r"~\AppData\Roaming"
_WINDOWS_LOCAL_DEFAULT = r"~\AppData\Local"
_WINDOWS_TEMP_DEFAULT = r"~\AppData\Local\Temp"


def app_folder_standards(os_name: str = os.name) -> dict:
    """Return the ``{folder_kind: FolderSpec}`` table for the given ``os.name``.

    This is the *single* place where config2py branches on the operating
    system: everything else consumes the returned table.  Exposing it as a
    function (rather than an ``if`` at import time) keeps the branch testable
    on any platform -- callers can ask for the table of an OS they are not
    running on.

    Args:
        os_name: An ``os.name`` value; ``"nt"`` selects the Windows standards,
            anything else selects the XDG Base Directory standards.

    >>> app_folder_standards("nt")["cache"]
    FolderSpec(env_var='LOCALAPPDATA', default_path='~\\\\AppData\\\\Local', subpath='Temp')
    >>> app_folder_standards("posix")["cache"]
    FolderSpec(env_var='XDG_CACHE_HOME', default_path='~/.cache', subpath='')
    """
    if os_name == "nt":
        return dict(
            config=FolderSpec("APPDATA", _WINDOWS_ROAMING_DEFAULT),
            data=FolderSpec("LOCALAPPDATA", _WINDOWS_LOCAL_DEFAULT),
            # Note the ``subpath``: %LOCALAPPDATA% is also the *data* root, so
            # cache must be a sub-folder of it -- otherwise clearing the cache
            # would wipe the user's data.
            cache=FolderSpec("LOCALAPPDATA", _WINDOWS_LOCAL_DEFAULT, "Temp"),
            state=FolderSpec("LOCALAPPDATA", _WINDOWS_LOCAL_DEFAULT),
            runtime=FolderSpec("TEMP", _WINDOWS_TEMP_DEFAULT),
        )
    return dict(
        config=FolderSpec("XDG_CONFIG_HOME", "~/.config"),
        data=FolderSpec("XDG_DATA_HOME", "~/.local/share"),
        cache=FolderSpec("XDG_CACHE_HOME", "~/.cache"),
        state=FolderSpec("XDG_STATE_HOME", "~/.local/state"),
        runtime=FolderSpec("XDG_RUNTIME_DIR", "/tmp"),
    )


APP_FOLDER_STANDARDS = app_folder_standards()


AppFolderKind = Literal["config", "data", "cache", "state", "runtime"]

# Verify AppFolderKind matches _APP_FOLDER_STANDARDS_DICT keys
# Note: This is due to the fact that static type checkers can't verify
# that the keys of _APP_FOLDER_STANDARDS_DICT match the Literal values.
# This breaks SSOT, but here we at least validate alignment at runtime.
_literal_kinds = get_args(AppFolderKind)
assert set(_literal_kinds) == set(APP_FOLDER_STANDARDS.keys()), (
    f"AppFolderKind Literal {_literal_kinds} doesn't match "
    f"APP_FOLDER_STANDARDS keys {tuple(APP_FOLDER_STANDARDS.keys())}"
)

config2py_env_var = SimpleNamespace(
    **{k: f"CONFIG2PY_{k.upper()}_DIR" for k in APP_FOLDER_STANDARDS}
)


DFLT_APP_FOLDER_KIND: AppFolderKind = "config"  # type: ignore (for <3.11)


def _absolute_path_from_env(name: str) -> Optional[str]:
    """The value of env var ``name`` if it is an absolute path (after ``~`` expansion).

    A blank or relative value counts as unset, as the XDG Base Directory spec says for
    ``XDG_*`` (i2mint/config2py#38): honoured, it would root config folders, secrets
    included, at the current working directory, often a project checkout.
    """
    value = (os.getenv(name) or "").strip()
    if not value:
        return None
    if not os.path.isabs(os.path.expanduser(value)):
        import warnings

        warnings.warn(
            f"Ignoring {name}={value!r}: it is not an absolute path, so it would put "
            "config folders (secrets included) under the current working directory.",
            stacklevel=3,
        )
        return None
    return value


def system_default_for_app_data_folder(
    folder_kind: AppFolderKind = DFLT_APP_FOLDER_KIND,  # type: ignore (for <3.11)
    *,
    standards: Optional[dict] = None,
) -> str:
    """Get the system default folder for ``folder_kind``.

    The root is the value of the platform's standard environment variable for
    that kind, falling back to the spec's ``default_path``; the spec's
    ``subpath`` (usually empty) is then appended.

    Args:
        folder_kind: One of 'config', 'data', 'cache', 'state', 'runtime'.
        standards: The ``{folder_kind: FolderSpec}`` table to resolve against.
            Defaults to the running platform's (``APP_FOLDER_STANDARDS``);
            pass another platform's table to resolve as that platform would.
    """
    if standards is None:
        standards = APP_FOLDER_STANDARDS
    env_var, default, subpath = standards[folder_kind]
    root = os.path.expanduser(_absolute_path_from_env(env_var) or default)
    return os.path.join(root, subpath) if subpath else root


DFLT_DATA_FOLDER = system_default_for_app_data_folder("data")
DFLT_CACHE_FOLDER = system_default_for_app_data_folder("cache")
DFLT_STATE_FOLDER = system_default_for_app_data_folder("state")
DFLT_RUNTIME_FOLDER = system_default_for_app_data_folder("runtime")


def get_app_rootdir(
    folder_kind: AppFolderKind = DFLT_APP_FOLDER_KIND,  # type: ignore (for <3.11)
    *,
    ensure_exists: bool = True,
) -> str:
    """
    Returns the root directory for a specific folder kind.

    The folder kind determines which standard directory is returned:

    - 'config': Configuration files (XDG_CONFIG_HOME, default ~/.config)
    - 'data': Application data (XDG_DATA_HOME, default ~/.local/share)
    - 'cache': Temporary/cache files (XDG_CACHE_HOME, default ~/.cache)
    - 'state': State data/logs (XDG_STATE_HOME, default ~/.local/state)
    - 'runtime': Runtime files (XDG_RUNTIME_DIR, default /tmp)

    On Windows:

    - 'config': %APPDATA%
    - 'data': %LOCALAPPDATA%
    - 'cache': %LOCALAPPDATA%\\Temp
    - 'state': %LOCALAPPDATA%
    - 'runtime': %TEMP%

    Args:
        folder_kind (str): The kind of folder to get. One of 'config', 'data', 'cache', 'state', 'runtime'.
            Defaults to 'config'.
            Here are concise explanations for each folder kind:
            **config**: User preferences and settings files (e.g., API keys, theme preferences, editor settings). Files users might edit manually or that define how the app behaves.
            **data**: Essential user-created content and application state (e.g., databases, saved games, user documents, session files). Data that should be backed up and persists across updates.
            **cache**: Temporary, regeneratable files (e.g., downloaded images, compiled assets, web cache). Can be safely deleted to free space without losing user work.
            **state**: Application state and logs that persist between sessions but aren't critical user data (e.g., command history, undo history, recently opened files, log files). Unlike cache, shouldn't be auto-deleted.
            **runtime**: Temporary runtime files that only exist while the app runs (e.g., PID files, Unix sockets, lock files, named pipes). Typically cleared on logout/reboot.
            **TL;DR**: config = settings, data = user files, cache = disposable, state = logs/history, runtime = process files.

        ensure_exists: Whether to create the directory if it doesn't exist

    Returns:
        str: The full path of the app root folder for the specified kind.

    Note: The default root folder follows XDG Base Directory standards on Unix/Linux/macOS.
    You can override this by setting environment variables:

    - CONFIG2PY_CONFIG_DIR, CONFIG2PY_DATA_DIR, CONFIG2PY_CACHE_DIR, etc.
      (highest priority, overrides everything, and works on **every** platform --
      see ``config2py_env_var`` for the full list of names)
    - The platform's own standard variable: XDG_CONFIG_HOME, XDG_DATA_HOME,
      XDG_CACHE_HOME, etc. on Unix/Linux/macOS; APPDATA / LOCALAPPDATA / TEMP on
      Windows. The XDG variables are a POSIX standard and are **not** consulted on
      Windows -- use the CONFIG2PY_* variables above for platform-neutral overrides.
    - If neither is set, uses platform defaults

    Examples:

        >>> get_app_rootdir('config')  # doctest: +SKIP
        '/Users/.../.config'
        >>> get_app_rootdir('data')  # doctest: +SKIP
        '/Users/.../.local/share'
        >>> get_app_rootdir('cache')  # doctest: +SKIP
        '/Users/.../.cache'
    """
    folderpath = (
        # Check config2py custom env var first (a blank or relative one counts as
        # unset, #38)
        _absolute_path_from_env(getattr(config2py_env_var, folder_kind))
        # ... if not, use system default
        or system_default_for_app_data_folder(folder_kind)
    )

    return process_path(folderpath, ensure_dir_exists=ensure_exists)


# renaming get_app_data_rootdir to get_app_rootdir
_legacy_app_data_rootdir = get_app_rootdir  # backwards compatibility alias


def _default_folder_setup(directory_path: str) -> None:
    """
    Create the given directory if it doesn't exist and initialize it
    with a hidden file for identification.

    Args:
        directory_path (str): Path to the directory to be initialized.

    Note:
        This is the default setup callback for directories managed by config2py.
    """
    if not os.path.isdir(directory_path):
        secure_makedirs(directory_path)
        # Add a hidden file to annotate the directory as one managed by config2py.
        # This helps distinguish it from directories created by other programs
        # (this can be useful to avoid conflicts).
        (Path(directory_path) / ".config2py").write_text("Created by config2py.")


def get_app_folder(
    app_name: str = DFLT_APP_NAME,
    *,
    setup_callback: Callable[[str], None] = _default_folder_setup,
    ensure_exists: bool = False,
    folder_kind: AppFolderKind = DFLT_APP_FOLDER_KIND,
) -> str:
    """
    Retrieve or create the app directory specific to the given app name and folder kind.

    The folder kind determines where the app's files are stored. Here are concise
    explanations for each folder kind:

    - **config**: User preferences and settings files (e.g., API keys, theme
      preferences, editor settings). Files users might edit manually or that
      define how the app behaves.
    - **data**: Essential user-created content and application state (e.g.,
      databases, saved games, user documents, session files). Data that should
      be backed up and persists across updates.
    - **cache**: Temporary, regeneratable files (e.g., downloaded images,
      compiled assets, web cache). Can be safely deleted to free space without
      losing user work.
    - **state**: Application state and logs that persist between sessions but
      aren't critical user data (e.g., command history, undo history, recently
      opened files, log files). Unlike cache, shouldn't be auto-deleted.
    - **runtime**: Temporary runtime files that only exist while the app runs
      (e.g., PID files, Unix sockets, lock files, named pipes). Typically
      cleared on logout/reboot.
    - **TL;DR**: config = settings, data = user files, cache = disposable,
      state = logs/history, runtime = process files.

    Args:
        app_name: Name of the app for which the directory is needed.
        setup_callback: A callback function to initialize the directory.
                       Default is _default_folder_setup.
        ensure_exists: Whether to ensure the directory exists.
        folder_kind: Type of folder ('config', 'data', 'cache', 'state', or 'runtime').
                    Default is 'config' for backward compatibility.

    Returns:
        str: Path to the app directory.

    By default, the app will be "config2py" and folder_kind will be "config".
    The exact text of the path is platform-specific (``~/.config/config2py`` under
    the XDG standards, ``%APPDATA%\\config2py`` on Windows), so we assert the
    properties that hold everywhere: it is an absolute path named after the app,
    sitting directly inside the 'config' root directory.

    >>> folder = get_app_folder()
    >>> os.path.isabs(folder)
    True
    >>> os.path.basename(folder)
    'config2py'
    >>> os.path.dirname(folder) == get_app_rootdir('config')
    True

    You can specify a different app name and folder kind:

    >>> get_app_folder('my_app', folder_kind='data')  # doctest: +SKIP
    '/Users/.../.local/share/my_app'
    >>> get_app_folder('my_app', folder_kind='cache')  # doctest: +SKIP
    '/Users/.../.cache/my_app'

    You can also specify a path relative to the app root directory:

    >>> get_app_folder('another/app/subfolder', folder_kind='data')  # doctest: +SKIP
    '/Users/.../.local/share/another/app/subfolder'

    If ensure_exists is True, the directory will be created and initialized
    with the setup_callback:

    >>> path = get_app_folder('my_app', ensure_exists=True)  # doctest: +SKIP
    >>> os.path.exists(path)  # doctest: +SKIP
    True
    """
    app_data_path = os.path.join(
        get_app_rootdir(folder_kind, ensure_exists=ensure_exists), app_name
    )
    app_data_folder_does_not_exist = not os.path.isdir(app_data_path)

    if app_data_folder_does_not_exist and ensure_exists:
        setup_callback(app_data_path)
    return app_data_path


get_app_config_folder = partial(get_app_folder, folder_kind="config")
get_app_data_folder = partial(get_app_folder, folder_kind="data")

DFLT_CONFIGS_NAME = "configs"


# TODO: is "get" the right word, since it makes the folder too?
# TODO: Merge get_configs_folder_for_app and get_app_config_folder
def get_configs_folder_for_app(
    app_name: str = DFLT_APP_NAME,
    *,
    configs_name: str = DFLT_CONFIGS_NAME,
    app_dir_setup_callback: Callable[[str], None] = _default_folder_setup,
    config_dir_setup_callback: Callable[[str], None] = _default_folder_setup,
    ensure_exists: bool = True,
):
    """
    Retrieve or create the configs directory specific to the given app name.

    Args:
        app_name (str): Name of the app for which the configs directory is needed.
        configs_name (str): Name of the configs directory.
        app_dir_setup_callback (Callable[[str], None]): A callback function to
            initialize the app directory. Default is _default_folder_setup.
        config_dir_setup_callback (Callable[[str], None]): A callback function to
            initialize the configs directory. Default is _default_folder_setup.
        ensure_exists (bool): Whether to create (and set up) the directory. With
            ``False``, only the path is computed: nothing is created or chmod-ed.
    """
    app_dir = get_app_config_folder(app_name, setup_callback=app_dir_setup_callback)
    configs_dir = os.path.join(app_dir, configs_name)
    if not ensure_exists:
        return configs_dir
    return setup_configs_folder(configs_dir, setup_callback=config_dir_setup_callback)


def setup_configs_folder(
    configs_dir: str,
    *,
    setup_callback: Callable[[str], None] = _default_folder_setup,
) -> str:
    """Create ``configs_dir`` (via ``setup_callback``) and return it.

    If the folder is one config2py manages (it holds a ``.config2py`` marker), its
    modes are also re-tightened, as ``get_configs_folder_for_app`` does.
    """
    setup_callback(configs_dir)
    if os.path.isfile(os.path.join(configs_dir, ".config2py")):
        _tighten_managed_configs_folder(configs_dir)
    return configs_dir


def _tighten_managed_configs_folder(configs_dir):
    """Re-tighten a config2py-managed configs folder created with looser modes.

    The folder becomes ``0o700`` and the files in it lose their group and other
    permission bits, so secrets saved before values were written ``0o600`` are not
    left world-readable (see i2mint/config2py#33 and #35). Best-effort: a failing
    ``chmod`` warns instead of raising. Symlinks are not followed.
    """
    if os.name != "posix":
        return
    if not tighten_mode(configs_dir, 0o700):
        return
    # Each file is opened without following symlinks and fchmod-ed through its
    # descriptor, so a file swapped for a symlink can't redirect the chmod.
    nofollow = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    failures = []
    for dirpath, _dirnames, filenames in os.walk(configs_dir):
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                fd = os.open(path, nofollow)
            except OSError as error:
                if error.errno not in (errno.ELOOP, errno.ENOENT):
                    failures.append((path, error))
                continue  # a symlink (not followed), or gone
            try:
                st = os.fstat(fd)
                if stat.S_ISREG(st.st_mode) and st.st_mode & 0o077:
                    os.fchmod(fd, st.st_mode & 0o700)
            except OSError as error:
                failures.append((path, error))
            finally:
                os.close(fd)
    if failures:  # one warning, not one per file and per import
        path, error = failures[0]
        _warn_not_tightened(
            f"{len(failures)} file(s) in {configs_dir!r} (e.g. {path!r}: {error})"
        )


get_app_data_directory = get_app_config_folder  # backwards compatibility alias
get_configs_directory_for_app = (
    get_configs_folder_for_app  # backwards compatibility alias
)

# The path of config2py's own configs folder. It is computed at import, but the folder
# is only created on first use, so ``import config2py`` writes nothing to disk
# (see https://github.com/i2mint/config2py/issues/26). Reading ``DFLT_CONFIG_FOLDER``
# (served by the module ``__getattr__`` below) creates it, as importing did before.
_DFLT_CONFIGS_FOLDER_PATH = get_configs_folder_for_app(ensure_exists=False)
_dflt_configs_folder_is_set_up = False


def _normalized_path(path) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(os.path.expanduser(path))))


def looks_like_path(src) -> bool:
    """Whether ``src`` is spelled as a filesystem path rather than as an app name.

    A ``pathlib.Path`` (or any ``os.PathLike``), an absolute path, or a string
    containing ``os.sep`` or ``os.altsep`` (so ``"C:/work/configs"`` on Windows) is a
    path. A bare name such as ``"configs"`` is not, whether or not a directory of that
    name exists (see https://github.com/i2mint/config2py/issues/28).

    >>> looks_like_path("my_app")
    False
    >>> looks_like_path("configs/")
    True
    >>> from pathlib import Path
    >>> looks_like_path(Path("configs"))
    True
    """
    if not isinstance(src, str):
        return isinstance(src, os.PathLike)
    return (
        os.path.isabs(src)
        or os.path.sep in src
        or bool(os.path.altsep and os.path.altsep in src)
    )


def is_default_configs_folder(path) -> bool:
    """Whether ``path`` (however spelled) is config2py's own configs folder.

    A string without a path separator (that doesn't start with ``~``) is an app name,
    not a path (see https://github.com/i2mint/config2py/issues/28), so it is never
    the default folder, whatever the current directory.
    """
    if isinstance(path, str):
        if not (looks_like_path(path) or path.startswith("~")):
            return False
    try:
        return _normalized_path(path) == _normalized_path(_DFLT_CONFIGS_FOLDER_PATH)
    except (TypeError, ValueError, OSError):  # not a path, or no current directory
        return False


def ensure_default_configs_folder() -> str:
    """Create config2py's own configs folder if needed, and return its path.

    The folder's modes are re-tightened (see ``setup_configs_folder``) once per
    process; a folder deleted in the meantime is re-created.
    """
    global _dflt_configs_folder_is_set_up
    path = _DFLT_CONFIGS_FOLDER_PATH
    if not (_dflt_configs_folder_is_set_up and os.path.isdir(path)):
        setup_configs_folder(path)
        _dflt_configs_folder_is_set_up = True
    return path


def __getattr__(name):
    if name == "DFLT_CONFIG_FOLDER":
        return ensure_default_configs_folder()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Seed-on-missing and AppData facade
# ---------------------------------------------------------------------------


def ensure_seeded(
    target: Union[str, Path],
    package_name: str,
    seed_subpackage: str,
    filename: str,
    *,
    seed_data_dir: str = "_seed_data",
) -> Path:
    """Copy a bundled seed file to *target* if it does not already exist.

    Reads the seed from ``importlib.resources.files(
    "{package_name}.{seed_data_dir}.{seed_subpackage}") / filename``
    and writes its bytes to *target*.  If *target* already exists, this is
    a no-op (user edits are preserved).

    Args:
        target: Destination path for the seeded file.
        package_name: Top-level Python package that ships the seed data.
        seed_subpackage: Subdirectory inside ``_seed_data`` (e.g. ``"resources"``
            or ``"config"``).
        filename: Name of the seed file.
        seed_data_dir: Name of the seed-data directory inside *package_name*
            (default ``"_seed_data"``).

    Returns:
        The resolved *target* as a ``Path``.

    Example:

        >>> from config2py import ensure_seeded
        >>> # ensure_seeded("/tmp/myfile.txt", "mypkg", "resources", "myfile.txt")
    """
    target = Path(target)
    if not target.exists():
        from importlib.resources import files

        ref = files(f"{package_name}.{seed_data_dir}.{seed_subpackage}") / filename
        secure_makedirs(target.parent)
        with secure_open(target, "wb") as fp:
            fp.write(ref.read_bytes())
    return target


class AppData:
    """Per-user data directory facade for a Python application.

    Binds an application name (and optional Python package name) once and
    provides convenient access to:

    * **resources** — editable reference data seeded from the package on
      first access (``~/.local/share/<app>/resources/``).
    * **config** — user preference files, also seeded on first access
      (``~/.config/<app>/``).
    * **artifact directories** — runtime-generated data organised by kind
      (``~/.local/share/<app>/artifacts/<kind>/``).

    Seed files are read via ``importlib.resources`` from
    ``<package_name>._seed_data.{resources,config}/``.

    Args:
        app_name: The application name used for the directory under the
            XDG root (e.g. ``"my_app"`` → ``~/.local/share/my_app``).
        package_name: The top-level Python package that contains the
            ``_seed_data`` directory.  Defaults to *app_name*.
        seed_data_dir: Name of the seed-data sub-package inside the
            Python package (default ``"_seed_data"``).

    Example:

        >>> app = AppData("myapp", package_name="myapp")
        >>> app.app_folder()  # doctest: +SKIP
        PosixPath('/Users/.../.local/share/myapp')
    """

    def __init__(
        self,
        app_name: str,
        *,
        package_name: Optional[str] = None,
        seed_data_dir: str = "_seed_data",
    ):
        """See the class docstring for each parameter."""
        self.app_name = app_name
        self.package_name = package_name or app_name
        self.seed_data_dir = seed_data_dir

    # -- folder helpers ---------------------------------------------------

    def app_folder(self, *, folder_kind: str = "data") -> Path:
        """Return the app directory for *folder_kind*, creating it if needed."""
        return Path(
            get_app_folder(
                self.app_name,
                folder_kind=folder_kind,
                ensure_exists=True,
            )
        )

    # -- seed-on-missing access -------------------------------------------

    def get_resource(self, name: str) -> Path:
        """Return a user resource path, seeding from package data if missing."""
        target = self.app_folder(folder_kind="data") / "resources" / name
        return ensure_seeded(
            target,
            self.package_name,
            "resources",
            name,
            seed_data_dir=self.seed_data_dir,
        )

    def get_config(self, name: str) -> Path:
        """Return a config file path, seeding from package data if missing."""
        target = self.app_folder(folder_kind="config") / name
        return ensure_seeded(
            target,
            self.package_name,
            "config",
            name,
            seed_data_dir=self.seed_data_dir,
        )

    # -- artifact directories ---------------------------------------------

    def get_artifact_dir(self, kind: str) -> Path:
        """Return (and create) an artifact sub-directory for *kind*."""
        d = self.app_folder(folder_kind="data") / "artifacts" / kind
        secure_makedirs(d)
        return d


import sys


def _get_ipython_in_globals():
    return "get_ipython" in globals()


def _main_does_not_have_file_attribute():
    return not hasattr(sys.modules["__main__"], "__file__")


_repl_conditions = {_get_ipython_in_globals, _main_does_not_have_file_attribute}


def is_repl():
    """
    Determines if the Python interpreter is running in REPL.

    To test: If you put it in a module.py, do a print of it in the module, and do
    ``python module.py`` it should print False.
    If you do ``python -i module.py``, or call it from a python console or jupyter
    notebook, it should return ``True``.

    Returns:
        bool: True if running in a REPL, False otherwise.

    ``is_repl`` returns ``True`` if any function in ``is_repl.repl_conditions``
    (a set of no-argument callables) returns ``True``. By default that set checks
    whether ``get_ipython`` is in globals, or whether ``__main__`` has no
    ``__file__`` attribute. Mutate ``is_repl.repl_conditions`` in place (e.g.
    ``is_repl.repl_conditions.add(fn)``) to change the checks -- rebinding the
    attribute to a new set has no effect, since ``is_repl`` reads the original set.
    """
    if any(condition() for condition in _repl_conditions):
        return True
    return False


is_repl.repl_conditions: set[Callable] = _repl_conditions  # type: ignore


def _value_node_is_instance_of(
    node_value, classes=(ast.Constant, ast.List, ast.Tuple, ast.Dict)
):
    return isinstance(node_value, classes)


def parse_assignments_from_py_source(
    source_code: str, *, name_filt=None, value_filt=_value_node_is_instance_of
):
    """Parse assignments from python source code.

    >>> source_code = '''a = 1
    ... b = 'hello'
    ... c = [1, 2, 3]
    ... def func():
    ...     d = 4
    ... '''
    >>> dict(parse_assignments_from_py_source(source_code))
    {'a': 1, 'b': 'hello', 'c': [1, 2, 3], 'd': 4}

    """
    name_filt = name_filt or (lambda x: True)
    value_filt = value_filt or (lambda x: True)

    # Parse the source code to create an AST
    tree = ast.parse(source_code)

    # Walk through all nodes in the AST
    for node in ast.walk(tree):
        # If the node is an assignment, it may be assigning a value to a variable
        if isinstance(node, ast.Assign):
            # Go through each target in the assignment
            for target in node.targets:
                # If the target is a Name node, it's a variable being assigned a value
                if isinstance(target, ast.Name):
                    if name_filt(target.id) and value_filt(node.value):
                        yield target.id, ast.literal_eval(node.value)
