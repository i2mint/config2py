import tempfile
import os
import pytest


def test_process_path():
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, 'foo/bar')

        output_path = process_path(temp_path)
        assert output_path == temp_path
        assert not os.path.exists(output_path)

        output_path = process_path(temp_path, expanduser=False)
        assert output_path == temp_path
        assert not os.path.exists(output_path)

        with pytest.raises(AssertionError):
            output_path = process_path(temp_path, assert_exists=True)

        output_path = process_path(temp_path, ensure_dir_exists=True)
        assert output_path == temp_path
        assert os.path.exists(output_path)

        output_path = process_path(temp_path, assert_exists=True)
        assert output_path == temp_path
        assert os.path.exists(output_path)

        # If path doesn't end with a (system file separator) slash, add one:
        output_path = process_path(temp_path, ensure_endswith_slash=True)
        assert output_path == temp_path + os.path.sep

        # If path ends with a (system file separator) slash, remove it.
        output_path = process_path(
            temp_path + os.path.sep, ensure_does_not_end_with_slash=True
        )
        assert output_path == temp_path
