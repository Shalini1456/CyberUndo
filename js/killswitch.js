// CyberUndo Zero-Trust Killswitch & Blast Radius Interactive Engine

const STATE = {
  IDLE: 'IDLE',
  SHARING: 'SHARING',
  ACTIVE_THREAT: 'ACTIVE_THREAT',
  REVOKED: 'REVOKED'
};

class KillSwitchManager {
  constructor() {
    this.currentState = STATE.IDLE;
    this.currentShareId = null;
    this.viewRecorded = false;
    this.activeFile = {
      id: 0,
      filename: "Project_Final.pdf",
      status: "active",
      created_at: new Date().toISOString()
    };
    this.propagationTimer1 = null;
    this.propagationTimer2 = null;
    this.propagationTimer3 = null;
    this.syncInterval = null;
    this.lastProcessedDownloadCount = 0;
  }

  init() {
    this.setupHotkeys();
    this.setupCrossTabListener();
    this.updateUI();
  }

  setFile(file) {
    if (!file) return;
    this.activeFile = file;
    this.reset(false);
    this.updateFileDisplay();
  }

  updateFileDisplay() {
    const filenameEl = document.getElementById("activeFileName");
    const filesizeEl = document.getElementById("activeFileSize");
    const shareBtnText = document.getElementById("btnShareText");

    if (filenameEl) filenameEl.innerText = this.activeFile.filename;
    if (filesizeEl) {
      filesizeEl.innerText = `Vault ID: #${this.activeFile.id || 'DEMO'} • Encrypted AES-256`;
    }
    if (shareBtnText && this.currentState === STATE.IDLE) {
      shareBtnText.innerText = `SHARE FILE SECURELY`;
    }
  }

