import base64
from types import SimpleNamespace

import httpx
import pytest

from server.providers import ProviderError, Providers, image_error


@pytest.mark.parametrize('count', [1, 2])
def test_flash_reference_request_and_single_output(monkeypatch, count):
    monkeypatch.setenv('VOLCENGINE_API_KEY', 'test-key')
    monkeypatch.setenv('VOLCENGINE_MODEL_ID', 'doubao-seedream-5-0-flash-260915')
    monkeypatch.setenv('VOLCENGINE_FINAL_SIZE', '2K')
    monkeypatch.setenv('VOLCENGINE_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3')
    photos = [b'original-photo-one', b'original-photo-two']

    def post(self, url, *, headers, json):
        assert url.endswith('/images/generations')
        assert 'sequential_image_generation' not in json
        assert json['model'] == 'doubao-seedream-5-0-flash-260915'
        assert [base64.b64decode(p.split(',', 1)[1]) for p in json['image']] == photos
        assert json['size'] == '2K'
        return httpx.Response(200, json={'data': [
            {'b64_json': base64.b64encode(b'generated-grid').decode()}
            for _ in range(count)
        ]})

    monkeypatch.setattr(httpx.Client, 'post', post)
    provider = Providers(SimpleNamespace(mode='live'))
    if count == 1:
        assert provider.generate('nine-cell grid', photos) == b'generated-grid'
    else:
        with pytest.raises(ProviderError, match='单张有效母图'):
            provider.generate('nine-cell grid', photos)


@pytest.mark.parametrize('upstream,expected', [
    ('QuotaExceeded','image_quota_exceeded'),
    ('SetLimitExceeded','image_spending_limit'),
    ('ModelAccountIpmRateLimitExceeded','image_rate_limited'),
    ('ServerOverloaded','image_capacity_failed'),
])
def test_429_diagnostics_exclude_upstream_private_message(monkeypatch, upstream, expected):
    monkeypatch.setenv('VOLCENGINE_API_KEY','private-test-key')
    response=httpx.Response(429,headers={'x-request-id':'req-123'},json={
        'error':{'code':upstream,'message':'private-test-key personal-photo-base64 otp-123456'}})
    error=image_error(response)
    assert error.code==expected
    assert error.diagnostics=={'status':429,'upstream_code':upstream,'request_id':'req-123'}
    assert 'private-test-key' not in str(error)
    assert 'personal-photo' not in str(error.diagnostics)


def test_invalid_error_body_and_sensitive_identifier_are_not_logged(monkeypatch):
    monkeypatch.setenv('VOLCENGINE_API_KEY','private-test-key')
    error=image_error(httpx.Response(429,headers={'x-request-id':'private-test-key'},content=b'not-json'))
    assert error.diagnostics=={'status':429,'upstream_code':None,'request_id':None}
    assert image_error(httpx.Response(429,json={'error':[]})).code=='image_rate_limited'
