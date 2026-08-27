from app.tools.rights_log_search import format_params


def test_format_params_modern_php_serialized_groups():
    text = (
        'a:2:{s:12:"4::oldgroups";a:2:{i:0;s:13:"autopatrolled";'
        'i:1;s:24:"temporary-account-viewer";}s:12:"5::newgroups";'
        'a:1:{i:0;s:13:"autopatrolled";}}'
    )
    assert format_params(text) == "from autopatrolled, temporary-account-viewer to autopatrolled"


def test_format_params_modern_php_serialized_empty_oldgroups():
    text = 'a:2:{s:12:"4::oldgroups";a:0:{}s:12:"5::newgroups";a:1:{i:0;s:13:"autopatrolled";}}'
    assert format_params(text) == "from (none) to autopatrolled"


def test_format_params_legacy_newline_pair():
    assert format_params("oldval\nnewval") == "from oldval to newval"


def test_format_params_empty():
    assert format_params("") == "(none)"
    assert format_params(None) == "(none)"


def test_format_params_bytes_input():
    assert format_params(b"oldval\nnewval") == "from oldval to newval"
