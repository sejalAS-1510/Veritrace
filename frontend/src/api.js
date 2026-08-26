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

/**
 * Runs one full adversarial round (Forge → Sentinel → Feedback → Mutate)
 */
export const runAdversarialRound = async () => {
  try {
    const response = await client.post('/adversarial/run');
    return response.data;
  } catch (error) {
    console.error('Error running adversarial round:', error);
    throw error;
  }
};

/**
 * Resets the adversarial session (round counter + Forge params)
 */
export const resetAdversarialSession = async () => {
  try {
    const response = await client.post('/adversarial/reset');
    return response.data;
  } catch (error) {
    console.error('Error resetting adversarial session:', error);
    throw error;
  }
};

/**
 * Returns live adversarial round history (falls back to demo data if no rounds run)
 */
export const getAdversarialRounds = async () => {
  try {
    const response = await client.get('/adversarial/rounds');
    return response.data;
  } catch (error) {
    console.error('Error fetching adversarial rounds:', error);
    throw error;
  }
};

/**
 * Returns adversarial session status (current Forge params, round count)
 */
export const getAdversarialStatus = async () => {
  try {
    const response = await client.get('/adversarial/status');
    return response.data;
  } catch (error) {
    console.error('Error fetching adversarial status:', error);
    throw error;
  }
};

/**
 * Returns precision / recall / F1 / evasion rate from live adversarial rounds
 */
export const getMetrics = async () => {
  try {
    const response = await client.get('/adversarial/metrics');
    return response.data;
  } catch (error) {
    console.error('Error fetching adversarial metrics:', error);
    throw error;
  }
};

export default {
  generateIdentity,
  getHistory,
  getTimeline,
  getRounds,
  getSimilarityGraph,
  runAdversarialRound,
  resetAdversarialSession,
  getAdversarialRounds,
  getAdversarialStatus,
  getMetrics,
};
