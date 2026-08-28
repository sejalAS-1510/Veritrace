import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

/**
 * Health check & system stats
 */
export const getSystemStatus = async () => {
  try {
    const response = await client.get('/');
    return response.data;
  } catch (error) {
    console.error('Error fetching system status:', error);
    throw error;
  }
};

/**
 * Generates a synthetic identity timeline and evaluates risk via Sentinel
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
 * Generates a batch of identities including a coordinated fraud ring
 * @param {Object} options { count?: number, sleeper_ratio?: number }
 */
export const generateBatch = async (options = { count: 10, sleeper_ratio: 0.5 }) => {
  try {
    const response = await client.post('/forge/batch', options);
    return response.data;
  } catch (error) {
    console.error('Error generating batch:', error);
    throw error;
  }
};

/**
 * Analyzes an externally supplied timeline
 * @param {Object} payload { timeline: Array, identity_id?: string }
 */
export const analyzeTimeline = async (payload) => {
  try {
    const response = await client.post('/sentinel/analyze', payload);
    return response.data;
  } catch (error) {
    console.error('Error analyzing timeline:', error);
    throw error;
  }
};

/**
 * Fetches all evaluated identities and verdicts
 * @param {Object} params { limit?: number, type_filter?: string, flagged_only?: boolean }
 */
export const getHistory = async (params = {}) => {
  try {
    const response = await client.get('/sentinel/history', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching sentinel history:', error);
    throw error;
  }
};

/**
 * Fetches all sleeper-type identities (attacks) sorted by risk score
 */
export const getAttacks = async (limit = 100) => {
  try {
    const response = await client.get('/attacks', { params: { limit } });
    return response.data;
  } catch (error) {
    console.error('Error fetching attacks:', error);
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
 * Fetches global detection metrics across all identities
 */
export const getGlobalMetrics = async () => {
  try {
    const response = await client.get('/metrics');
    return response.data;
  } catch (error) {
    console.error('Error fetching global metrics:', error);
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
 * Runs one live adversarial round (Forge generation → Sentinel scoring → Mutation feedback)
 * @param {string} ringId optional ring id
 */
export const runAdversarialRound = async (ringId = null) => {
  try {
    const params = ringId ? { ring_id: ringId } : {};
    const response = await client.post('/adversarial/run', null, { params });
    return response.data;
  } catch (error) {
    console.error('Error running adversarial round:', error);
    throw error;
  }
};

/**
 * Resets the adversarial session (round counter + Forge parameters)
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
 * Returns live adversarial round history
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
 * Returns adversarial session status (Forge params, round count, catch rate)
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
export const getAdversarialMetrics = async () => {
  try {
    const response = await client.get('/adversarial/metrics');
    return response.data;
  } catch (error) {
    console.error('Error fetching adversarial metrics:', error);
    throw error;
  }
};

export default {
  getSystemStatus,
  generateIdentity,
  generateBatch,
  analyzeTimeline,
  getHistory,
  getAttacks,
  getTimeline,
  getGlobalMetrics,
  getSimilarityGraph,
  runAdversarialRound,
  resetAdversarialSession,
  getAdversarialRounds,
  getAdversarialStatus,
  getAdversarialMetrics,
};
