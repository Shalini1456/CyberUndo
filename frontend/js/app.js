// CyberUndo Main Application Controller

// Toast Notification Engine
class Toast {
  constructor() {
    this.container = document.getElementById("toastContainer");
  }

  show(message, type = "info", duration = 4000) {
    if (!this.container) {
      this.container = document.createElement("div");
      this.container.id = "toastContainer";
      document.body.appendChild(this.container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let iconName = "info";
    if (type === "success") iconName = "check-circle";
    if (type === "error") iconName = "alert-circle";

    toast.innerHTML = `
      <i data-lucide="${iconName}" class="w-4 h-4 flex-shrink-0"></i>
      <span class="flex-1 font-medium">${message}</span>
      <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-white transition">
        <i data-lucide="x" class="w-3.5 h-3.5"></i>
      </button>
    `;

    this.container.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px) scale(0.95)";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  success(msg) { this.show(msg, "success"); }
  error(msg) { this.show(msg, "error", 5000); }
  info(msg) { this.show(msg, "info"); }
}

window.toast = new Toast();

// Modal Functions
window.openAuthModal = function(mode = "login") {
  const modal = document.getElementById("authModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.classList.add("flex");
  window.switchAuthTab(mode);
};

window.closeAuthModal = function() {
  const modal = document.getElementById("authModal");
  if (!modal) return;
  modal.classList.add("hidden");
  modal.classList.remove("flex");
};

window.switchAuthTab = function(mode) {
  const loginTab = document.getElementById("tabLoginBtn");
  const registerTab = document.getElementById("tabRegisterBtn");
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  const modalTitle = document.getElementById("authModalTitle");

  if (mode === "login") {
    loginTab.className = "flex-1 py-2 font-mono text-xs font-bold border-b-2 border-cyan-400 text-cyan-300";
    registerTab.className = "flex-1 py-2 font-mono text-xs font-semibold text-slate-400 hover:text-slate-200 border-b-2 border-transparent";
    loginForm.classList.remove("hidden");
    registerForm.classList.add("hidden");
    if (modalTitle) modalTitle.innerText = "Access CyberUndo Security Gateway";
  } else {
    registerTab.className = "flex-1 py-2 font-mono text-xs font-bold border-b-2 border-cyan-400 text-cyan-300";
    loginTab.className = "flex-1 py-2 font-mono text-xs font-semibold text-slate-400 hover:text-slate-200 border-b-2 border-transparent";
    registerForm.classList.remove("hidden");
    loginForm.classList.add("hidden");
    if (modalTitle) modalTitle.innerText = "Create CyberUndo Account";
  }
};

window.openSettingsModal = function() {
  const modal = document.getElementById("settingsModal");
  const input = document.getElementById("customApiInput");
  if (input) input.value = CONFIG.getApiBase();
  if (modal) {
    modal.classList.remove("hidden");
    modal.classList.add("flex");
  }
};

window.closeSettingsModal = function() {
  const modal = document.getElementById("settingsModal");
  if (modal) {
    modal.classList.add("hidden");
    modal.classList.remove("flex");
  }
};

window.saveApiSettings = function() {
  const input = document.getElementById("customApiInput");
  if (input) {
    const val = input.value.trim();
    CONFIG.setApiBase(val);
    window.toast.success(`API URL set to: ${CONFIG.getApiBase()}`);
    window.closeSettingsModal();
    window.checkBackendHealth();
  }
};

window.resetApiSettings = function() {
  CONFIG.setApiBase(null);
  const input = document.getElementById("customApiInput");
  if (input) input.value = CONFIG.getApiBase();
  window.toast.info("Reset to default public Render backend.");
  window.closeSettingsModal();
  window.checkBackendHealth();
};

// Top Navigation Tab Switching
window.switchMainTab = function(tabName) {
  const tabDashboard = document.getElementById("tabDashboardContent");
  const tabVault = document.getElementById("tabVaultContent");
  const tabTelemetry = document.getElementById("tabTelemetryContent");
  const btnDashboard = document.getElementById("navBtnDashboard");
  const btnVault = document.getElementById("navBtnVault");
  const btnTelemetry = document.getElementById("navBtnTelemetry");

  [tabDashboard, tabVault, tabTelemetry].forEach(el => el && el.classList.add("hidden"));
  [btnDashboard, btnVault, btnTelemetry].forEach(btn => {
    if (btn) {
      btn.classList.remove("bg-cyan-500/20", "text-cyan-300", "border-cyan-500/40");
      btn.classList.add("bg-slate-900/60", "text-slate-400", "border-slate-800");
    }
  });

  if (tabName === "dashboard") {
    if (tabDashboard) tabDashboard.classList.remove("hidden");
    if (btnDashboard) {
      btnDashboard.classList.add("bg-cyan-500/20", "text-cyan-300", "border-cyan-500/40");
      btnDashboard.classList.remove("bg-slate-900/60", "text-slate-400", "border-slate-800");
    }
  } else if (tabName === "vault") {
    if (tabVault) tabVault.classList.remove("hidden");
    if (btnVault) {
      btnVault.classList.add("bg-cyan-500/20", "text-cyan-300", "border-cyan-500/40");
      btnVault.classList.remove("bg-slate-900/60", "text-slate-400", "border-slate-800");
    }
  } else if (tabName === "telemetry") {
    if (tabTelemetry) tabTelemetry.classList.remove("hidden");
    if (btnTelemetry) {
      btnTelemetry.classList.add("bg-cyan-500/20", "text-cyan-300", "border-cyan-500/40");
      btnTelemetry.classList.remove("bg-slate-900/60", "text-slate-400", "border-slate-800");
    }
  }
  lucide.createIcons();
};

// Check Backend Health
window.checkBackendHealth = async function() {
  const pillText = document.getElementById("topStatusText");
  const pillDot = document.getElementById("topStatusDot");
  const apiEndpointDisplay = document.getElementById("apiEndpointDisplay");

  if (apiEndpointDisplay) {
    apiEndpointDisplay.innerText = CONFIG.getApiBase();
  }

  try {
    const res = await apiService.checkHealth();
    if (res.success) {
      if (pillText) pillText.innerText = "BACKEND LIVE (HTTP 200)";
      if (pillDot) pillDot.className = "w-2 h-2 rounded-full bg-emerald-400 animate-pulse";
    }
  } catch (err) {
    if (pillText) pillText.innerText = "BACKEND OFFLINE / CONNECTING";
    if (pillDot) pillDot.className = "w-2 h-2 rounded-full bg-amber-400 animate-pulse";
    console.warn("Backend health check failed:", err.message);
  }
};

// Audio toggle
window.toggleAudio = function() {
  const isEnabled = soundEngine.toggle();
  const soundIcon = document.getElementById("soundIcon");
  if (soundIcon) {
    soundIcon.setAttribute("data-lucide", isEnabled ? "volume-2" : "volume-x");
    lucide.createIcons();
  }
  window.toast && window.toast.info(`Audio feedback ${isEnabled ? 'enabled' : 'muted'}`);
};

// Global Handlers
window.handleShareFile = () => killSwitchManager.handleShareFile();
window.handleRevokeAccess = () => killSwitchManager.handleRevokeAccess();
window.resetPrototype = () => killSwitchManager.reset();

// Form Submissions
document.addEventListener("DOMContentLoaded", () => {
  // Auth Form Handlers
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");

  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("loginEmail").value.trim();
      const password = document.getElementById("loginPassword").value;
      const submitBtn = loginForm.querySelector("button[type='submit']");

      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="inline-block animate-spin mr-2">⟳</span> Authenticating...`;
        await authManager.login(email, password);
        window.closeAuthModal();
        loginForm.reset();
      } catch (err) {
        soundEngine.play("threat");
        window.toast.error(err.message || "Login failed");
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `LOGIN`;
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("regName").value.trim();
      const email = document.getElementById("regEmail").value.trim();
      const password = document.getElementById("regPassword").value;
      const submitBtn = registerForm.querySelector("button[type='submit']");

      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="inline-block animate-spin mr-2">⟳</span> Registering...`;
        await authManager.register(name, email, password);
        window.closeAuthModal();
        registerForm.reset();
      } catch (err) {
        soundEngine.play("threat");
        window.toast.error(err.message || "Registration failed");
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `CREATE ACCOUNT`;
      }
    });
  }

  // Initialize Subsystems
  killSwitchManager.init();
  authManager.verifySession();
  filesManager.init();
  window.checkBackendHealth();
  lucide.createIcons();
});
