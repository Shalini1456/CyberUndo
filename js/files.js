// CyberUndo Live File Vault Manager

class FilesManager {
  constructor() {
    this.files = [];
    this.selectedFile = null;
    this.isLoading = false;
  }

  init() {
    this.setupEventListeners();
    if (authManager.isAuthenticated()) {
      this.loadFiles();
    }
  }

  setupEventListeners() {
    const dropZone = document.getElementById("fileDropZone");
    const fileInput = document.getElementById("fileInputElement");

    if (dropZone && fileInput) {
      dropZone.addEventListener("click", () => fileInput.click());

      dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("border-cyan-400", "bg-cyan-950/20");
      });

      dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("border-cyan-400", "bg-cyan-950/20");
      });

      dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("border-cyan-400", "bg-cyan-950/20");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          this.handleFileUpload(e.dataTransfer.files[0]);
        }
      });

      fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
          this.handleFileUpload(e.target.files[0]);
          e.target.value = "";
        }
      });
    }
  }

  async handleFileUpload(file) {
    if (!authManager.isAuthenticated()) {
      window.toast && window.toast.error("Please login or create an account to upload files.");
      window.openAuthModal("login");
      return;
    }

    // Client-side size check (16MB)
    const maxBytes = 16 * 1024 * 1024;
    if (file.size > maxBytes) {
      window.toast && window.toast.error("File size exceeds maximum allowed limit (16MB).");
      return;
    }

    const uploadProgress = document.getElementById("uploadProgress");
    const uploadProgressBar = document.getElementById("uploadProgressBar");
    const uploadStatusText = document.getElementById("uploadStatusText");
    const dropZoneContent = document.getElementById("dropZoneContent");

    try {
      if (uploadProgress) uploadProgress.classList.remove("hidden");
      if (dropZoneContent) dropZoneContent.classList.add("opacity-30", "pointer-events-none");
      if (uploadStatusText) uploadStatusText.innerText = `Encrypting & Uploading ${file.name}...`;
      if (uploadProgressBar) uploadProgressBar.style.width = "60%";

      const res = await apiService.uploadFile(file);

      if (uploadProgressBar) uploadProgressBar.style.width = "100%";
      soundEngine.play("success");
      window.toast && window.toast.success(`"${file.name}" uploaded & encrypted successfully!`);

      // Refresh file list and automatically select newly uploaded file for KillSwitch demo
      await this.loadFiles();
      if (res.data && res.data.file) {
        this.selectFile(res.data.file);
      }
    } catch (err) {
      console.error("Upload error:", err);
      soundEngine.play("threat");
      window.toast && window.toast.error(err.message || "Failed to upload file.");
    } finally {
      setTimeout(() => {
        if (uploadProgress) uploadProgress.classList.add("hidden");
        if (dropZoneContent) dropZoneContent.classList.remove("opacity-30", "pointer-events-none");
        if (uploadProgressBar) uploadProgressBar.style.width = "0%";
      }, 500);
    }
  }

  async loadFiles() {
    if (!authManager.isAuthenticated()) {
      this.clearFiles();
      return;
    }

    this.isLoading = true;
    this.renderLoading();

    try {
      const res = await apiService.listFiles();
      if (res.success && res.data && Array.isArray(res.data.files)) {
        this.files = res.data.files;
        this.renderFilesList();

        // If user has files, select the latest uploaded file; otherwise clear selection
        if (this.files.length > 0) {
          this.selectFile(this.files[0]);
        } else {
          this.selectFile(null);
        }
      }
    } catch (err) {
      console.error("Error loading files:", err);
      this.renderError(err.message);
    } finally {
      this.isLoading = false;
    }
  }

  clearFiles() {
    this.files = [];
    this.selectedFile = null;
    this.renderFilesList();
    if (window.killSwitchManager) {
      window.killSwitchManager.setFile(null);
    }
  }

  selectFile(file) {
    this.selectedFile = file || null;
    this.renderFilesList(); // Re-render to update active highlight

    // Update the Killswitch / Share section with the selected real file
    if (window.killSwitchManager) {
      window.killSwitchManager.setFile(this.selectedFile);
    }
  }

  async downloadFile(fileId, filename, e) {
    if (e) e.stopPropagation();
    try {
      window.toast && window.toast.info(`Starting secure download: ${filename}...`);
      await apiService.downloadFile(fileId, filename);
      soundEngine.play("click");
    } catch (err) {
      console.error("Download error:", err);
      window.toast && window.toast.error(err.message || "Download failed.");
    }
  }

  renderLoading() {
    const listContainer = document.getElementById("vaultFilesList");
    if (!listContainer) return;
    listContainer.innerHTML = `
      <div class="flex items-center justify-center py-10 text-slate-400 gap-3 font-mono text-xs">
        <span class="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></span>
        <span>Fetching secure file vault...</span>
      </div>
    `;
  }

  renderError(msg) {
    const listContainer = document.getElementById("vaultFilesList");
    if (!listContainer) return;
    listContainer.innerHTML = `
      <div class="p-4 rounded-xl bg-red-950/30 border border-red-500/30 text-center text-xs font-mono text-red-400">
        <p class="font-bold mb-1">Failed to load files</p>
        <p class="text-slate-400 mb-3 text-[11px]">${msg}</p>
        <button onclick="filesManager.loadFiles()" class="px-3 py-1.5 rounded-lg bg-red-900/50 hover:bg-red-800 text-white font-sans text-xs transition">
          Retry
        </button>
      </div>
    `;
  }

  renderFilesList() {
    const listContainer = document.getElementById("vaultFilesList");
    const filesCountBadge = document.getElementById("vaultFilesCount");
    if (!listContainer) return;

    if (filesCountBadge) {
      filesCountBadge.innerText = `${this.files.length} file${this.files.length === 1 ? "" : "s"}`;
    }

    if (this.files.length === 0) {
      listContainer.innerHTML = `
        <div class="text-center py-10 px-4 border border-dashed border-slate-800 rounded-xl">
          <i data-lucide="shield-check" class="w-8 h-8 text-slate-600 mx-auto mb-2"></i>
          <p class="text-xs font-bold text-slate-300 font-mono">No Files in Vault</p>
          <p class="text-[11px] text-slate-500 mt-1 max-w-xs mx-auto">
            Upload your first sensitive PDF, document, or archive above to arm CyberUndo protection.
          </p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    listContainer.innerHTML = this.files.map(file => {
      const isSelected = this.selectedFile && this.selectedFile.id === file.id;
      const formattedDate = file.created_at ? new Date(file.created_at).toLocaleDateString(undefined, {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      }) : "Recently uploaded";

      return `
        <div 
          onclick="filesManager.selectFile(${JSON.stringify(file).replace(/"/g, '&quot;')})"
          class="group p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
            isSelected 
              ? 'bg-cyan-950/40 border-cyan-500/60 shadow-md shadow-cyan-500/10' 
              : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
          }">
          
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
              isSelected ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'bg-slate-800 text-slate-400 border border-slate-700'
            }">
              <i data-lucide="file-text" class="w-5 h-5"></i>
            </div>
            
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <p class="font-mono text-xs font-bold text-white truncate max-w-[160px] sm:max-w-[220px]">${file.filename}</p>
                <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-semibold ${
                  file.status === 'active' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
                }">${file.status.toUpperCase()}</span>
              </div>
              <p class="text-[10px] text-slate-500 font-mono mt-0.5">${formattedDate}</p>
            </div>
          </div>

          <div class="flex items-center gap-2 flex-shrink-0">
            ${isSelected ? `
              <span class="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-500/30 hidden sm:inline-block">
                Armed
              </span>
            ` : ''}

            <!-- Download Button -->
            <button 
              onclick="filesManager.downloadFile(${file.id}, '${file.filename.replace(/'/g, "\\'")}', event)"
              class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition"
              title="Download file">
              <i data-lucide="download" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>
      `;
    }).join("");

    lucide.createIcons();
  }
}

window.filesManager = new FilesManager();
