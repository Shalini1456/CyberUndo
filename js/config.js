// CyberUndo Frontend Configuration

const CONFIG = {
  // Default to live Render backend; fallback to local if needed
  DEFAULT_API_BASE: "https://cyberundo.onrender.com/api",
  LOCAL_API_BASE: "http://127.0.0.1:5000/api",
  
  // Storage keys
  TOKEN_KEY: "cyberundo_auth_token",
  USER_KEY: "cyberundo_user_data",
  API_URL_KEY: "cyberundo_custom_api_url",

  getApiBase() {
    return localStorage.getItem(this.API_URL_KEY) || this.DEFAULT_API_BASE;
  },

  setApiBase(url) {
    if (url) {
      localStorage.setItem(this.API_URL_KEY, url.trim().replace(/\/$/, ""));
    } else {
      localStorage.removeItem(this.API_URL_KEY);
    }
  }
};

window.CONFIG = CONFIG;
