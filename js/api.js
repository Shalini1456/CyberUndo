// CyberUndo API Client — Connects ONLY to verified backend routes

class ApiService {
  constructor() {
    this.token = localStorage.getItem(CONFIG.TOKEN_KEY) || null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem(CONFIG.TOKEN_KEY, token);
    } else {
      localStorage.removeItem(CONFIG.TOKEN_KEY);
    }
  }

  getToken() {
    return this.token || localStorage.getItem(CONFIG.TOKEN_KEY);
  }

  getHeaders(isMultipart = false) {
    const headers = {};
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    if (!isMultipart) {
      headers["Content-Type"] = "application/json";
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${CONFIG.getApiBase()}${endpoint}`;
    const defaultHeaders = this.getHeaders(options.body instanceof FormData);

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {})
      }
    };

    try {
      const response = await fetch(url, config);
      
      // Handle file download binary responses
      if (options.isBlob) {
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          const error = new Error(errData.message || `Download failed (HTTP ${response.status})`);
          error.status = response.status;
          error.data = errData;
          throw error;
        }
        return await response.blob();
      }

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const errorMsg = data && data.message ? data.message : `HTTP Error ${response.status}: ${response.statusText}`;
        const error = new Error(errorMsg);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        throw new Error("Unable to connect to backend server. Please verify the backend is running and CORS is configured.");
      }
      throw err;
    }
  }

  // ==========================================
  // 1. HEALTH CHECK
  // ==========================================
  async checkHealth() {
    return this.request("/health", { method: "GET" });
  }

  // ==========================================
  // 2. AUTHENTICATION ENDPOINTS
  // ==========================================
  async register(name, email, password) {
    return this.request("/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password })
    });
  }

  async login(email, password) {
    const res = await this.request("/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });

    if (res.success && res.data && res.data.token) {
      this.setToken(res.data.token);
      localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(res.data.user));
    }
    return res;
  }

  async getMe() {
    return this.request("/auth/me", { method: "GET" });
  }

  logout() {
    this.setToken(null);
    localStorage.removeItem(CONFIG.USER_KEY);
  }

  // ==========================================
  // 3. FILE MANAGEMENT ENDPOINTS
  // ==========================================
  async uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    return this.request("/files/upload", {
      method: "POST",
      body: formData
    });
  }

  async listFiles() {
    return this.request("/files", { method: "GET" });
  }

  async getFile(fileId) {
    return this.request(`/files/${fileId}`, { method: "GET" });
  }

  async downloadFile(fileId, filename) {
    const blob = await this.request(`/files/${fileId}/download`, {
      method: "GET",
      isBlob: true
    });

    // Trigger browser download
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filename || `file_${fileId}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    a.remove();
  }

  // ==========================================
  // 4. SECURE SHARING & REVOKE (MEMBER 2)
  // ==========================================
  async createShare({ fileId, recipientEmail, expiry = "24h", allowDownload = true }) {
    return this.request("/shares", {
      method: "POST",
      body: JSON.stringify({
        file_id: fileId,
        recipient_email: recipientEmail,
        expiry: expiry,
        allow_download: allowDownload
      })
    });
  }

  async listShares(fileId = null) {
    const url = fileId ? `/shares?file_id=${fileId}` : "/shares";
    return this.request(url, { method: "GET" });
  }

  async getShare(token) {
    return this.request(`/shares/${token}`, { method: "GET" });
  }

  async recordShareView(token) {
    return this.request(`/shares/${token}/view`, { method: "POST" });
  }

  async downloadSharedFile(token, filename) {
    const blob = await this.request(`/shares/${token}/download`, {
      method: "GET",
      isBlob: true
    });

    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = downloadUrl;
    a.download = filename || `shared_document`;
    a.target = "_blank";
    document.body.appendChild(a);
    a.click();

    // Defer revokeObjectURL so mobile and desktop browsers have time to process download
    setTimeout(() => {
      try {
        window.URL.revokeObjectURL(downloadUrl);
        a.remove();
      } catch (e) {}
    }, 10000);
  }

  async revokeShare(tokenOrId) {
    return this.request(`/shares/${tokenOrId}/revoke`, { method: "POST" });
  }

  async revokeAllShares(fileId = null) {
    return this.request("/shares/revoke-all", {
      method: "POST",
      body: JSON.stringify(fileId ? { file_id: fileId } : {})
    });
  }

  // ==========================================
  // 5. MEMBER 4: RISK ENGINE & BLAST RADIUS
  // ==========================================
  async analyzeRisk(payload) {
    return this.request("/risk/analyze", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async analyzeBlastRadius(payload) {
    return this.request("/blast-radius/analyze", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async logActivity(payload) {
    return this.request("/activity/log", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async getFileActivity(fileId) {
    return this.request(`/activity/${fileId}`, { method: "GET" });
  }
}

window.apiService = new ApiService();

