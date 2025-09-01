import pytest
import json
import os
import sys

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestCORS:
    """Test CORS configuration and functionality."""
    
    def test_healthz_ok(self, client):
        """Test that /healthz returns 200 and proper JSON."""
        response = client.get('/healthz')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        assert data.get('status') == 'ok'
        assert 'ts' in data
    
    def test_preflight_login_allows_origin(self, client):
        """Test that OPTIONS /login handles CORS preflight correctly."""
        origin = 'https://pfcreativeaistudio.vercel.app'
        response = client.options('/login', headers={
            'Origin': origin,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type, x-admin-password'
        })
        
        # Should return 200 or 204 for preflight
        assert response.status_code in [200, 204]
        
        # Check CORS headers
        assert response.headers.get('Access-Control-Allow-Origin') == origin
        assert response.headers.get('Access-Control-Allow-Credentials') == 'true'
        
        # Check that required headers are allowed
        allow_headers = response.headers.get('Access-Control-Allow-Headers', '').lower()
        assert 'content-type' in allow_headers
        assert 'x-admin-password' in allow_headers or 'authorization' in allow_headers
    
    def test_post_login_reaches_server(self, client):
        """Test that POST /login is not blocked by CORS."""
        origin = 'https://pfcreativeaistudio.vercel.app'
        response = client.post('/login', 
            headers={
                'Origin': origin,
                'Content-Type': 'application/json'
            },
            data=json.dumps({
                'username': 'testuser',
                'password': 'testpass'
            })
        )
        
        # Should reach server (may return 401/400 due to auth failure, but not CORS blocked)
        assert response.status_code in [200, 400, 401, 500]  # Any response means it reached server
        
        # Check CORS headers are present
        assert response.headers.get('Access-Control-Allow-Origin') == origin
        assert response.headers.get('Access-Control-Allow-Credentials') == 'true'
    
    def test_cors_with_localhost(self, client):
        """Test CORS works with localhost origin."""
        origin = 'http://localhost:3000'
        response = client.options('/login', headers={
            'Origin': origin,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type'
        })
        
        assert response.status_code in [200, 204]
        assert response.headers.get('Access-Control-Allow-Origin') == origin
        assert response.headers.get('Access-Control-Allow-Credentials') == 'true'
    
    def test_cors_rejects_unknown_origin(self, client):
        """Test that unknown origins are rejected."""
        origin = 'https://evil.com'
        response = client.options('/login', headers={
            'Origin': origin,
            'Access-Control-Request-Method': 'POST'
        })
        
        # Should not return the evil origin in Allow-Origin header
        allow_origin = response.headers.get('Access-Control-Allow-Origin')
        assert allow_origin != origin or allow_origin is None
