const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://api.spark.wiki';
const ADMIN_TOKEN_KEY = 'spark_admin_token';
// The bird photos' CDN, and the other photos'. Their hostnames (and buckets)
// are named for what they held first.
const BIRDS_CDN_BASE_URL = process.env.REACT_APP_BIRDS_CDN_URL || 'https://photos.spark.wiki';
const PHOTOS_CDN_BASE_URL = process.env.REACT_APP_PHOTOS_CDN_URL || 'https://normal-photos.spark.wiki';
// CloudFront distribution in front of spark.wiki.books, origin = bucket root
// (no origin path override), so this mirrors S3 keys 1:1 the same way
// BIRDS_CDN_BASE_URL does for the bird photos bucket.
const COVERS_CDN_BASE_URL = process.env.REACT_APP_COVERS_CDN_URL || 'https://books.spark.wiki';

// Each photos bucket's CDN. Both are laid out the same way: a photo at its
// key, and its thumbnail at thumbnail/<key>.
const PHOTO_CDN_BASE_URLS = {
  'spark.wiki.photos': BIRDS_CDN_BASE_URL,
  'spark.wiki.normal-photos': PHOTOS_CDN_BASE_URL,
};

const S3_URI = /^s3:\/\/([^/]+)\/(.*)$/;

// The CDN serving an S3 URI's photo, and the URL-encoded key path it serves
// it under.
function photoCdnLocation(s3Uri) {
  const [, bucket, key] = S3_URI.exec(s3Uri) || [null, null, s3Uri];
  return {
    baseUrl: PHOTO_CDN_BASE_URLS[bucket] || BIRDS_CDN_BASE_URL,
    path: key.split('/').map(encodeURIComponent).join('/'),
  };
}

class ApiService {
  async fetchBirds(filter = {}) {
    try {
      const params = new URLSearchParams(filter);
      const query = params.toString() ? `?${params}` : '';
      const response = await fetch(`${API_BASE_URL}/birds${query}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data.photos || [];
    } catch (error) {
      console.error('Error fetching bird photos:', error);
      throw error;
    }
  }

  // The photos that aren't of birds. filter is optionally one of year
  // ('YYYY'), month ('YYYY-MM'), or day ('YYYY-MM-DD').
  async fetchPhotos(filter = {}) {
    try {
      const params = new URLSearchParams(filter);
      const query = params.toString() ? `?${params}` : '';
      const response = await fetch(`${API_BASE_URL}/photos${query}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data.photos || [];
    } catch (error) {
      console.error('Error fetching photos:', error);
      throw error;
    }
  }

  async fetchTaxonomy() {
    try {
      const response = await fetch(`${API_BASE_URL}/birds/taxonomy`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data.taxonomy || {};
    } catch (error) {
      console.error('Error fetching taxonomy:', error);
      throw error;
    }
  }

  async fetchBird(photoId) {
    try {
      const response = await fetch(`${API_BASE_URL}/birds/${encodeURIComponent(photoId)}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching bird photo:', error);
      throw error;
    }
  }

  getThumbnailUrl(s3Uri) {
    const { baseUrl, path } = photoCdnLocation(s3Uri);
    return `${baseUrl}/thumbnail/${path}`;
  }

  getFullsizeUrl(s3Uri) {
    const { baseUrl, path } = photoCdnLocation(s3Uri);
    return `${baseUrl}/${path}`;
  }

  async fetchPosts() {
    try {
      const response = await fetch(`${API_BASE_URL}/posts`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      return data.posts || [];
    } catch (error) {
      console.error('Error fetching posts:', error);
      throw error;
    }
  }

  async fetchPost(slug) {
    try {
      const response = await fetch(`${API_BASE_URL}/posts/${encodeURIComponent(slug)}`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching post:', error);
      throw error;
    }
  }

  async fetchBooks() {
    try {
      const response = await fetch(`${API_BASE_URL}/books`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      return data.books || [];
    } catch (error) {
      console.error('Error fetching books:', error);
      throw error;
    }
  }

  async fetchBook(title) {
    try {
      const response = await fetch(`${API_BASE_URL}/books/${encodeURIComponent(title)}`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching book:', error);
      throw error;
    }
  }

  // coverKey is the S3 key under spark.wiki.books, e.g. "covers/Dune.jpg" --
  // our own stored copy of the Open Library cover, not a hotlink to it.
  getBookCoverUrl(coverKey) {
    if (!coverKey) return null;
    const path = coverKey.split('/').map(encodeURIComponent).join('/');
    return `${COVERS_CDN_BASE_URL}/${path}`;
  }

  // --- Admin ---

  getAdminToken() {
    return localStorage.getItem(ADMIN_TOKEN_KEY);
  }

  setAdminToken(token) {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
  }

  clearAdminToken() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
  }

  async adminLogin(username, password) {
    const response = await fetch(`${API_BASE_URL}/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || 'Login failed');
    }
    this.setAdminToken(data.token);
    return data;
  }

  // Confirms the stored token (if any) is still accepted by the backend --
  // used on admin page load so an expired token bounces back to the login
  // page instead of the UI just failing silently on the next real request.
  async verifyAdminSession() {
    const token = this.getAdminToken();
    if (!token) return false;
    try {
      const response = await fetch(`${API_BASE_URL}/admin/session`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!response.ok) {
        this.clearAdminToken();
        return false;
      }
      return true;
    } catch (error) {
      console.error('Error verifying admin session:', error);
      return false;
    }
  }

  // An authenticated admin API call, returning its JSON body. A 401 means
  // the session expired, so the stored token is dropped too.
  async adminRequest(path, { method = 'GET', body, failureMessage } = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        'Authorization': `Bearer ${this.getAdminToken()}`,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
      this.clearAdminToken();
    }
    if (!response.ok) {
      throw new Error(data.error || failureMessage);
    }
    return data;
  }

  async submitBookReview(payload) {
    return this.adminRequest('/admin/book-reviews', {
      method: 'POST',
      body: payload,
      failureMessage: 'Failed to submit book review',
    });
  }

  // collection is the photos bucket: 'birds' or 'photos'. prefix is a
  // folder in it: '' for its root, else e.g. '2025/05/17/'.
  async fetchPhotoFolder(collection, prefix) {
    const params = new URLSearchParams({ collection, prefix });
    return this.adminRequest(`/admin/photos/folders?${params}`, {
      failureMessage: 'Failed to load folder',
    });
  }

  async createPhotoFolder(collection, parent, name) {
    return this.adminRequest('/admin/photos/folders', {
      method: 'POST',
      body: { collection, parent, name },
      failureMessage: 'Failed to create folder',
    });
  }

  // Uploads straight to S3 through a presigned URL from the API (photos are
  // too big to send through it), reporting progress from 0 to 1.
  async uploadPhoto(collection, folder, file, onProgress) {
    const { url, headers } = await this.adminRequest('/admin/photos/upload-url', {
      method: 'POST',
      body: { collection, folder, filename: file.name },
      failureMessage: 'Failed to start upload',
    });

    // XMLHttpRequest rather than fetch, which can't report upload progress.
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('PUT', url);
      Object.entries(headers).forEach(([name, value]) => xhr.setRequestHeader(name, value));
      xhr.upload.onprogress = e => {
        if (e.lengthComputable) onProgress(e.loaded / e.total);
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve();
        else reject(new Error(`Upload failed (HTTP ${xhr.status})`));
      };
      // Also what a missing S3 CORS rule looks like from here.
      xhr.onerror = () => reject(new Error('Upload failed (network or CORS error)'));
      xhr.send(file);
    });
  }
}

export default new ApiService();