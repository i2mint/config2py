"""Test tools.py"""

import os
from unittest.mock import patch

import pytest

from config2py.tools import simple_config_getter


@pytest.fixture
def mock_config_store_factory():
    with patch('config2py.tools.get_configs_local_store') as mock_factory:
        yield mock_factory


def test_simple_config_getter(mock_config_store_factory):
    key = '_CONFIG2PY_SAFE_TO_DELETE_VAR_'

    # Set up mock config store
    mock_config_store = {key: 'from store'}
    mock_config_store_factory.return_value = mock_config_store

    # Test getting config from environment variable
    os.environ[key] = 'from env var'
    config_getter = simple_config_getter(first_look_in_env_vars=True)
    assert config_getter(key) == 'from env var'

    # Test getting config from central config store
    del os.environ[key]  # delete env var to test central config store
    # config_getter = simple_config_getter()
    # assert config_getter(key) == "from store"

    # Test getting config with ask_user_if_key_not_found=True
    with patch('builtins.input', return_value='from user'):
        config_getter = simple_config_getter(ask_user_if_key_not_found=True)
        assert config_getter('new_key') == 'from user'

    # TODO: Make this test work
    # Test that config_getter.configs is set correctly
    # assert config_getter.configs is mock_config_store
