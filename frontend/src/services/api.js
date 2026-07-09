const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://api.spark.wiki';
const CDN_BASE_URL = process.env.REACT_APP_CDN_URL || 'https://photos.spark.wiki';

// Strips the "s3://<bucket>/" prefix off an S3 URI and URL-encodes each path
// segment, yielding the key path the CDN serves images under.
function s3UriToPath(s3Uri) {
  const key = s3Uri.replace(/^s3:\/\/[^/]+\//, '');
  return key.split('/').map(encodeURIComponent).join('/');
}

class ApiService {
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

  async fetchPhoto(photoId) {
    try {
      const response = await fetch(`${API_BASE_URL}/photos/${encodeURIComponent(photoId)}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching photo:', error);
      throw error;
    }
  }

  getThumbnailUrl(s3Uri) {
    return `${CDN_BASE_URL}/thumbnail/${s3UriToPath(s3Uri)}`;
  }

  getFullsizeUrl(s3Uri) {
    return `${CDN_BASE_URL}/${s3UriToPath(s3Uri)}`;
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

  async fetchPost(postId) {
    try {
      const response = await fetch(`${API_BASE_URL}/posts/${postId}`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching post:', error);
      throw error;
    }
  }
}

export default new ApiService();