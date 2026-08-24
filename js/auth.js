// CyberUndo Auth Manager

class AuthManager {
  constructor() {
    this.currentUser = null;
    this.init();
  }

  init() {
    const savedUser = localStorage.getItem(CONFIG.USER_KEY);
    if (savedUser) {
      try {
        this.currentUser = JSON.parse(savedUser);
      } catch (e) {
        this.currentUser = null;
      }
    }
  }

  isAuthenticated() {
    return !!apiService.getToken() && !!this.currentUser;
  }

  getUser() {
    return this.currentUser;
  }

  async verifySession() {
    if (!apiService.getToken()) {
      this.updateAuthUI();
      return false;
    }

    try {
      const res = await apiService.getMe();
      if (res.success && res.data && res.data.user) {
        this.currentUser = res.data.user;
        localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(this.currentUser));
        this.updateAuthUI();
        return true;
      }
    } catch (err) {
      console.warn("Session verification failed, logging out:", err.message);
      this.logout(false);
    }
    this.updateAuthUI();
    return false;
  }

  async login(email, password) {
    const res = await apiService.login(email, password);
    if (res.success && res.data) {
      this.currentUser = res.data.user;
      this.updateAuthUI();
      window.toast && window.toast.success(`Welcome back, ${this.currentUser.name}!`);
      // Reload user files
      if (window.filesManager) {
        window.filesManager.loadFiles();
      }
    }
    return res;
  }

  async register(name, email, password) {
    const res = await apiService.register(name, email, password);
    if (res.success) {
      window.toast && window.toast.success("Account created successfully! Logging you in...");
      // Auto-login after registration
      return await this.login(email, password);
    }
    return res;
  }

  logout(showToast = true) {
    apiService.logout();
    this.currentUser = null;
    this.updateAuthUI();
    if (window.filesManager) {
      window.filesManager.clearFiles();
    }
    if (showToast) {
      window.toast && window.toast.info("Logged out successfully.");
    }
  }

  updateAuthUI() {
    const authGuestSection = document.getElementById("authGuestSection");
    const authUserSection = document.getElementById("authUserSection");
    const userDisplayName = document.getElementById("userDisplayName");
    const userAvatarText = document.getElementById("userAvatarText");
    const vaultAuthPrompt = document.getElementById("vaultAuthPrompt");
    const vaultContent = document.getElementById("vaultContent");

    if (this.isAuthenticated()) {
      if (authGuestSection) authGuestSection.classList.add("hidden");
      if (authUserSection) authUserSection.classList.remove("hidden");
      if (userDisplayName) userDisplayName.innerText = this.currentUser.name || this.currentUser.email;
      if (userAvatarText) {
        const initials = (this.currentUser.name || "U")
          .split(" ")
          .map(n => n[0])
          .join("")
          .toUpperCase()
          .slice(0, 2);
        userAvatarText.innerText = initials;
      }
      if (vaultAuthPrompt) vaultAuthPrompt.classList.add("hidden");
      if (vaultContent) vaultContent.classList.remove("hidden");
    } else {
      if (authGuestSection) authGuestSection.classList.remove("hidden");
      if (authUserSection) authUserSection.classList.add("hidden");
      if (vaultAuthPrompt) vaultAuthPrompt.classList.remove("hidden");
      if (vaultContent) vaultContent.classList.add("hidden");
    }
  }
}

window.authManager = new AuthManager();
