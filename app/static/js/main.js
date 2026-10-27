const AudioFeedback = {
    ctx: null,

    init() {
        if (!this.ctx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) {
                this.ctx = new AudioCtx();
            }
        }
    },

    playSuccess() {
        try {
            this.init();
            if (!this.ctx) return;
            if (this.ctx.state === 'suspended') this.ctx.resume();

            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sine';

            const now = this.ctx.currentTime;
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.setValueAtTime(1320, now + 0.08);

            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.25);
        } catch (e) {
            console.warn("Audio playback error:", e);
        }
    },

    playWarning() {
        try {
            this.init();
            if (!this.ctx) return;
            if (this.ctx.state === 'suspended') this.ctx.resume();

            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sawtooth';

            const now = this.ctx.currentTime;
            osc.frequency.setValueAtTime(320, now);
            osc.frequency.setValueAtTime(260, now + 0.12);

            gain.gain.setValueAtTime(0.2, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.35);
        } catch (e) {
            console.warn("Audio playback error:", e);
        }
    }
};

function initClock() {
    const clockEl = document.getElementById('live-clock');
    if (!clockEl) return;

    function update() {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
    }
    update();
    setInterval(update, 1000);
}

function initAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });
}

function initSidebarToggle() {
    const toggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.app-sidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initAlerts();
    initSidebarToggle();
});
