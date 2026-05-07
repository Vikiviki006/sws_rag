import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const sendChatMessage = async (question) => {
  try {
    const response = await api.post('/chat', { question });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to send message');
  }
};

export const uploadPdf = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  try {
    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to upload PDF');
  }
};

export const fetchHealth = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    throw new Error('Backend is unreachable');
  }
};
