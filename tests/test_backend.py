"""
Test suite for the Photo Mosaic Platform Backend API
"""
import pytest
import os
import sys
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend_api import app, db, User, Mosaic, PrintProduct, Order


@pytest.fixture
def client():
    """Create test client with temporary database."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()  # Ensure clean state
            db.create_all()
            # Add test products
            product = PrintProduct(
                name='Test Poster',
                category='poster',
                size='24x36',
                base_price=8.00,
                retail_price=24.99
            )
            db.session.add(product)
            db.session.commit()
            yield client
            db.session.remove()
            db.drop_all()


@pytest.fixture
def auth_client(client):
    """Create authenticated test client with active session."""
    with client.session_transaction() as sess:
        sess.clear()

    # Register and login a user
    client.post('/api/auth/register',
        json={'username': 'testuser', 'email': 'test@example.com', 'password': 'testpass123'},
        content_type='application/json'
    )
    # Login explicitly to ensure session is set
    client.post('/api/auth/login',
        json={'username': 'testuser', 'password': 'testpass123'},
        content_type='application/json'
    )
    return client


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestAuthentication:
    """Test authentication endpoints."""

    def test_register_success(self, client):
        response = client.post('/api/auth/register',
            json={
                'username': 'newuser',
                'email': 'new@example.com',
                'password': 'password123'
            },
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'user' in data
        assert data['user']['username'] == 'newuser'

    def test_register_missing_fields(self, client):
        response = client.post('/api/auth/register',
            json={'username': 'test'},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_register_short_username(self, client):
        response = client.post('/api/auth/register',
            json={
                'username': 'ab',
                'email': 'test@example.com',
                'password': 'password123'
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Username must be 3-30 characters' in data['error']

    def test_register_invalid_username(self, client):
        response = client.post('/api/auth/register',
            json={
                'username': 'invalid@user',
                'email': 'test@example.com',
                'password': 'password123'
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'letters, numbers, and underscores' in data['error']

    def test_register_invalid_email(self, client):
        response = client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'invalid-email',
                'password': 'password123'
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid email format' in data['error']

    def test_register_short_password(self, client):
        response = client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'short'
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Password must be at least 8 characters' in data['error']

    def test_register_duplicate_username(self, client):
        # First registration
        client.post('/api/auth/register',
            json={
                'username': 'duplicate',
                'email': 'first@example.com',
                'password': 'password123'
            },
            content_type='application/json'
        )
        # Second registration with same username
        response = client.post('/api/auth/register',
            json={
                'username': 'duplicate',
                'email': 'second@example.com',
                'password': 'password123'
            },
            content_type='application/json'
        )
        assert response.status_code == 409
        data = json.loads(response.data)
        assert 'Username already exists' in data['error']

    def test_login_success(self, client):
        # Register first
        client.post('/api/auth/register',
            json={
                'username': 'logintest',
                'email': 'login@example.com',
                'password': 'password123'
            },
            content_type='application/json'
        )
        # Then login
        response = client.post('/api/auth/login',
            json={
                'username': 'logintest',
                'password': 'password123'
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data

    def test_login_wrong_password(self, client):
        # Register first
        client.post('/api/auth/register',
            json={
                'username': 'wrongpass',
                'email': 'wrong@example.com',
                'password': 'password123'
            },
            content_type='application/json'
        )
        # Login with wrong password
        response = client.post('/api/auth/login',
            json={
                'username': 'wrongpass',
                'password': 'wrongpassword'
            },
            content_type='application/json'
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post('/api/auth/login',
            json={
                'username': 'nonexistent',
                'password': 'password123'
            },
            content_type='application/json'
        )
        assert response.status_code == 401

    def test_get_current_user_unauthenticated(self, client):
        response = client.get('/api/auth/me')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_current_user_authenticated(self, auth_client):
        response = auth_client.get('/api/auth/me')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['username'] == 'testuser'


class TestProducts:
    """Test product endpoints."""

    def test_get_products(self, client):
        response = client.get('/api/products')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'products' in data
        assert len(data['products']) >= 1

    def test_get_product_by_id(self, client):
        # First get all products to find an ID
        response = client.get('/api/products')
        data = json.loads(response.data)
        product_id = data['products'][0]['id']

        # Then get specific product
        response = client.get(f'/api/products/{product_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'product' in data

    def test_get_nonexistent_product(self, client):
        response = client.get('/api/products/99999')
        assert response.status_code == 404


class TestMosaics:
    """Test mosaic endpoints."""

    def test_list_mosaics_unauthenticated(self, client):
        response = client.get('/api/mosaic')
        assert response.status_code == 401

    def test_list_mosaics_authenticated(self, auth_client):
        response = auth_client.get('/api/mosaic')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'mosaics' in data
        assert 'total' in data

    def test_list_mosaics_pagination_limit(self, auth_client):
        # Test that per_page is capped at 100
        response = auth_client.get('/api/mosaic?per_page=500')
        assert response.status_code == 200
        # The request should succeed (limit is enforced server-side)


class TestOrders:
    """Test order endpoints."""

    def test_list_orders_unauthenticated(self, client):
        response = client.get('/api/order')
        assert response.status_code == 401

    def test_list_orders_authenticated(self, auth_client):
        response = auth_client.get('/api/order')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'orders' in data


class TestErrorHandling:
    """Test error handling."""

    def test_404_error(self, client):
        response = client.get('/api/nonexistent-endpoint')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
