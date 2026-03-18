from robot.osiptel.session import _extract_site_key


def test_extract_from_data_attr():
    html = '<div data-sitekey="6LdcxV8dAAAAAMQZV05VmMp5TYlQJGoGQjv6FgX8"></div>'
    assert _extract_site_key(html) == "6LdcxV8dAAAAAMQZV05VmMp5TYlQJGoGQjv6FgX8"

def test_extract_single_quotes():
    html = "<div data-sitekey='6LdcxV8dAAAAAMQZV05VmMp5TYlQJGoGQjv6FgX8'></div>"
    assert _extract_site_key(html) == "6LdcxV8dAAAAAMQZV05VmMp5TYlQJGoGQjv6FgX8"

def test_missing_returns_empty():
    assert _extract_site_key("<html></html>") == ""
