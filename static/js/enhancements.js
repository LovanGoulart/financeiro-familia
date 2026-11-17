/* Eventos persistentes, avisos flutuantes e instalação progressiva. */
(() => {
    'use strict';
    const read = (key, fallback = '') => { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } };
    const write = (key, value) => { try { localStorage.setItem(key, String(value)); } catch { /* Navegação privada */ } };
    const region = document.getElementById('toast-region');
    const user = document.body.dataset.user;
    let audio;
    let soundEnabled = read('finance-sound') === '1';
    const soundButton = document.getElementById('sound-toggle');
    function updateSound() {
        if (!soundButton) return;
        soundButton.textContent = soundEnabled ? 'Som ativado' : 'Ativar som';
        soundButton.setAttribute('aria-pressed', String(soundEnabled));
    }
    async function unlockAudio() {
        if (!soundEnabled) return;
        try {
            const Audio = window.AudioContext || window.webkitAudioContext;
            if (!Audio) return;
            audio ||= new Audio();
            await audio.resume();
        } catch { /* O navegador exige interação para liberar o som. */ }
    }
    function beep() {
        if (!soundEnabled || !audio || audio.state !== 'running') return;
        const oscillator = audio.createOscillator();
        const gain = audio.createGain();
        oscillator.connect(gain); gain.connect(audio.destination);
        oscillator.frequency.setValueAtTime(880, audio.currentTime);
        gain.gain.setValueAtTime(0.06, audio.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.25);
        oscillator.start(); oscillator.stop(audio.currentTime + 0.25);
    }
    window.financeToast = (message, category = 'info', playSound = true) => {
        if (!region) return;
        const toast = document.createElement('div');
        toast.className = `finance-toast ${['success', 'danger', 'warning'].includes(category) ? category : 'info'}`;
        toast.setAttribute('role', category === 'danger' ? 'alert' : 'status');
        const text = document.createElement('span'); text.textContent = message;
        const close = document.createElement('button'); close.type = 'button'; close.textContent = '×';
        close.setAttribute('aria-label', 'Fechar aviso'); close.addEventListener('click', () => toast.remove());
        toast.append(text, close); region.append(toast);
        while (region.children.length > 4) region.firstElementChild.remove();
        if (playSound) beep();
        setTimeout(() => toast.remove(), 8000);
    };
    updateSound();
    soundButton?.addEventListener('click', async () => {
        soundEnabled = !soundEnabled; write('finance-sound', soundEnabled ? '1' : '0'); updateSound();
        await unlockAudio(); if (soundEnabled) beep();
    });
    document.addEventListener('pointerdown', unlockAudio);
    document.addEventListener('keydown', unlockAudio);
    const flashes = JSON.parse(document.getElementById('flash-data')?.textContent || '[]');
    flashes.forEach(([category, message]) => window.financeToast(message, category));

    // Instalação: só mostrar o convite nativo se o navegador confirmar a disponibilidade.
    const banner = document.getElementById('install-banner');
    const installButton = document.getElementById('install-app');
    let installPrompt;
    const standalone = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
    const installed = () => standalone() || read('finance-installed') === '1';
    function rememberInstalled() { write('finance-installed', '1'); if (banner) banner.hidden = true; }
    if (standalone()) rememberInstalled();
    function canInvite() { return !installed() && Date.now() > Number(read('finance-install-dismissed', '0')); }
    window.addEventListener('beforeinstallprompt', event => {
        event.preventDefault(); installPrompt = event;
        if (canInvite()) banner.hidden = false;
    });
    window.addEventListener('appinstalled', rememberInstalled);
    window.matchMedia('(display-mode: standalone)').addEventListener('change', () => { if (standalone()) rememberInstalled(); });
    window.addEventListener('storage', event => { if (event.key === 'finance-installed' && event.newValue === '1') banner.hidden = true; });
    const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    if (ios && canInvite()) {
        document.getElementById('install-text').textContent = 'No Safari, toque em Compartilhar e depois em Adicionar à Tela de Início. Após instalar, abra pelo ícone do app.';
        installButton.textContent = 'Já instalei'; banner.hidden = false;
    }
    installButton?.addEventListener('click', async () => {
        if (ios && !installPrompt) { rememberInstalled(); return; }
        if (!installPrompt) return;
        await installPrompt.prompt();
        const choice = await installPrompt.userChoice;
        installPrompt = null; banner.hidden = true;
        if (choice.outcome === 'accepted') rememberInstalled();
    });
    document.getElementById('dismiss-install')?.addEventListener('click', () => {
        banner.hidden = true; write('finance-install-dismissed', Date.now() + 24 * 60 * 60 * 1000);
    });
    if ('serviceWorker' in navigator && window.isSecureContext) {
        navigator.serviceWorker.register('/sw.js').catch(() => console.warn('Não foi possível registrar o aplicativo.'));
    }

    if (!user) return;
    const key = `finance-cursor-${user}`;
    let cursor = Number(read(key, document.body.dataset.cursor || '0'));
    const status = document.getElementById('connection-status');
    let source, pollTimer, polling = false, failureTimer, busy = false, refreshTimer;
    let dirty = false;
    document.querySelector('.content-area')?.addEventListener('input', event => {
        if (event.target.closest('form[method="POST" i]')) dirty = true;
    });
    let pendingRefresh = false;
    async function refreshView() {
        if (!pendingRefresh || busy || document.hidden || dirty || document.querySelector('.modal.show, .modal[style*="display: flex"], .modal[style*="display: block"]')) return;
        const page = document.body.dataset.page;
        if (!['dashboard', 'expenses', 'reports', 'shopping'].includes(page)) return;
        busy = true;
        try {
            const response = await fetch(location.href, {headers: {'X-Live-Refresh': '1'}, cache: 'no-store'});
            if (!response.ok || response.redirected) return;
            const html = new DOMParser().parseFromString(await response.text(), 'text/html');
            if (page === 'dashboard') {
                if (document.activeElement?.closest('form')) return;
                document.querySelectorAll('canvas').forEach(canvas => window.Chart?.getChart(canvas)?.destroy());
                document.querySelector('.content-area').replaceChildren(...html.querySelector('.content-area').childNodes);
                if (typeof window.initCharts === 'function') window.initCharts();
            } else if (page === 'expenses') {
                // Full read view refresh via a deferred reload to retain delegated form behavior.
                saveNoticesAndReload(); return;
            } else if (page === 'reports') {
                saveNoticesAndReload(); return;
            } else {
                saveNoticesAndReload(); return;
            }
            pendingRefresh = false;
        } catch { /* Nova tentativa na próxima atualização ou ao voltar à aba. */ }
        finally { busy = false; }
    }
    function saveNoticesAndReload() {
        // Reload only passive read pages; data entry and dirty forms are never discarded.
        if (document.activeElement?.closest('form') || dirty) return;
        try {
            sessionStorage.setItem(`finance-live-notices-${user}`, JSON.stringify([...region.querySelectorAll('span')].map(el => el.textContent)));
            sessionStorage.setItem('finance-scroll', String(window.scrollY));
        } catch { /* Sem armazenamento local */ }
        location.reload();
    }
    try {
        const saved = JSON.parse(sessionStorage.getItem(`finance-live-notices-${user}`) || '[]');
        sessionStorage.removeItem(`finance-live-notices-${user}`);
        saved.forEach(message => window.financeToast(message, 'info', false));
        const scroll = sessionStorage.getItem('finance-scroll'); sessionStorage.removeItem('finance-scroll');
        if (scroll) window.scrollTo(0, Number(scroll));
    } catch { /* Sem armazenamento local */ }
    function receive(event) {
        if (event.id <= cursor) return;
        cursor = event.id; write(key, cursor);
        if (String(event.actor_id) !== user && event.id > Number(read(`finance-alerted-${user}`, '0'))) {
            write(`finance-alerted-${user}`, event.id);
            window.financeToast(event.message);
        }
        pendingRefresh = true;
        clearTimeout(refreshTimer); refreshTimer = setTimeout(refreshView, 700);
    }
    async function poll() {
        if (polling || document.hidden) return;
        polling = true;
        try {
            const response = await fetch(`/api/notifications?after=${cursor}`, {cache: 'no-store'});
            if (response.status === 401) { stop(); status.textContent = 'Entre novamente'; return; }
            if (!response.ok) throw new Error('offline');
            const data = await response.json(); data.events.forEach(receive);
            status.textContent = 'Conectado';
        } catch { status.textContent = 'Reconectando…'; }
        finally { polling = false; }
    }
    function stop() { source?.close(); clearInterval(pollTimer); clearTimeout(failureTimer); }
    function fallback() {
        source?.close(); source = null;
        if (!pollTimer) { poll(); pollTimer = setInterval(poll, 2000); }
    }
    function connect() {
        if (!window.EventSource) { fallback(); return; }
        source = new EventSource(`/api/notifications/stream?after=${cursor}`);
        failureTimer = setTimeout(fallback, 5000);
        source.onopen = () => { clearTimeout(failureTimer); status.textContent = 'Conectado'; };
        source.addEventListener('change', event => receive(JSON.parse(event.data)));
        source.onerror = () => { status.textContent = 'Reconectando…'; fallback(); };
    }
    document.addEventListener('visibilitychange', () => { if (!document.hidden) { poll(); refreshView(); } });
    window.addEventListener('online', poll);
    document.addEventListener('focusout', () => { if (pendingRefresh) setTimeout(refreshView, 100); });
    window.addEventListener('pagehide', stop);
    window.addEventListener('pageshow', event => { if (event.persisted) { pollTimer = null; connect(); } });
    connect();
})();
