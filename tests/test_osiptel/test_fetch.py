import json
import pytest
from unittest.mock import MagicMock, patch

from robot.domain import RUC
from robot.osiptel.fetch import count_lines
from robot.osiptel.session import Session


def _session() -> Session:
    return Session(cookie="s=x; a=y", site_key="key")


def _mock_client(pages: list[dict]) -> MagicMock:
    client = MagicMock()
    responses = []
    for page in pages:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = page
        responses.append(resp)
    client.post.side_effect = responses
    return client


def test_single_page():
    page = {"iTotalRecords": 2, "aaData": [["a"], ["b"]]}
    client = _mock_client([page])
    assert count_lines(client, _session(), RUC("20100070970"), "tok", 100) == 2

def test_zero_results():
    page = {"iTotalRecords": 0, "aaData": []}
    client = _mock_client([page])
    assert count_lines(client, _session(), RUC("20100070970"), "tok", 100) == 0

def test_multiple_pages():
    page1 = {"iTotalRecords": 3, "aaData": [["a"], ["b"]]}
    page2 = {"iTotalRecords": 3, "aaData": [["c"]]}
    client = _mock_client([page1, page2])
    assert count_lines(client, _session(), RUC("20100070970"), "tok", 2) == 3
    assert client.post.call_count == 2

def test_http_error_propagates():
    client = MagicMock()
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("500")
    client.post.return_value = resp
    with pytest.raises(Exception, match="500"):
        count_lines(client, _session(), RUC("20100070970"), "tok", 100)
