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
    this.activeFile = {
      id: 0,
      filename: "Project_Final.pdf",
      status: "active",
      created_at: new Date().toISOString()
    };
    this.propagationTimer1 = null;
    this.propagationTimer2 = null;
    this.propagationTimer3 = null;
  }

  init() {
    this.setupHotkeys();
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
      shareBtnText.innerText = `SHARE FILE (${this.activeFile.filename} → Person A)`;
    }
  }

  setupHotkeys() {
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        if (this.currentState === STATE.ACTIVE_THREAT) {
          this.handleRevokeAccess();
        } else if (this.currentState === STATE.REVOKED) {
          this.flashRevokedNotice();
        } else {
          // Pulse the share button if not shared yet
          const btnShare = document.getElementById('btnShare');
          if (btnShare) {
            btnShare.classList.add('ring-2', 'ring-cyan-400');
            setTimeout(() => btnShare.classList.remove('ring-2', 'ring-cyan-400'), 600);
          }
        }
      }
    });
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

  handleShareFile() {
    if (this.currentState !== STATE.IDLE) return;
    
    this.currentState = STATE.SHARING;
    soundEngine.play('share');

    const btnShare = document.getElementById('btnShare');
    const btnShareText = document.getElementById('btnShareText');
    const shareCard = document.getElementById('shareFileCard');
    const fileBadgeState = document.getElementById('fileBadgeState');

    btnShare.disabled = true;
    btnShare.classList.remove('from-cyan-600', 'to-blue-600', 'hover:from-cyan-500');
    btnShare.classList.add('bg-slate-800', 'text-slate-400', 'border-slate-700');
    btnShareText.innerHTML = `<span class="inline-block animate-spin mr-2">⟳</span> GENERATING SECURE TOKEN...`;

    shareCard.classList.add('glass-card-glow-cyan');
    fileBadgeState.innerText = 'Sharing...';
    fileBadgeState.className = 'px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-cyan-950 text-cyan-300 border border-cyan-500/40';

    this.updateStepPills(1);

    setTimeout(() => {
      btnShareText.innerHTML = `✓ SHARED WITH PERSON A`;
      fileBadgeState.innerText = 'Active Link';
      fileBadgeState.className = 'px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-emerald-950 text-emerald-300 border border-emerald-500/40';

      document.getElementById('topStatusText').innerText = 'LINK ACTIVE — MONITORING';
      document.getElementById('topStatusDot').className = 'w-2 h-2 rounded-full bg-cyan-400 animate-pulse';

      const badgeShared = document.getElementById('badgeShared');
      badgeShared.className = 'flex flex-col items-center justify-center p-2.5 rounded-lg bg-cyan-950/80 border border-cyan-500/60 text-cyan-300 transition-all';
      document.getElementById('badgeSharedTime').innerText = '00:00:01';

      this.addLogEntry('12:00:00', `File <b>${this.activeFile.filename}</b> shared to <b>alex.morgan@partnercorp.io</b>`, 'shared');

      document.getElementById('connectorLine1').className = 'h-0.5 w-full bg-cyan-500 laser-line-active';
      document.getElementById('connectorArrow1').className = 'w-4 h-4 text-cyan-400 absolute';
      document.getElementById('nodePersonA').classList.add('border-cyan-500/40', 'shadow-cyan-500/10');
      
      document.getElementById('activityLiveIndicator').classList.remove('hidden');
      document.getElementById('activityLiveIndicator').classList.add('flex');

      this.simulateRapidProgression();
    }, 700);
  }

  simulateRapidProgression() {
    this.propagationTimer1 = setTimeout(() => {
      if (this.currentState === STATE.REVOKED) return;
      
      soundEngine.play('share');
      this.updateStepPills(2);

      const badgeViewed = document.getElementById('badgeViewed');
      badgeViewed.className = 'flex flex-col items-center justify-center p-2.5 rounded-lg bg-blue-950/80 border border-blue-500/60 text-blue-300 transition-all';
      document.getElementById('badgeViewedTime').innerText = '00:00:04';

      this.addLogEntry('12:00:04', '<b>Person A</b> opened access link in Chrome on macOS (IP: 198.51.100.24, San Francisco)', 'viewed');

      const ep1 = document.getElementById('endpoint1');
      ep1.classList.remove('opacity-50');
      ep1.classList.add('border-blue-500/40', 'bg-blue-950/20');
      ep1.querySelector('.status-pill').className = 'status-pill text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-600 animate-pulse';
      ep1.querySelector('.status-pill').innerText = 'Viewing';
    }, 900);

    this.propagationTimer2 = setTimeout(() => {
      if (this.currentState === STATE.REVOKED) return;
      
      soundEngine.play('share');

      const badgeDownloaded = document.getElementById('badgeDownloaded');
      badgeDownloaded.className = 'flex flex-col items-center justify-center p-2.5 rounded-lg bg-amber-950/80 border border-amber-500/60 text-amber-300 transition-all';
      document.getElementById('badgeDownloadedTime').innerText = '00:00:08 (1x)';

      this.addLogEntry('12:00:08', 'Download #1 initiated by <b>Person A</b> (MacBook Pro)', 'download');

      const ep1 = document.getElementById('endpoint1');
      ep1.querySelector('.status-pill').className = 'status-pill text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-600';
      ep1.querySelector('.status-pill').innerText = 'Downloaded';

      document.getElementById('connectorLine2').className = 'h-0.5 w-full bg-amber-500 laser-line-active';
      document.getElementById('connectorArrow2').className = 'w-4 h-4 text-amber-400 absolute';
      
      document.getElementById('downloadsNodeSubtitle').innerText = '1 active node';
      document.getElementById('propagationFormula').innerText = 'You → Person A → 1 Download';
      document.getElementById('activeSessionsCount').innerText = '1 Active Session';
    }, 1800);

    this.propagationTimer3 = setTimeout(() => {
      if (this.currentState === STATE.REVOKED) return;

      this.currentState = STATE.ACTIVE_THREAT;
      soundEngine.play('threat');
      this.updateStepPills(3);

      document.getElementById('badgeDownloadedTime').innerText = '00:00:12 (3x)';
      
      this.addLogEntry('12:00:11', '⚠️ Link forwarded! Download #2 from Windows 11 (IP: 203.0.113.45, Frankfurt)', 'threat');
      this.addLogEntry('12:00:13', '🚨 Download #3 from Unverified Cloud Node (IP: 192.0.2.89, Singapore)', 'threat');

      const ep2 = document.getElementById('endpoint2');
      ep2.classList.remove('opacity-50');
      ep2.classList.add('border-amber-500/40', 'bg-amber-950/20');
      ep2.querySelector('.status-pill').className = 'status-pill text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-600';
      ep2.querySelector('.status-pill').innerText = 'Downloaded';

      const ep3 = document.getElementById('endpoint3');
      ep3.classList.remove('opacity-50');
      ep3.classList.add('border-red-500/40', 'bg-red-950/20');
      ep3.querySelector('.status-pill').className = 'status-pill text-[10px] px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-600 animate-pulse';
      ep3.querySelector('.status-pill').innerText = 'External Leak';

      const blastSection = document.getElementById('blastRadiusSection');
      blastSection.classList.add('glass-card-glow-danger');

      const exposureBadge = document.getElementById('exposureBadge');
      exposureBadge.className = 'flex items-center gap-1.5 px-3 py-1 rounded-full font-mono text-xs font-bold bg-red-950 text-red-400 border border-red-500 animate-pulse';
      document.getElementById('exposureText').innerText = 'Exposure: HIGH';
      document.getElementById('exposureIcon').setAttribute('data-lucide', 'alert-octagon');

      document.getElementById('blastRadiusSummary').innerText = '3 Endpoints Compromised';
      document.getElementById('blastRadiusSummary').className = 'text-red-400 font-mono font-bold';

      document.getElementById('downloadsIconBg').className = 'w-9 h-9 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center mb-1.5 border border-red-500/40';
      document.getElementById('downloadsNodeTitle').className = 'text-xs font-bold text-red-400 font-mono';
      document.getElementById('downloadsNodeSubtitle').innerText = '3 active downloads';
      document.getElementById('downloadsNodeSubtitle').className = 'text-[10px] text-red-300 font-mono';

      document.getElementById('propagationFormula').innerText = 'You → Person A → 3 Downloads';
      document.getElementById('propagationFormula').className = 'px-2.5 py-1 rounded bg-red-950/80 text-red-300 border border-red-500/50 font-bold';

      document.getElementById('activeSessionsCount').innerText = '3 Active Sessions Detected';
      document.getElementById('activeSessionsCount').className = 'text-red-400 font-bold';

      document.getElementById('connectorLine2').className = 'h-0.5 w-full bg-red-500 laser-line-danger';
      document.getElementById('connectorArrow2').className = 'w-4 h-4 text-red-400 absolute';

      document.getElementById('topStatusText').innerText = 'CRITICAL THREAT — 3 DOWNLOADS DETECTED';
      document.getElementById('topStatusDot').className = 'w-2 h-2 rounded-full bg-red-500 animate-ping';

      this.activateRevokeButton();
      lucide.createIcons();
    }, 2800);
  }

  activateRevokeButton() {
    this.updateStepPills(4);
    const btnRevoke = document.getElementById('btnRevoke');
    const revokeSection = document.getElementById('revokeSection');

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

    revokeSection.classList.add('glass-card-glow-danger');
    document.getElementById('revokeHelperText').innerHTML = `<span class="text-red-400 font-bold animate-pulse">⚡ CLICK REVOKE ACCESS OR PRESS CTRL+Z NOW TO RECOVER CONTROL</span>`;
  }

  handleRevokeAccess() {
    if (this.currentState !== STATE.ACTIVE_THREAT && this.currentState !== STATE.SHARING) return;

    this.currentState = STATE.REVOKED;
    soundEngine.play('revoke');

    document.body.classList.add('revoke-shockwave');
    setTimeout(() => document.body.classList.remove('revoke-shockwave'), 600);

    const btnRevoke = document.getElementById('btnRevoke');
    const btnRevokeText = document.getElementById('btnRevokeText');
    btnRevoke.disabled = true;
    btnRevoke.classList.remove('animate-pulse-slow', 'from-red-600', 'to-rose-600');
    btnRevoke.classList.add('bg-slate-900', 'text-emerald-400', 'border-emerald-500/50', 'shadow-none', 'cursor-default');
    btnRevokeText.innerHTML = `✓ ACCESS REVOKED (Zero-Trust Killswitch Executed)`;
    document.getElementById('revokeBtnIconWrapper').innerHTML = `<i data-lucide="shield-check" class="w-5 h-5 text-emerald-400"></i>`;

    document.getElementById('revokeHelperText').innerHTML = `<span class="text-emerald-400 font-mono">Remediation complete. Decryption tokens invalidated across edge CDN nodes.</span>`;

    this.updateStepPills(5);

    document.getElementById('connectorLine1').className = 'h-0.5 w-full bg-slate-700 laser-line-severed';
    document.getElementById('connectorArrow1').className = 'w-4 h-4 text-slate-700 absolute';
    document.getElementById('connectorLine2').className = 'h-0.5 w-full bg-slate-700 laser-line-severed';
    document.getElementById('connectorArrow2').className = 'w-4 h-4 text-slate-700 absolute';

    const blastSection = document.getElementById('blastRadiusSection');
    blastSection.classList.remove('glass-card-glow-danger');
    blastSection.classList.add('glass-card-glow-emerald');

    const exposureBadge = document.getElementById('exposureBadge');
    exposureBadge.className = 'flex items-center gap-1.5 px-3 py-1 rounded-full font-mono text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-500';
    document.getElementById('exposureText').innerText = 'Exposure: CONTAINED / ZERO RISK';
    document.getElementById('exposureIcon').setAttribute('data-lucide', 'shield-check');

    document.getElementById('blastRadiusSummary').innerText = 'All Threats Neutralized';
    document.getElementById('blastRadiusSummary').className = 'text-emerald-400 font-mono font-bold';

    document.getElementById('downloadsIconBg').className = 'w-9 h-9 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-1.5 border border-emerald-500/40';
    document.getElementById('downloadsNodeTitle').className = 'text-xs font-bold text-slate-300 font-mono';
    document.getElementById('downloadsNodeSubtitle').innerText = '0 active sessions (Terminated)';
    document.getElementById('downloadsNodeSubtitle').className = 'text-[10px] text-emerald-400 font-mono';

    document.getElementById('propagationFormula').innerText = 'You → Person A → 3 Downloads [REVOKED / NULLIFIED]';
    document.getElementById('propagationFormula').className = 'px-2.5 py-1 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/50 font-bold';

    document.getElementById('activeSessionsCount').innerText = '0 Active Sessions (3 Forcefully Terminated)';
    document.getElementById('activeSessionsCount').className = 'text-emerald-400 font-semibold';

    ['endpoint1', 'endpoint2', 'endpoint3'].forEach((id) => {
      const ep = document.getElementById(id);
      ep.classList.remove('border-amber-500/40', 'border-red-500/40', 'bg-amber-950/20', 'bg-red-950/20');
      ep.classList.add('border-slate-800', 'bg-slate-900/60');
      const pill = ep.querySelector('.status-pill');
      pill.className = 'status-pill text-[10px] px-2 py-0.5 rounded bg-red-950/80 text-red-400 border border-red-800/80';
      pill.innerText = 'Connection Severed';
    });

    const resultSection = document.getElementById('resultSection');
    resultSection.classList.add('glass-card-glow-emerald');
    document.getElementById('resultStatePill').innerText = 'SECURED & CONTAINED';
    document.getElementById('resultStatePill').className = 'text-xs font-mono px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40 font-bold';

    const card1 = document.getElementById('cardAccessRevoked');
    card1.className = 'p-3.5 rounded-xl bg-red-950/30 border border-red-500/40 transition-all flex items-start gap-3 shadow-lg shadow-red-500/5';
    card1.querySelector('p.font-bold').className = 'text-xs font-mono font-black text-red-400 tracking-wider flex items-center gap-1.5';
    card1.querySelector('p.font-bold').innerHTML = `<i data-lucide="x-circle" class="w-3.5 h-3.5 text-red-400"></i> ACCESS REVOKED`;
    document.getElementById('iconAccessRevoked').className = 'p-2 rounded-lg bg-red-500/20 text-red-400 mt-0.5 border border-red-500/40';
    document.getElementById('descAccessRevoked').innerHTML = `<span class="text-slate-300">All 3 active endpoint connections killed instantly at edge reverse-proxy.</span>`;

    const card2 = document.getElementById('cardLinkInvalidated');
    card2.className = 'p-3.5 rounded-xl bg-amber-950/30 border border-amber-500/40 transition-all flex items-start gap-3 shadow-lg shadow-amber-500/5';
    card2.querySelector('p.font-bold').className = 'text-xs font-mono font-black text-amber-400 tracking-wider flex items-center gap-1.5';
    card2.querySelector('p.font-bold').innerHTML = `<i data-lucide="ban" class="w-3.5 h-3.5 text-amber-400"></i> LINK INVALIDATED`;
    document.getElementById('iconLinkInvalidated').className = 'p-2 rounded-lg bg-amber-500/20 text-amber-400 mt-0.5 border border-amber-500/40';
    document.getElementById('descLinkInvalidated').innerHTML = `<span class="text-slate-300">Cryptographic token revoked. URL permanently returns <b>403 Forbidden</b>.</span>`;

    document.getElementById('previewHttpStatus').className = 'font-mono text-[11px] px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-500/60 font-bold';
    document.getElementById('previewHttpStatus').innerText = 'HTTP 403 FORBIDDEN';
    document.getElementById('previewStatusDot').className = 'w-2 h-2 rounded-full bg-red-500';
    document.getElementById('previewUrlText').innerHTML = `<span class="line-through text-slate-500">https://cyberundo.security/share/v9x-77a1</span> <span class="text-red-400 ml-1 font-bold">[ACCESS DENIED]</span>`;
    document.getElementById('previewActionLabel').innerHTML = `<span class="text-red-400 font-bold">REVOKED BY CYBERUNDO</span>`;
    document.getElementById('mockBrowserContent').className = 'p-3 rounded-lg bg-red-950/20 border border-red-500/30 text-xs font-mono flex items-center justify-between transition-all';

    document.getElementById('topStatusText').innerText = 'INCIDENT NEUTRALIZED — ALL ACCESS REVOKED';
    document.getElementById('topStatusDot').className = 'w-2 h-2 rounded-full bg-emerald-400';

    this.addLogEntry('12:00:15', `🚨 <b>KILLSWITCH TRIGGERED</b>: CyberUndo revocation executed on <b>${this.activeFile.filename}</b>`, 'revoked');
    this.addLogEntry('12:00:15', '⚡ Access tokens invalidated across global edge clusters (0ms propagation)', 'revoked');
    this.addLogEntry('12:00:16', '🔒 3 active sessions terminated. Remote file decryption disabled.', 'revoked');

    setTimeout(() => soundEngine.play('contained'), 400);
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
    if (this.propagationTimer1) clearTimeout(this.propagationTimer1);
    if (this.propagationTimer2) clearTimeout(this.propagationTimer2);
    if (this.propagationTimer3) clearTimeout(this.propagationTimer3);

    this.currentState = STATE.IDLE;
    if (playSoundEffect) soundEngine.play('share');

    const btnShare = document.getElementById('btnShare');
    const btnShareText = document.getElementById('btnShareText');
    if (btnShare) {
      btnShare.disabled = false;
      btnShare.className = 'w-full relative group overflow-hidden rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 active:scale-[0.99] text-white font-semibold py-3.5 px-4 shadow-lg shadow-cyan-600/25 border border-cyan-400/30 transition-all flex items-center justify-center gap-2 text-sm tracking-wide';
    }
    if (btnShareText) {
      btnShareText.innerText = `SHARE FILE (${this.activeFile.filename} → Person A)`;
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
      document.getElementById('propagationFormula').innerText = 'You → Person A → 0 Downloads';
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

  updateUI() {
    this.updateFileDisplay();
    lucide.createIcons();
  }
}

window.killSwitchManager = new KillSwitchManager();
