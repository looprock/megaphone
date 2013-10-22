from webtest import TestApp
from megaphone import megaphone

# see: http://webtest.pythonpaste.org/en/latest/index.html


def test_get_status():
    app = TestApp(megaphone.app)
    resp = app.get('/')

    assert resp.status_int == 200
