import React, { useState, useEffect } from 'react';

// ============================================================================
// MAIN APP COMPONENT
// ============================================================================

export default function MosaicApp() {
  const [currentPage, setCurrentPage] = useState('home');
  const [user, setUser] = useState(null);
  const [mosaics, setMosaics] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Check if user is logged in
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await fetch('/api/auth/me');
      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    }
  };

  return (
    <div className="app">
      <Navigation user={user} setUser={setUser} currentPage={currentPage} setCurrentPage={setCurrentPage} />
      
      <main className="main-content">
        {currentPage === 'home' && <HomePage user={user} setCurrentPage={setCurrentPage} />}
        {currentPage === 'create' && user && <CreateMosaicPage setCurrentPage={setCurrentPage} user={user} />}
        {currentPage === 'gallery' && user && <GalleryPage user={user} />}
        {currentPage === 'login' && <LoginPage setUser={setUser} setCurrentPage={setCurrentPage} />}
        {currentPage === 'signup' && <SignupPage setUser={setUser} setCurrentPage={setCurrentPage} />}
      </main>
      
      <Footer />
    </div>
  );
}

// ============================================================================
// NAVIGATION
// ============================================================================

function Navigation({ user, setUser, currentPage, setCurrentPage }) {
  return (
    <nav className="navbar">
      <div className="nav-container">
        <div className="nav-brand" onClick={() => setCurrentPage('home')}>
          <span className="logo-icon">🎨</span>
          <h1>MosaicStudio</h1>
        </div>
        
        <div className="nav-menu">
          <button className="nav-link" onClick={() => setCurrentPage('home')}>
            Home
          </button>
          
          {user ? (
            <>
              <button className="nav-link" onClick={() => setCurrentPage('create')}>
                Create
              </button>
              <button className="nav-link" onClick={() => setCurrentPage('gallery')}>
                My Mosaics
              </button>
              <button className="nav-link logout" onClick={() => {
                fetch('/api/auth/logout', { method: 'POST' });
                setUser(null);
                setCurrentPage('home');
              }}>
                Logout
              </button>
            </>
          ) : (
            <>
              <button className="nav-link" onClick={() => setCurrentPage('login')}>
                Login
              </button>
              <button className="nav-link signup" onClick={() => setCurrentPage('signup')}>
                Sign Up
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

// ============================================================================
// HOME PAGE
// ============================================================================

function HomePage({ user, setCurrentPage }) {
  const handleGetStarted = () => {
    if (user) {
      setCurrentPage('create');
    } else {
      setCurrentPage('signup');
    }
  };

  return (
    <div className="home-page">
      <section className="hero">
        <div className="hero-content">
          <h2 className="hero-title">Transform Your Photos Into Mosaic Masterpieces</h2>
          <p className="hero-subtitle">Create stunning photo mosaics and order premium prints, canvases, and framed artwork</p>

          <div className="cta-buttons">
            <button className="btn btn-primary" onClick={handleGetStarted}>Get Started Free</button>
            <button className="btn btn-secondary" onClick={() => document.querySelector('.features').scrollIntoView({ behavior: 'smooth' })}>Learn More</button>
          </div>
        </div>
        
        <div className="hero-visual">
          <div className="mosaic-preview">
            <div className="preview-grid">
              {Array.from({ length: 16 }).map((_, i) => (
                <div key={i} className={`grid-cell cell-${i}`}></div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="features">
        <h2 className="section-title">How It Works</h2>
        
        <div className="features-grid">
          <FeatureCard 
            icon="📤"
            title="Upload"
            description="Upload your target image and tile photos"
          />
          <FeatureCard 
            icon="✨"
            title="Generate"
            description="Our AI creates a beautiful mosaic instantly"
          />
          <FeatureCard 
            icon="🖨️"
            title="Print"
            description="Order high-quality prints, canvases, or framed art"
          />
          <FeatureCard 
            icon="🚚"
            title="Deliver"
            description="Fast shipping to your doorstep"
          />
        </div>
      </section>

      <section className="product-showcase">
        <h2 className="section-title">Available Products</h2>
        
        <div className="products-grid">
          <ProductShowcase 
            category="Posters"
            sizes={['18×24"', '24×36"', '36×48"']}
            price="$24.99+"
            icon="🖼️"
          />
          <ProductShowcase 
            category="Canvas"
            sizes={['12×16"', '16×20"', '20×24"']}
            price="$39.99+"
            icon="🎨"
          />
          <ProductShowcase 
            category="Framed"
            sizes={['11×14"', '16×20"']}
            price="$49.99+"
            icon="🖌️"
          />
        </div>
      </section>

      <section className="testimonials">
        <h2 className="section-title">Loved By Creators</h2>
        
        <div className="testimonials-grid">
          <Testimonial 
            text="These mosaics are absolutely stunning! The quality is incredible."
            author="Sarah M."
          />
          <Testimonial 
            text="Best way to turn my family photos into wall art. Highly recommend!"
            author="James P."
          />
          <Testimonial 
            text="The framed option is gorgeous. Makes a perfect gift!"
            author="Emma K."
          />
        </div>
      </section>
    </div>
  );
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="feature-card">
      <div className="feature-icon">{icon}</div>
      <h3 className="feature-title">{title}</h3>
      <p className="feature-description">{description}</p>
    </div>
  );
}

function ProductShowcase({ category, sizes, price, icon }) {
  return (
    <div className="product-showcase-card">
      <div className="showcase-icon">{icon}</div>
      <h3>{category}</h3>
      <div className="showcase-sizes">
        {sizes.map(size => <span key={size} className="size-tag">{size}</span>)}
      </div>
      <p className="showcase-price">{price}</p>
      <button className="btn btn-small">Learn More</button>
    </div>
  );
}

function Testimonial({ text, author }) {
  return (
    <div className="testimonial">
      <p className="testimonial-text">"{text}"</p>
      <p className="testimonial-author">— {author}</p>
    </div>
  );
}

// ============================================================================
// CREATE MOSAIC PAGE
// ============================================================================

function CreateMosaicPage({ setCurrentPage, user }) {
  const [targetImage, setTargetImage] = useState(null);
  const [tileImages, setTileImages] = useState([]);
  const [title, setTitle] = useState('My Mosaic');
  const [width, setWidth] = useState(4320);
  const [height, setHeight] = useState(2880);
  const [tileSize, setTileSize] = useState(120);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleTargetImageChange = (e) => {
    setTargetImage(e.target.files[0]);
  };

  const handleTileImagesChange = (e) => {
    setTileImages(Array.from(e.target.files));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!targetImage || tileImages.length === 0) {
      setError('Please select a target image and tile images');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('target_image', targetImage);
      tileImages.forEach(file => formData.append('tiles', file));
      formData.append('title', title);
      formData.append('width', width);
      formData.append('height', height);
      formData.append('tile_size', tileSize);

      const response = await fetch('/api/mosaic/create', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to create mosaic');
      }

      const data = await response.json();
      // Redirect to order page
      setCurrentPage('order');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-mosaic-page">
      <div className="create-container">
        <h2 className="page-title">Create Your Mosaic</h2>

        <form className="mosaic-form" onSubmit={handleSubmit}>
          <div className="form-section">
            <h3>Basic Information</h3>
            
            <div className="form-group">
              <label htmlFor="title">Mosaic Title</label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Give your mosaic a name"
              />
            </div>
          </div>

          <div className="form-section">
            <h3>Images</h3>
            
            <div className="form-group">
              <label htmlFor="target">Target Image (the image you want to recreate)</label>
              <div className="file-input-wrapper">
                <input
                  id="target"
                  type="file"
                  accept="image/*"
                  onChange={handleTargetImageChange}
                  className="file-input"
                />
                <div className="file-input-label">
                  {targetImage ? (
                    <span>✓ {targetImage.name}</span>
                  ) : (
                    <span>Click to upload or drag and drop</span>
                  )}
                </div>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="tiles">Tile Images (at least 100 recommended)</label>
              <div className="file-input-wrapper">
                <input
                  id="tiles"
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleTileImagesChange}
                  className="file-input"
                />
                <div className="file-input-label">
                  {tileImages.length > 0 ? (
                    <span>✓ {tileImages.length} images selected</span>
                  ) : (
                    <span>Click to upload or drag and drop multiple images</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3>Settings</h3>
            
            <div className="settings-grid">
              <div className="form-group">
                <label htmlFor="width">Width (pixels)</label>
                <select id="width" value={width} onChange={(e) => setWidth(Number(e.target.value))}>
                  <option value={1920}>1920</option>
                  <option value={3840}>3840</option>
                  <option value={4320}>4320 (36"×24")</option>
                  <option value={7200}>7200 (Large)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="height">Height (pixels)</label>
                <select id="height" value={height} onChange={(e) => setHeight(Number(e.target.value))}>
                  <option value={1440}>1440</option>
                  <option value={2880}>2880 (36"×24")</option>
                  <option value={5400}>5400 (Large)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="tileSize">Tile Size (pixels)</label>
                <select id="tileSize" value={tileSize} onChange={(e) => setTileSize(Number(e.target.value))}>
                  <option value={60}>60 (fine detail)</option>
                  <option value={80}>80</option>
                  <option value={120}>120 (recommended)</option>
                  <option value={160}>160 (fast)</option>
                </select>
              </div>
            </div>

            <div className="settings-info">
              <p>📊 Your mosaic will be {width}×{height}px with {(width/tileSize)*(height/tileSize)} tiles</p>
            </div>
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating Mosaic...' : 'Create Mosaic'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============================================================================
// GALLERY PAGE
// ============================================================================

function GalleryPage({ user }) {
  const [mosaics, setMosaics] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMosaics();
  }, []);

  const fetchMosaics = async () => {
    try {
      const response = await fetch('/api/mosaic');
      if (response.ok) {
        const data = await response.json();
        setMosaics(data.mosaics);
      }
    } catch (error) {
      console.error('Failed to fetch mosaics:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gallery-page">
      <div className="gallery-container">
        <h2 className="page-title">My Mosaics</h2>

        {loading ? (
          <div className="loading">Loading your mosaics...</div>
        ) : mosaics.length === 0 ? (
          <div className="empty-state">
            <p>You haven't created any mosaics yet</p>
            <p>Get started by uploading photos!</p>
          </div>
        ) : (
          <div className="mosaics-grid">
            {mosaics.map(mosaic => (
              <MosaicCard key={mosaic.id} mosaic={mosaic} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MosaicCard({ mosaic }) {
  return (
    <div className="mosaic-card">
      <div className="mosaic-thumbnail">
        <div className="placeholder"></div>
      </div>
      <div className="mosaic-info">
        <h3>{mosaic.title}</h3>
        <p className="mosaic-date">{new Date(mosaic.created_at).toLocaleDateString()}</p>
        <p className="mosaic-size">{mosaic.width}×{mosaic.height}</p>
        
        <div className="mosaic-actions">
          <button className="btn btn-small">Download</button>
          <button className="btn btn-small">Order</button>
          <button className="btn btn-small">Share</button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// LOGIN PAGE
// ============================================================================

function LoginPage({ setUser, setCurrentPage }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Login failed');
      }

      const data = await response.json();
      setUser(data.user);
      setCurrentPage('home');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-form-container">
        <h2>Welcome Back</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account? <a href="#" onClick={() => setCurrentPage('signup')}>Sign up</a>
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// SIGNUP PAGE
// ============================================================================

function SignupPage({ setUser, setCurrentPage }) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Signup failed');
      }

      const data = await response.json();
      setUser(data.user);
      setCurrentPage('home');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-form-container">
        <h2>Join MosaicStudio</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <a href="#" onClick={() => setCurrentPage('login')}>Login</a>
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// FOOTER
// ============================================================================

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-content">
          <div className="footer-section">
            <h4>MosaicStudio</h4>
            <p>Transform your photos into stunning mosaic art</p>
          </div>
          
          <div className="footer-section">
            <h4>Products</h4>
            <ul>
              <li><a href="#">Posters</a></li>
              <li><a href="#">Canvas</a></li>
              <li><a href="#">Framed Art</a></li>
            </ul>
          </div>
          
          <div className="footer-section">
            <h4>Support</h4>
            <ul>
              <li><a href="#">FAQ</a></li>
              <li><a href="#">Contact</a></li>
              <li><a href="#">Privacy</a></li>
            </ul>
          </div>
          
          <div className="footer-section">
            <h4>Follow</h4>
            <div className="social-links">
              <a href="#">Twitter</a>
              <a href="#">Instagram</a>
              <a href="#">Pinterest</a>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p>&copy; 2024 MosaicStudio. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
