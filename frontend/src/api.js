import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

/**
 * Generates a synthetic identity timeline and evaluates risk
 * @param {Object} options { identity_type?: 'sleeper' | 'benign', weeks?: number, ring_id?: string }
 */
export const generateIdentity = async (options = {}) => {
  try {
    const response = await client.post('/forge/generate', options);
    return response.data;
  } catch (error) {
    console.error('Error generating identity:', error);
    throw error;
  }
};

/**
 * Fetches all past evaluated identities and verdicts
 */
export const getHistory = async () => {
  try {
    const response = await client.get('/sentinel/history');
    return response.data;
  } catch (error) {
    console.error('Error fetching sentinel history:', error);
    throw error;
  }
};

/**
 * Fetches structured weekly spend and login timeline for an identity
 * @param {string} identityId
 */
export const getTimeline = async (identityId) => {
  try {
    const response = await client.get(`/sentinel/timeline/${identityId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching timeline for ${identityId}:`, error);
    throw error;
  }
};

/**
 * Fetches round-by-round catch rate data showing adversarial arms race
 */
export const getRounds = async () => {
  try {
    const response = await client.get('/sentinel/rounds');
    return response.data;
  } catch (error) {
    console.error('Error fetching sentinel rounds:', error);
    throw error;
  }
};

/**
 * Fetches identity similarity network graph
 * @param {number} threshold Cosine similarity threshold (0.5 - 1.0)
 */
export const getSimilarityGraph = async (threshold = 0.88) => {
  try {
    const response = await client.get(`/sentinel/graph?threshold=${threshold}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching similarity graph:', error);
    throw error;
  }
};

export default {
  generateIdentity,
  getHistory,
  getTimeline,
  getRounds,
  getSimilarityGraph,
};
