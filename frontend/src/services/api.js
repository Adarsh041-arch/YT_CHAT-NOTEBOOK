const API_BASE_URL = import.meta.env.VITE_API_URL;

const getHeaders = (token) => {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
};

export const api = {
  login: async (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }
    
    return response.json();
  },

  register: async (username, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }
    
    return response.json();
  },

  getSessions: async (token) => {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      headers: getHeaders(token),
    });
    return response.json();
  },

  getSessionMessages: async (sessionId, token) => {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
      headers: getHeaders(token),
    });
    return response.json();
  },

  processVideo: async (videoId, token) => {
    const response = await fetch(`${API_BASE_URL}/process`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify({ video_id: videoId }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to process video');
    }
    return data;
  },

  streamChat: async (videoId, question, sessionId, token, onChunk) => {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ video_id: videoId, question, session_id: sessionId }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    if (!response.body) {
      throw new Error('No response body from server');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let newSessionId = response.headers.get('X-Session-ID');
    let buffer = '';

    const parseEvent = (text) => {
      let event = 'message';
      let dataStr = '';
      for (const line of text.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7);
        else if (line.startsWith('data: ')) dataStr = line.slice(6);
      }
      try { return { event, data: dataStr ? JSON.parse(dataStr) : null }; }
      catch { return { event, data: null }; }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        if (!part.trim()) continue;
        const parsed = parseEvent(part);
        if (parsed.event === 'token') {
          if (parsed.data && parsed.data.text) {
            onChunk(parsed.data.text, newSessionId);
            newSessionId = null;
          }
        } else if (parsed.event === 'done') {
          return;
        }
      }
    }
  },

  streamPlaylistChat: async (playlistId, question, sessionId, token, onChunk) => {
    const response = await fetch(`${API_BASE_URL}/playlist/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ playlist_id: playlistId, question, session_id: sessionId }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    if (!response.body) {
      throw new Error('No response body from server');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let newSessionId = response.headers.get('X-Session-ID');
    let buffer = '';

    const parseEvent = (text) => {
      let event = 'message';
      let dataStr = '';
      for (const line of text.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7);
        else if (line.startsWith('data: ')) dataStr = line.slice(6);
      }
      try { return { event, data: dataStr ? JSON.parse(dataStr) : null }; }
      catch { return { event, data: null }; }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        if (!part.trim()) continue;
        const parsed = parseEvent(part);
        if (parsed.event === 'token') {
          if (parsed.data && parsed.data.text) {
            onChunk(parsed.data.text, newSessionId);
            newSessionId = null;
          }
        } else if (parsed.event === 'done') {
          return;
        }
      }
    }
  },

  health: async (token) => {
    const response = await fetch(`${API_BASE_URL}/health`, {
      headers: getHeaders(token),
    });
    return response.json();
  },

  processPlaylist: async (playlistUrl, token) => {
    const response = await fetch(`${API_BASE_URL}/playlist`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify({})
    });
    return response.json();
  },

  processPlaylistStream: async (playlistUrl, token, onProgress) => {
    const response = await fetch(`${API_BASE_URL}/playlist/stream`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify({ playlist_url: playlistUrl }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Failed to process playlist');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onProgress(data);
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  },

  getPlaylistForVideo: async (videoId, token) => {
    const response = await fetch(`${API_BASE_URL}/playlist/for-video/${videoId}`, {
      headers: getHeaders(token),
    });
    return response.json();
  },

  retryPlaylistStream: async (playlistUrl, token, onProgress) => {
    const response = await fetch(`${API_BASE_URL}/playlist/retry/stream`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify({ playlist_url: playlistUrl }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Failed to retry playlist');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onProgress(data);
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  },

  generateVisualization: async (videoId, question, answer, token) => {
    const response = await fetch(`${API_BASE_URL}/visualize`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify({ video_id: videoId, question, answer }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    return response.json();
  },

  regenerateVisualization: async (videoId, query, category, failedCode, errorMessage, token) => {
    const response = await fetch(`${API_BASE_URL}/visualize/regenerate`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify({
        video_id: videoId,
        query: query,
        category: category,
        failed_code: failedCode,
        error_message: errorMessage
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    return response.json();
  },
};