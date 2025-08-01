const API_BASE_URL = 'https://api.spark.wiki';

class ApiService {
  async fetchPhotos() {
    try {
      const response = await fetch(`${API_BASE_URL}/photos`);
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
}

export default new ApiService();