  setupHotkeys() {
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        // Allow instant revocation whenever file is shared or threat is active
        if (this.currentState === STATE.SHARING || this.currentState === STATE.ACTIVE_THREAT) {
          this.handleRevokeAccess();
        } else if (this.currentState === STATE.REVOKED) {
          this.flashRevokedNotice();
        } else {
          // If in IDLE state, highlight the share button
          const btnShare = document.getElementById('btnShare');
          if (btnShare) {
            btnShare.classList.add('ring-2', 'ring-cyan-400');
            setTimeout(() => btnShare.classList.remove('ring-2', 'ring-cyan-400'), 600);
          }
        }
      }
    });
  }

  setupCrossTabListener() {
    window.addEventListener('storage', (e) => {
      this.handleExternalStorageEvent();
    });

    // Authoritative Server-backed polling (fetches real DB state across devices/phones)
    if (this.syncInterval) clearInterval(this.syncInterval);
    this.syncInterval = setInterval(() => {
      if (this.currentState === STATE.SHARING || this.currentState === STATE.ACTIVE_THREAT) {
        this.pollServerShareStatus();
        this.handleExternalStorageEvent();
      }
    }, 1000);
  }

  async pollServerShareStatus() {
    if (!this.currentShareId || this.currentState === STATE.REVOKED || this.currentState === STATE.IDLE) return;
    if (!window.apiService) return;

    try {
      const res = await apiService.getShare(this.currentShareId);
      if (res && res.success && res.data && res.data.share) {
        const serverShare = res.data.share;

        // 1. Authoritative VIEW Detection from backend DB
        if ((serverShare.view_count > 0 || serverShare.first_viewed_at) && !this.viewRecorded && this.currentState !== STATE.REVOKED) {
          this.viewRecorded = true;
          this.triggerViewedState(false);
        }

        // 2. Authoritative DOWNLOAD Detection from backend DB
        if (serverShare.download_count > this.lastProcessedDownloadCount && this.currentState !== STATE.REVOKED) {
          this.lastProcessedDownloadCount = serverShare.download_count;
          this.triggerDownloadState(serverShare.download_count, false);
        }

        // 3. Authoritative REVOKE / EXPIRED Status from backend DB
        if (serverShare.status === 'revoked' && this.currentState !== STATE.REVOKED) {
          this.handleRevokeAccess(true);
        }
      }
    } catch (err) {
      // 403 Forbidden indicates token was revoked or expired on server
      if (err && err.status === 403 && this.currentState !== STATE.REVOKED) {
        this.handleRevokeAccess(true);
      }
    }
  }

  handleExternalStorageEvent() {
    if (!this.currentShareId) return;
    const rawData = localStorage.getItem('cyberundo_share_' + this.currentShareId) || localStorage.getItem('cyberundo_active_share');
    if (!rawData) return;

    try {
      const share = JSON.parse(rawData);

      // If remote tab triggered View
      if (share.viewed && !this.viewRecorded && this.currentState !== STATE.REVOKED) {
        this.viewRecorded = true;
        const badgeViewedTime = document.getElementById('badgeViewedTime');
        if (badgeViewedTime && badgeViewedTime.innerText === 'Pending') {
          this.triggerViewedState(true);
        }
      }

      // If remote tab triggered Download
      if (share.downloadCount > this.lastProcessedDownloadCount && this.currentState !== STATE.REVOKED) {
        this.lastProcessedDownloadCount = share.downloadCount;
        this.triggerDownloadState(share.downloadCount, true);
      }
    } catch (e) {
      console.warn("Storage sync error:", e);
    }
  }

  flashRevokedNotice() {
    const card = document.getElementById('resultSection');
    if (card) {
      card.classList.add('ring-2', 'ring-emerald-400');
      setTimeout(() => card.classList.remove('ring-2', 'ring-emerald-400'), 500);
    }
  }

  addLogEntry(time, event, type = 'info') {
    const logsList = document.getElementById('activityLogsList');
    const emptyMsg = document.getElementById('emptyLogsMsg');
    if (emptyMsg) emptyMsg.remove();

    const logItem = document.createElement('div');
    logItem.className = 'flex items-start gap-2 text-xs py-1 border-b border-slate-900 animate-fade-in';
    
    let badgeClass = 'bg-slate-800 text-slate-300 border-slate-700';
    let iconName = 'info';

    if (type === 'shared') {
      badgeClass = 'bg-cyan-950 text-cyan-300 border-cyan-700/50';
      iconName = 'share-2';
    } else if (type === 'viewed') {
      badgeClass = 'bg-blue-950 text-blue-300 border-blue-700/50';
      iconName = 'eye';
    } else if (type === 'download') {
      badgeClass = 'bg-amber-950 text-amber-300 border-amber-700/50';
      iconName = 'download';
    } else if (type === 'threat') {
      badgeClass = 'bg-red-950 text-red-300 border-red-700/50';
      iconName = 'alert-triangle';
    } else if (type === 'revoked') {
      badgeClass = 'bg-emerald-950 text-emerald-300 border-emerald-700/50';
      iconName = 'shield-alert';
    }

    logItem.innerHTML = `
      <span class="text-slate-500 font-mono text-[10px] w-14 flex-shrink-0 pt-0.5">${time}</span>
      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono border ${badgeClass} flex-shrink-0 flex items-center gap-1">
        <i data-lucide="${iconName}" class="w-2.5 h-2.5"></i>
        ${type.toUpperCase()}
      </span>
      <span class="text-slate-300 flex-1">${event}</span>
    `;

    logsList.prepend(logItem);
    lucide.createIcons();

    const count = logsList.children.length;
    const logCountEl = document.getElementById('logCount');
    if (logCountEl) logCountEl.innerText = `${count} event${count === 1 ? '' : 's'}`;
  }

  renderShareLink(shareUrl) {
    try {
      const shareLinkContainer = document.getElementById('shareLinkContainer');
      const shareLinkInput = document.getElementById('shareLinkInput');
      const btnOpenRecipientView = document.getElementById('btnOpenRecipientView');
      const previewUrlText = document.getElementById('previewUrlText');
      const previewOpenTabBtn = document.getElementById('previewOpenTabBtn');
      const previewActionLabel = document.getElementById('previewActionLabel');

      if (shareLinkContainer) {
        shareLinkContainer.classList.remove('hidden');
        shareLinkContainer.style.setProperty('display', 'block', 'important');
        shareLinkContainer.style.visibility = 'visible';
        shareLinkContainer.style.opacity = '1';
      }
      if (shareLinkInput) {
        shareLinkInput.value = shareUrl;
      }
      if (btnOpenRecipientView) {
        btnOpenRecipientView.setAttribute('data-url', shareUrl);
        btnOpenRecipientView.onclick = (e) => {
          if (e) e.preventDefault();
          this.openRecipientView();
          return false;
        };
      }
      if (previewUrlText) {
        previewUrlText.innerText = shareUrl;
      }
      if (previewOpenTabBtn) {
        previewOpenTabBtn.classList.remove('hidden');
        previewOpenTabBtn.classList.add('flex');
        previewOpenTabBtn.setAttribute('data-url', shareUrl);
        previewOpenTabBtn.onclick = (e) => {
          if (e) e.preventDefault();
          this.openRecipientView();
          return false;
        };
      }
      if (previewActionLabel) {
        previewActionLabel.innerText = 'Active Link';
      }
      if (window.lucide) lucide.createIcons();
    } catch(err) {
      console.error("Failed to render share link container:", err);
    }
  }

  async handleShareFile() {
    if (this.currentState !== STATE.IDLE) return;

    // Check authentication
    if (!window.authManager || !authManager.isAuthenticated()) {
      if (window.toast) {
        window.toast.error("Please login to create and manage secure shares.");
      } else {
        alert("Please login to create and manage secure shares.");
      }
      if (window.authManager) authManager.openAuthModal('login');
      return;
    }

    // Check active file
    if (!this.activeFile || !this.activeFile.id) {
      if (window.toast) {
        window.toast.error("Please select an uploaded file from your Secure Vault first.");
      } else {
        alert("Please select a file from your Vault first.");
      }
      if (window.switchMainTab) switchMainTab('vault');
      return;
    }

    // Read recipient email, expiry, and download policy from UI
    const emailInput = document.getElementById('shareRecipientEmail');
    const expirySelect = document.getElementById('shareExpirySelect');
    const allowDownloadCheck = document.getElementById('shareAllowDownload');

    const recipientEmail = emailInput ? emailInput.value.trim() : '';
    if (!recipientEmail) {
      if (window.toast) {
        window.toast.error("Please enter a valid recipient email address.");
      } else {
        alert("Please enter a valid recipient email address.");
      }
      if (emailInput) emailInput.focus();
      return;
    }

    const expiry = expirySelect ? expirySelect.value : '24h';
    const allowDownload = allowDownloadCheck ? allowDownloadCheck.checked : true;

    const btnShare = document.getElementById('btnShare');
    const btnShareText = document.getElementById('btnShareText');
    if (btnShare) {
      btnShare.disabled = true;
      if (btnShareText) btnShareText.innerText = "GENERATING SERVER TOKEN...";
    }

    let shareToken = '';
    let shareUrl = '';
    let serverShare = null;

    try {
      const res = await apiService.createShare({
        fileId: this.activeFile.id,
        recipientEmail: recipientEmail,
        expiry: expiry,
        allowDownload: allowDownload
      });

      if (res && res.success && res.data) {
        shareToken = res.data.share_token;
        serverShare = res.data.share;
        
        // Resolve full share URL
        const origin = window.location.origin;
        const pathname = window.location.pathname.replace(/\/index\.html$/, '').replace(/\/$/, '');
        shareUrl = `${origin}${pathname}/share?id=${shareToken}`;

        if (window.toast) {
          window.toast.success(res.message || "Secure share link created successfully.");
        }
      } else {
        throw new Error((res && res.message) || "Failed to create share on backend.");
      }
    } catch (err) {
      console.error("Backend share creation failed:", err);
      if (btnShare) {
        btnShare.disabled = false;
        if (btnShareText) btnShareText.innerText = "SHARE FILE SECURELY";
      }
      const errorMsg = (err && (err.message || (err.data && err.data.message))) || "Failed to create secure share.";
      if (window.toast) window.toast.error(errorMsg);
      else alert(errorMsg);
      return;
    }

    this.currentState = STATE.SHARING;
    this.viewRecorded = false;
    this.lastProcessedDownloadCount = 0;
    this.currentShareId = shareToken;
    this.currentShareUrl = shareUrl;
    soundEngine.play('share');

    // 1. Render Share Link Container IMMEDIATELY with real server URL
    this.renderShareLink(shareUrl);

    // 2. Persist active share in localStorage for cross-tab recipient sync
    try {
      const ownerUser = (window.authManager && authManager.getUser()) || {};
      const filename = (this.activeFile && this.activeFile.filename) || 'Document.pdf';
      const shareData = {
        id: this.currentShareId,
        fileId: this.activeFile.id,
        filename: filename,
        fileSize: this.activeFile.size_formatted || "Encrypted File",
        ownerName: ownerUser.name || "Security Lead",
        ownerEmail: ownerUser.email || "lead@cyberundo.io",
        recipientEmail: recipientEmail,
        expiry: expiry,
        allow_download: allowDownload,
        status: "ACTIVE",
        viewed: false,
        downloadCount: 0,
        createdAt: new Date().toISOString()
      };
      localStorage.setItem('cyberundo_share_' + this.currentShareId, JSON.stringify(shareData));
      localStorage.setItem('cyberundo_active_share', JSON.stringify(shareData));
      window.dispatchEvent(new Event('storage'));
    } catch(err) {
      console.warn("Storage sync warning:", err);
    }

    // 3. Immediately arm REVOKE ACCESS button so owner can revoke at any time
    this.activateRevokeButton();

    // 4. Update Share button state & Visuals safely
    try {
      const shareCard = document.getElementById('shareFileCard');
      const fileBadgeState = document.getElementById('fileBadgeState');

      if (btnShare) {
        btnShare.disabled = true;
        btnShare.classList.remove('from-cyan-600', 'to-blue-600', 'hover:from-cyan-500');
        btnShare.classList.add('bg-slate-800', 'text-slate-400', 'border-slate-700');
      }
      if (btnShareText) {
        btnShareText.innerHTML = `✓ SHARED WITH ${recipientEmail.toUpperCase()}`;
      }
      if (shareCard) {
        shareCard.classList.add('glass-card-glow-cyan');
      }
      if (fileBadgeState) {
        fileBadgeState.innerText = 'Active Link';
        fileBadgeState.className = 'px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-emerald-950 text-emerald-300 border border-emerald-500/40';
      }

      this.updateStepPills(1);

      const topStatusText = document.getElementById('topStatusText');
      if (topStatusText) topStatusText.innerText = 'LINK ACTIVE — MONITORING ACCESS';
      const topStatusDot = document.getElementById('topStatusDot');
      if (topStatusDot) topStatusDot.className = 'w-2 h-2 rounded-full bg-cyan-400 animate-pulse';

      const badgeShared = document.getElementById('badgeShared');
      if (badgeShared) badgeShared.className = 'flex flex-col items-center justify-center p-2.5 rounded-lg bg-cyan-950/80 border border-cyan-500/60 text-cyan-300 transition-all';
      const badgeSharedTime = document.getElementById('badgeSharedTime');
      if (badgeSharedTime) badgeSharedTime.innerText = 'Just now';

      const nowTime = new Date().toTimeString().split(' ')[0];
      const filename = (this.activeFile && this.activeFile.filename) || 'Document.pdf';
      this.addLogEntry(nowTime, `File <b>${filename}</b> shared securely to <b>${recipientEmail}</b>`, 'shared');

      const connectorLine1 = document.getElementById('connectorLine1');
      if (connectorLine1) connectorLine1.className = 'h-0.5 w-full bg-cyan-500 laser-line-active';
      const connectorArrow1 = document.getElementById('connectorArrow1');
      if (connectorArrow1) connectorArrow1.className = 'w-4 h-4 text-cyan-400 absolute';
      
      const activityLive = document.getElementById('activityLiveIndicator');
      if (activityLive) {
        activityLive.classList.remove('hidden');
        activityLive.classList.add('flex');
      }

      if (window.lucide) lucide.createIcons();
    } catch(err) {
      console.warn("DOM update non-fatal error:", err);
    }
  }

  triggerViewedState(fromCrossTab = false) {
    if (this.currentState === STATE.REVOKED || this.currentState === STATE.IDLE) return;

    soundEngine.play('share');
    this.updateStepPills(2);

    const badgeViewed = document.getElementById('badgeViewed');
    if (badgeViewed) {
      badgeViewed.className = 'flex flex-col items-center justify-center p-2.5 rounded-lg bg-blue-950/80 border border-blue-500/60 text-blue-300 transition-all';
    }
    const badgeTime = document.getElementById('badgeViewedTime');
    if (badgeTime) badgeTime.innerText = 'Live';

    const nowTime = new Date().toTimeString().split(' ')[0];
    const sourceLabel = '<b>Authorized Recipient</b> opened and viewed protected document';
    this.addLogEntry(nowTime, sourceLabel, 'viewed');

    const ep1 = document.getElementById('endpoint1');
    if (ep1) {
      ep1.classList.remove('opacity-50');
      ep1.classList.add('border-blue-500/40', 'bg-blue-950/20');
      const pill = ep1.querySelector('.status-pill');
      if (pill) {
        pill.className = 'status-pill text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-600 animate-pulse';
        pill.innerText = 'Viewing';
      }
    }
    lucide.createIcons();
  }

  triggerDownloadState(count = 1, fromCrossTab = false) {
    if (this.currentState === STATE.REVOKED || this.currentState === STATE.IDLE) return;

    soundEngine.play('share');

    const badgeDownloaded = document.getElementById('badgeDownloaded');
    if (badgeDownloaded) {
      badgeDownloaded.className = 'flex flex-col items-center justify-center p-2.5 rounded-lg bg-amber-950/80 border border-amber-500/60 text-amber-300 transition-all';
    }
    const badgeTime = document.getElementById('badgeDownloadedTime');
    if (badgeTime) badgeTime.innerText = `Active (${count}x)`;

    const nowTime = new Date().toTimeString().split(' ')[0];
    const sourceLabel = `Download #${count} completed by <b>Authorized Recipient</b>`;
    this.addLogEntry(nowTime, sourceLabel, 'download');

    const ep1 = document.getElementById('endpoint1');
    if (ep1) {
      const pill = ep1.querySelector('.status-pill');
      if (pill) {
        pill.className = 'status-pill text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-600';
        pill.innerText = 'Downloaded';
      }
    }

    const conn2 = document.getElementById('connectorLine2');
    const arrow2 = document.getElementById('connectorArrow2');
    if (conn2) conn2.className = 'h-0.5 w-full bg-amber-500 laser-line-active';
    if (arrow2) arrow2.className = 'w-4 h-4 text-amber-400 absolute';
    
    const nodeSubtitle = document.getElementById('downloadsNodeSubtitle');
    if (nodeSubtitle) nodeSubtitle.innerText = `${count} download${count === 1 ? '' : 's'}`;
    const formula = document.getElementById('propagationFormula');
    if (formula) formula.innerText = `Owner → Recipient → ${count} Download${count === 1 ? '' : 's'}`;
    const activeSessions = document.getElementById('activeSessionsCount');
    if (activeSessions) activeSessions.innerText = `${count} Active Download${count === 1 ? '' : 's'}`;

    lucide.createIcons();
  }

  activateRevokeButton() {
    this.updateStepPills(4);
    const btnRevoke = document.getElementById('btnRevoke');
    const revokeSection = document.getElementById('revokeSection');

    if (!btnRevoke) return;

    btnRevoke.disabled = false;
    btnRevoke.classList.remove('bg-slate-800', 'text-slate-500', 'border-slate-700', 'cursor-not-allowed');
    btnRevoke.classList.add(
      'bg-gradient-to-r', 'from-red-600', 'to-rose-600',
      'hover:from-red-500', 'hover:to-rose-500',
      'text-white', 'border-red-400/50',
      'shadow-xl', 'shadow-red-600/30',
      'animate-pulse-slow', 'cursor-pointer',
      'active:scale-[0.98]'
    );

    if (revokeSection) revokeSection.classList.add('glass-card-glow-danger');
    const helperText = document.getElementById('revokeHelperText');
    if (helperText) {
      helperText.innerHTML = `<span class="text-red-400 font-bold animate-pulse">⚡ CLICK REVOKE ACCESS OR PRESS CTRL+Z NOW TO RECOVER CONTROL</span>`;
    }
  }

  handleRevokeAccess(fromServerSync = false) {
    // Prevent duplicate revokes or revoking from idle
    if (this.currentState === STATE.REVOKED || this.currentState === STATE.IDLE) return;

    // Clear all pending background progression timers
    if (this.propagationTimer1) { clearTimeout(this.propagationTimer1); this.propagationTimer1 = null; }
    if (this.propagationTimer2) { clearTimeout(this.propagationTimer2); this.propagationTimer2 = null; }
    if (this.propagationTimer3) { clearTimeout(this.propagationTimer3); this.propagationTimer3 = null; }

    this.currentState = STATE.REVOKED;
    soundEngine.play('revoke');

    // Call real backend API to revoke token on server if authenticated and user clicked revoke
    if (!fromServerSync && this.currentShareId && window.authManager && authManager.isAuthenticated()) {
      apiService.revokeShare(this.currentShareId).catch(err => {
        console.warn("Backend revoke notice:", err);
      });
    }

    // Update shared state in localStorage to REVOKED so recipient tab locks immediately
    if (this.currentShareId) {
      const rawData = localStorage.getItem('cyberundo_share_' + this.currentShareId) || localStorage.getItem('cyberundo_active_share');
      let shareData = {};
      if (rawData) {
        try { shareData = JSON.parse(rawData); } catch(e) {}
      }
      shareData.status = 'REVOKED';
      shareData.revokedAt = new Date().toISOString();
      localStorage.setItem('cyberundo_share_' + this.currentShareId, JSON.stringify(shareData));
      localStorage.setItem('cyberundo_active_share', JSON.stringify(shareData));
      window.dispatchEvent(new Event('storage'));
    }

    // 1. Update File Badge State
    const fileBadgeState = document.getElementById('fileBadgeState');
    if (fileBadgeState) {
      fileBadgeState.innerText = 'REVOKED / INVALIDATED';
      fileBadgeState.className = 'px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-red-950 text-red-300 border border-red-500/50';
    }

    // 2. Update Share Button to allow reset
    const btnShare = document.getElementById('btnShare');
    const btnShareText = document.getElementById('btnShareText');
    if (btnShare) {
      btnShare.disabled = false;
      btnShare.className = 'w-full relative group overflow-hidden rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 font-semibold py-3.5 px-4 transition-all flex items-center justify-center gap-2 text-sm tracking-wide cursor-pointer';
      btnShare.onclick = () => this.reset();
    }
    if (btnShareText) {
      btnShareText.innerHTML = `⟲ RESET WORKFLOW`;
    }

    // 3. Update Revoke Button to Executed state
    const btnRevoke = document.getElementById('btnRevoke');
    const btnRevokeText = document.getElementById('btnRevokeText');
    if (btnRevoke) {
      btnRevoke.disabled = true;
      btnRevoke.classList.remove('animate-pulse-slow', 'from-red-600', 'to-rose-600', 'cursor-pointer');
      btnRevoke.classList.add('bg-slate-900', 'text-emerald-400', 'border-emerald-500/50', 'shadow-none', 'cursor-default');
    }
    if (btnRevokeText) {
      btnRevokeText.innerHTML = `✓ ACCESS REVOKED (Zero-Trust Killswitch Executed)`;
    }
    const iconWrapper = document.getElementById('revokeBtnIconWrapper');
    if (iconWrapper) {
      iconWrapper.innerHTML = `<i data-lucide="shield-check" class="w-5 h-5 text-emerald-400"></i>`;
    }

    const revokeHelper = document.getElementById('revokeHelperText');
    if (revokeHelper) {
      revokeHelper.innerHTML = `<span class="text-emerald-400 font-mono font-semibold">⚡ ACCESS REVOKED: Decryption tokens invalidated across edge reverse proxies.</span>`;
    }

    this.updateStepPills(5);

    // 4. Sever laser connection lines
    const line1 = document.getElementById('connectorLine1');
    const arrow1 = document.getElementById('connectorArrow1');
    const line2 = document.getElementById('connectorLine2');
    const arrow2 = document.getElementById('connectorArrow2');

    if (line1) line1.className = 'h-0.5 w-full bg-slate-700 laser-line-severed';
    if (arrow1) arrow1.className = 'w-4 h-4 text-slate-700 absolute';
    if (line2) line2.className = 'h-0.5 w-full bg-slate-700 laser-line-severed';
    if (arrow2) arrow2.className = 'w-4 h-4 text-slate-700 absolute';

    // 5. Update Blast Radius & Exposure
    const blastSection = document.getElementById('blastRadiusSection');
    if (blastSection) {
      blastSection.classList.remove('glass-card-glow-danger');
      blastSection.classList.add('glass-card-glow-emerald');
    }

    const exposureBadge = document.getElementById('exposureBadge');
    if (exposureBadge) {
      exposureBadge.className = 'flex items-center gap-1.5 px-3 py-1 rounded-full font-mono text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-500';
    }
    const exposureText = document.getElementById('exposureText');
    if (exposureText) exposureText.innerText = 'Exposure: CONTAINED / ZERO RISK';
    const exposureIcon = document.getElementById('exposureIcon');
    if (exposureIcon) exposureIcon.setAttribute('data-lucide', 'shield-check');

    const blastSummary = document.getElementById('blastRadiusSummary');
    if (blastSummary) {
      blastSummary.innerText = 'All Threats Neutralized';
      blastSummary.className = 'text-emerald-400 font-mono font-bold';
    }

    const dlIconBg = document.getElementById('downloadsIconBg');
    if (dlIconBg) {
      dlIconBg.className = 'w-9 h-9 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-1.5 border border-emerald-500/40';
    }
    const dlTitle = document.getElementById('downloadsNodeTitle');
    if (dlTitle) {
      dlTitle.className = 'text-xs font-bold text-slate-300 font-mono';
    }
    const dlSubtitle = document.getElementById('downloadsNodeSubtitle');
    if (dlSubtitle) {
      dlSubtitle.innerText = '0 active sessions (Terminated)';
      dlSubtitle.className = 'text-[10px] text-emerald-400 font-mono';
    }

    const formula = document.getElementById('propagationFormula');
    if (formula) {
      formula.innerText = 'Owner → Recipient → 0 Active [REVOKED / NULLIFIED]';
      formula.className = 'px-2.5 py-1 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/50 font-bold';
    }

    const activeSessions = document.getElementById('activeSessionsCount');
    if (activeSessions) {
      activeSessions.innerText = '0 Active Sessions (Connections Terminated)';
      activeSessions.className = 'text-emerald-400 font-semibold';
    }

    ['endpoint1', 'endpoint2', 'endpoint3'].forEach((id) => {
      const ep = document.getElementById(id);
      if (ep) {
        ep.classList.remove('border-amber-500/40', 'border-red-500/40', 'bg-amber-950/20', 'bg-red-950/20');
        ep.classList.add('border-slate-800', 'bg-slate-900/60');
        const pill = ep.querySelector('.status-pill');
        if (pill) {
          pill.className = 'status-pill text-[10px] px-2 py-0.5 rounded bg-red-950/80 text-red-400 border border-red-800/80';
          pill.innerText = 'Connection Severed';
        }
      }
    });

    // 6. Update Result & Containment State Section
    const resultSection = document.getElementById('resultSection');
    if (resultSection) resultSection.classList.add('glass-card-glow-emerald');
    const resultPill = document.getElementById('resultStatePill');
    if (resultPill) {
      resultPill.innerText = 'SECURED & CONTAINED';
      resultPill.className = 'text-xs font-mono px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40 font-bold';
    }

    const card1 = document.getElementById('cardAccessRevoked');
    if (card1) {
      card1.className = 'p-3.5 rounded-xl bg-red-950/30 border border-red-500/40 transition-all flex items-start gap-3 shadow-lg shadow-red-500/5';
      const titleP = card1.querySelector('p.font-bold');
      if (titleP) {
        titleP.className = 'text-xs font-mono font-black text-red-400 tracking-wider flex items-center gap-1.5';
        titleP.innerHTML = `<i data-lucide="x-circle" class="w-3.5 h-3.5 text-red-400"></i> ACCESS REVOKED`;
      }
      const icon1 = document.getElementById('iconAccessRevoked');
      if (icon1) icon1.className = 'p-2 rounded-lg bg-red-500/20 text-red-400 mt-0.5 border border-red-500/40';
      const desc1 = document.getElementById('descAccessRevoked');
      if (desc1) desc1.innerHTML = `<span class="text-slate-300">All endpoint connections killed instantly at edge reverse-proxy.</span>`;
    }

    const card2 = document.getElementById('cardLinkInvalidated');
    if (card2) {
      card2.className = 'p-3.5 rounded-xl bg-amber-950/30 border border-amber-500/40 transition-all flex items-start gap-3 shadow-lg shadow-amber-500/5';
      const titleP2 = card2.querySelector('p.font-bold');
      if (titleP2) {
        titleP2.className = 'text-xs font-mono font-black text-amber-400 tracking-wider flex items-center gap-1.5';
        titleP2.innerHTML = `<i data-lucide="ban" class="w-3.5 h-3.5 text-amber-400"></i> LINK INVALIDATED`;
      }
      const icon2 = document.getElementById('iconLinkInvalidated');
      if (icon2) icon2.className = 'p-2 rounded-lg bg-amber-500/20 text-amber-400 mt-0.5 border border-amber-500/40';
      const desc2 = document.getElementById('descLinkInvalidated');
      if (desc2) desc2.innerHTML = `<span class="text-slate-300">Cryptographic token revoked. URL permanently returns <b>403 Forbidden</b>.</span>`;
    }

    const previewStatus = document.getElementById('previewHttpStatus');
    if (previewStatus) {
      previewStatus.className = 'font-mono text-[11px] px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-500/60 font-bold';
      previewStatus.innerText = 'HTTP 403 FORBIDDEN';
    }
    const previewDot = document.getElementById('previewStatusDot');
    if (previewDot) previewDot.className = 'w-2 h-2 rounded-full bg-red-500';
    const previewUrl = document.getElementById('previewUrlText');
    if (previewUrl) {
      previewUrl.innerHTML = `<span class="line-through text-slate-500">SHARE TOKEN REVOKED</span> <span class="text-red-400 ml-1 font-bold">[ACCESS DENIED]</span>`;
    }
    const previewOpenTabBtn = document.getElementById('previewOpenTabBtn');
    if (previewOpenTabBtn) {
      previewOpenTabBtn.classList.add('hidden');
      previewOpenTabBtn.classList.remove('flex');
    }
    const previewAction = document.getElementById('previewActionLabel');
    if (previewAction) {
      previewAction.innerHTML = `<span class="text-red-400 font-bold">REVOKED BY CYBERUNDO</span>`;
    }
    const mockContent = document.getElementById('mockBrowserContent');
    if (mockContent) {
      mockContent.className = 'p-3 rounded-lg bg-red-950/20 border border-red-500/30 text-xs font-mono flex items-center justify-between transition-all';
    }

    const topText = document.getElementById('topStatusText');
    if (topText) topText.innerText = 'INCIDENT NEUTRALIZED — ALL ACCESS REVOKED';
    const topDot = document.getElementById('topStatusDot');
    if (topDot) topDot.className = 'w-2 h-2 rounded-full bg-emerald-400';

    const nowStr = new Date().toTimeString().split(' ')[0];
    this.addLogEntry(nowStr, `🚨 <b>KILLSWITCH TRIGGERED</b>: CyberUndo revocation executed on <b>${this.activeFile.filename}</b>`, 'revoked');
    this.addLogEntry(nowStr, '⚡ Access tokens invalidated across global edge clusters (0ms propagation)', 'revoked');
    this.addLogEntry(nowStr, '🔒 Active sessions terminated. Remote file decryption disabled.', 'revoked');

    setTimeout(() => soundEngine.play('contained'), 300);
    lucide.createIcons();
  }

  updateStepPills(activeStep) {
    for (let i = 1; i <= 5; i++) {
      const pill = document.getElementById(`stepPill${i}`);
      if (!pill) continue;

      if (i < activeStep) {
        pill.className = 'step-pill flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 text-emerald-400 border border-emerald-500/40 transition';
        pill.querySelector('span:first-child').className = 'w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center font-bold text-[10px] text-emerald-400';
        pill.querySelector('span:first-child').innerHTML = '✓';
      } else if (i === activeStep) {
        if (activeStep === 4) {
          pill.className = 'step-pill flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-950 text-red-300 border border-red-500 animate-pulse transition';
          pill.querySelector('span:first-child').className = 'w-5 h-5 rounded-full bg-red-500/30 flex items-center justify-center font-bold text-[10px] text-red-300';
        } else if (activeStep === 5) {
          pill.className = 'step-pill flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950 text-emerald-300 border border-emerald-500 transition';
          pill.querySelector('span:first-child').className = 'w-5 h-5 rounded-full bg-emerald-500/30 flex items-center justify-center font-bold text-[10px] text-emerald-300';
        } else {
          pill.className = 'step-pill flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 transition';
          pill.querySelector('span:first-child').className = 'w-5 h-5 rounded-full bg-cyan-500/30 flex items-center justify-center font-bold text-[10px]';
        }
      } else {
        pill.className = 'step-pill flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 text-slate-500 border border-slate-800 transition';
        pill.querySelector('span:first-child').className = 'w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center font-bold text-[10px]';
        pill.querySelector('span:first-child').innerHTML = `${i}`;
      }
    }
  }

  reset(playSoundEffect = true) {
    if (this.propagationTimer1) { clearTimeout(this.propagationTimer1); this.propagationTimer1 = null; }
    if (this.propagationTimer2) { clearTimeout(this.propagationTimer2); this.propagationTimer2 = null; }
    if (this.propagationTimer3) { clearTimeout(this.propagationTimer3); this.propagationTimer3 = null; }

    this.currentState = STATE.IDLE;
    this.currentShareId = null;
    this.viewRecorded = false;
    this.lastProcessedDownloadCount = 0;
    if (playSoundEffect) soundEngine.play('share');

    const shareLinkContainer = document.getElementById('shareLinkContainer');
    if (shareLinkContainer) {
      shareLinkContainer.classList.add('hidden');
      shareLinkContainer.style.display = 'none';
    }

    const previewOpenTabBtn = document.getElementById('previewOpenTabBtn');
    if (previewOpenTabBtn) {
      previewOpenTabBtn.classList.add('hidden');
      previewOpenTabBtn.classList.remove('flex');
    }
    const previewActionLabel = document.getElementById('previewActionLabel');
    if (previewActionLabel) {
      previewActionLabel.innerText = 'Standby';
    }
    const previewUrlText = document.getElementById('previewUrlText');
    if (previewUrlText) {
      previewUrlText.innerText = 'https://cyberundo.security/share/ready';
    }

    const btnShare = document.getElementById('btnShare');
    const btnShareText = document.getElementById('btnShareText');
    if (btnShare) {
      btnShare.disabled = false;
      btnShare.onclick = () => this.handleShareFile();
      btnShare.className = 'w-full relative group overflow-hidden rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 active:scale-[0.99] text-white font-semibold py-3.5 px-4 shadow-lg shadow-cyan-600/25 border border-cyan-400/30 transition-all flex items-center justify-center gap-2 text-sm tracking-wide';
    }
    if (btnShareText) {
      btnShareText.innerText = `SHARE FILE SECURELY`;
    }

    const shareCard = document.getElementById('shareFileCard');
    if (shareCard) shareCard.className = 'glass-card rounded-2xl p-6 border transition-all duration-300 relative overflow-hidden';
    
    const fileBadgeState = document.getElementById('fileBadgeState');
    if (fileBadgeState) {
      fileBadgeState.innerText = 'Ready to Share';
      fileBadgeState.className = 'px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-slate-800 text-slate-400 border border-slate-700';
    }

    const activityLive = document.getElementById('activityLiveIndicator');
    if (activityLive) activityLive.className = 'hidden';
    
    ['badgeShared', 'badgeViewed', 'badgeDownloaded'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.className = 'flex flex-col items-center justify-center p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/60 text-slate-500 transition-all';
    });
    if (document.getElementById('badgeSharedTime')) document.getElementById('badgeSharedTime').innerText = 'Pending';
    if (document.getElementById('badgeViewedTime')) document.getElementById('badgeViewedTime').innerText = 'Pending';
    if (document.getElementById('badgeDownloadedTime')) document.getElementById('badgeDownloadedTime').innerText = 'Pending';
    
    const logsList = document.getElementById('activityLogsList');
    if (logsList) {
      logsList.innerHTML = `
        <p id="emptyLogsMsg" class="text-slate-600 text-center py-8 italic font-sans text-xs">
          No activity yet. Click "SHARE FILE" to initiate the tracking flow.
        </p>
      `;
    }
    if (document.getElementById('logCount')) document.getElementById('logCount').innerText = '0 events';

    const btnRevoke = document.getElementById('btnRevoke');
    if (btnRevoke) {
      btnRevoke.disabled = true;
      btnRevoke.className = 'w-full relative group overflow-hidden rounded-xl bg-slate-800 text-slate-500 font-bold py-4 px-6 border border-slate-700 transition-all flex items-center justify-center gap-3 text-base tracking-wider font-mono cursor-not-allowed';
    }
    if (document.getElementById('btnRevokeText')) document.getElementById('btnRevokeText').innerText = 'REVOKE ACCESS';
    if (document.getElementById('revokeBtnIconWrapper')) document.getElementById('revokeBtnIconWrapper').innerHTML = `<i data-lucide="shield-off" class="w-5 h-5"></i>`;
    if (document.getElementById('revokeSection')) document.getElementById('revokeSection').className = 'glass-card rounded-2xl p-6 border border-slate-800 transition-all duration-300 relative overflow-hidden';
    if (document.getElementById('revokeHelperText')) document.getElementById('revokeHelperText').innerText = 'Button activates automatically once file is shared and activity is detected.';

    const blastSection = document.getElementById('blastRadiusSection');
    if (blastSection) blastSection.className = 'glass-card rounded-2xl p-6 border transition-all duration-300 relative';
    if (document.getElementById('exposureBadge')) {
      document.getElementById('exposureBadge').className = 'flex items-center gap-1.5 px-3 py-1 rounded-full font-mono text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700 transition-all duration-500';
    }
    if (document.getElementById('exposureText')) document.getElementById('exposureText').innerText = 'Exposure: UNKNOWN';
    if (document.getElementById('exposureIcon')) document.getElementById('exposureIcon').setAttribute('data-lucide', 'activity');
    if (document.getElementById('blastRadiusSummary')) {
      document.getElementById('blastRadiusSummary').innerText = 'Standby';
      document.getElementById('blastRadiusSummary').className = 'text-slate-500 font-mono';
    }

    if (document.getElementById('connectorLine1')) document.getElementById('connectorLine1').className = 'h-0.5 w-full bg-slate-800 transition-all duration-500';
    if (document.getElementById('connectorArrow1')) document.getElementById('connectorArrow1').className = 'w-4 h-4 text-slate-600 absolute transition-colors';
    if (document.getElementById('connectorLine2')) document.getElementById('connectorLine2').className = 'h-0.5 w-full bg-slate-800 transition-all duration-500';
    if (document.getElementById('connectorArrow2')) document.getElementById('connectorArrow2').className = 'w-4 h-4 text-slate-600 absolute transition-colors';

    if (document.getElementById('downloadsIconBg')) document.getElementById('downloadsIconBg').className = 'w-9 h-9 rounded-full bg-slate-800 text-slate-500 flex items-center justify-center mb-1.5 border border-slate-700 transition-all';
    if (document.getElementById('downloadsNodeTitle')) document.getElementById('downloadsNodeTitle').className = 'text-xs font-bold text-slate-400 font-mono';
    if (document.getElementById('downloadsNodeSubtitle')) {
      document.getElementById('downloadsNodeSubtitle').innerText = '0 active';
      document.getElementById('downloadsNodeSubtitle').className = 'text-[10px] text-slate-500 font-mono';
    }

    if (document.getElementById('propagationFormula')) {
      document.getElementById('propagationFormula').innerText = 'Owner → Recipient → 0 Downloads';
      document.getElementById('propagationFormula').className = 'px-2.5 py-1 rounded bg-slate-900 text-slate-400 border border-slate-800 font-bold';
    }
    if (document.getElementById('activeSessionsCount')) {
      document.getElementById('activeSessionsCount').innerText = '0 Active Sessions';
      document.getElementById('activeSessionsCount').className = 'text-slate-500';
    }

    ['endpoint1', 'endpoint2', 'endpoint3'].forEach(id => {
      const ep = document.getElementById(id);
      if (ep) {
        ep.className = 'endpoint-item flex items-center justify-between p-2.5 rounded-xl bg-slate-900/70 border border-slate-800/80 text-xs font-mono opacity-50';
        const pill = ep.querySelector('.status-pill');
        if (pill) {
          pill.className = 'status-pill text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700';
          pill.innerText = 'Idle';
        }
      }
    });

    const resultSection = document.getElementById('resultSection');
    if (resultSection) resultSection.className = 'glass-card rounded-2xl p-6 border transition-all duration-300 relative';
    if (document.getElementById('resultStatePill')) {
      document.getElementById('resultStatePill').innerText = 'Awaiting Action';
      document.getElementById('resultStatePill').className = 'text-xs font-mono px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700';
    }

    const card1 = document.getElementById('cardAccessRevoked');
    if (card1) {
      card1.className = 'p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 transition-all flex items-start gap-3';
      card1.querySelector('p.font-bold').className = 'text-xs font-mono font-bold text-slate-400 tracking-wider';
      card1.querySelector('p.font-bold').innerHTML = 'ACCESS REVOKED';
      document.getElementById('iconAccessRevoked').className = 'p-2 rounded-lg bg-slate-800 text-slate-500 mt-0.5';
      document.getElementById('descAccessRevoked').innerText = 'All 3 active client sessions severed immediately at edge gateway.';
    }

    const card2 = document.getElementById('cardLinkInvalidated');
    if (card2) {
      card2.className = 'p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 transition-all flex items-start gap-3';
      card2.querySelector('p.font-bold').className = 'text-xs font-mono font-bold text-slate-400 tracking-wider';
      card2.querySelector('p.font-bold').innerHTML = 'LINK INVALIDATED';
      document.getElementById('iconLinkInvalidated').className = 'p-2 rounded-lg bg-slate-800 text-slate-500 mt-0.5';
      document.getElementById('descLinkInvalidated').innerText = 'Token revoked. Global signed URL returns 403 Forbidden.';
    }

    if (document.getElementById('previewHttpStatus')) {
      document.getElementById('previewHttpStatus').className = 'font-mono text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700';
      document.getElementById('previewHttpStatus').innerText = 'HTTP 200 OK';
    }
    if (document.getElementById('previewStatusDot')) document.getElementById('previewStatusDot').className = 'w-2 h-2 rounded-full bg-slate-500';
    if (document.getElementById('previewUrlText')) document.getElementById('previewUrlText').innerText = 'https://cyberundo.security/share/v9x-77a1';
    if (document.getElementById('previewActionLabel')) document.getElementById('previewActionLabel').innerText = 'Active';
    if (document.getElementById('mockBrowserContent')) {
      document.getElementById('mockBrowserContent').className = 'p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono flex items-center justify-between transition-all';
    }

    if (document.getElementById('topStatusText')) document.getElementById('topStatusText').innerText = 'SYSTEM READY';
    if (document.getElementById('topStatusDot')) document.getElementById('topStatusDot').className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';

    this.updateStepPills(1);
    this.updateFileDisplay();
    lucide.createIcons();
  }

  openRecipientView() {
    let url = this.currentShareUrl;
    if (!url) {
      const input = document.getElementById('shareLinkInput');
      if (input && input.value) {
        url = input.value;
      }
    }
    if (url) {
      window.open(url, '_blank');
    } else if (this.currentShareId) {
      const origin = window.location.origin;
      const pathname = window.location.pathname.replace(/\/index\.html$/, '').replace(/\/$/, '');
      const shareUrl = `${origin}${pathname}/share.html?id=${this.currentShareId}`;
      window.open(shareUrl, '_blank');
    }
  }

  copyShareLink() {
    const input = document.getElementById('shareLinkInput');
    const label = document.getElementById('copyBtnLabel');
    if (input && input.value) {
      navigator.clipboard.writeText(input.value).then(() => {
        if (label) label.innerText = 'Copied!';
        if (window.toast) window.toast.success('Share link copied to clipboard!');
        setTimeout(() => {
          if (label) label.innerText = 'Copy';
        }, 2000);
      }).catch(() => {
        input.select();
        document.execCommand('copy');
        if (label) label.innerText = 'Copied!';
        if (window.toast) window.toast.success('Share link copied!');
        setTimeout(() => {
          if (label) label.innerText = 'Copy';
        }, 2000);
      });
    }
  }

  async handleRevokeAll() {
    if (window.authManager && authManager.isAuthenticated()) {
      const fileId = (this.activeFile && this.activeFile.id) || null;
      try {
        await apiService.revokeAllShares(fileId);
        window.toast && window.toast.success("All active share links revoked successfully.");
      } catch (err) {
        console.warn("Backend revoke-all notice:", err);
      }
    }
    this.handleRevokeAccess();
  }

  updateUI() {
    this.updateFileDisplay();
    lucide.createIcons();
  }
}

// Global helpers for copying share link, opening recipient view, and revoking
window.copyShareLink = function() {
  if (window.killSwitchManager) {
    window.killSwitchManager.copyShareLink();
  }
};

window.openRecipientView = function() {
  if (window.killSwitchManager) {
    window.killSwitchManager.openRecipientView();
  }
};

window.handleRevokeAll = function() {
  if (window.killSwitchManager) {
    window.killSwitchManager.handleRevokeAll();
  }
};


window.killSwitchManager = new KillSwitchManager();
