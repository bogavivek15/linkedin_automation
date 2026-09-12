from apps.api.app.core.ssrf import validate_external_url


def test_allows_legitimate_public_urls():
    assert validate_external_url("https://himalayas.app/jobs/full-stack-engineer").is_safe is True
    assert validate_external_url("https://jobicy.com/api/v2/remote-jobs").is_safe is True
    assert validate_external_url("https://careers.google.com").is_safe is True


def test_blocks_localhost_and_loopback():
    assert validate_external_url("http://localhost:8000/api").is_safe is False
    assert validate_external_url("http://127.0.0.1:8000").is_safe is False
    assert validate_external_url("http://0.0.0.0").is_safe is False
    assert validate_external_url("http://[::1]/internal").is_safe is False


def test_blocks_cloud_metadata_endpoints():
    assert validate_external_url("http://169.254.169.254/latest/meta-data/").is_safe is False
    assert validate_external_url("http://metadata.google.internal").is_safe is False


def test_blocks_rfc1918_private_subnets():
    assert validate_external_url("http://10.0.0.1/admin").is_safe is False
    assert validate_external_url("http://172.16.5.2/secret").is_safe is False
    assert validate_external_url("http://192.168.1.1/gateway").is_safe is False


def test_blocks_non_http_protocols():
    assert validate_external_url("file:///etc/passwd").is_safe is False
    assert validate_external_url("ftp://ftp.example.com/data").is_safe is False
    assert validate_external_url("javascript:alert(1)").is_safe is False
