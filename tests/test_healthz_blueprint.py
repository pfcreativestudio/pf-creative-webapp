import main as appmod

def test_healthz_is_registered():
    app = appmod.app
    urls = [str(r) for r in app.url_map.iter_rules()]
    joined = " ".join(urls)
    assert "/ping" in joined
    assert "/health" in joined


