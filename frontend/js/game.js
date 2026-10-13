/* 游戏主页控制：键盘监听、难度选择、暂停/重开、音效(F-13)、成绩提交(F-10) */
(function () {
  if (!requireAuth()) return;
  renderNavbar('game');

  /* ---------- WebAudio 音效（无外部音频资源，纯振荡器合成） ---------- */
  const SoundFX = {
    ctx: null,
    enabled: localStorage.getItem(SOUND_KEY) !== 'off',
    ensure() {
      if (!this.ctx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (AC) this.ctx = new AC();
      }
      if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
    },
    beep(freq, delay = 0, dur = 0.08, type = 'square', vol = 0.12) {
      if (!this.enabled || !this.ctx) return;
      const t0 = this.ctx.currentTime + delay;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, t0);
      gain.gain.setValueAtTime(vol, t0);
      gain.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
      osc.connect(gain).connect(this.ctx.destination);
      osc.start(t0);
      osc.stop(t0 + dur + 0.02);
    },
    play(name) {
      this.ensure();
      switch (name) {
        case 'move': this.beep(180, 0, 0.03, 'square', 0.05); break;
        case 'rotate': this.beep(280, 0, 0.05, 'square', 0.07); break;
        case 'lock': this.beep(140, 0, 0.07, 'triangle', 0.10); break;
        case 'harddrop': this.beep(110, 0, 0.09, 'sawtooth', 0.10); break;
        case 'clear': this.beep(440); this.beep(560, .07); this.beep(700, .14, .1, 'triangle'); break;
        case 'tetris': [400, 520, 640, 800].forEach((f, i) => this.beep(f, i * .07, .1, 'triangle', .14)); break;
        case 'levelup': this.beep(520); this.beep(780, .1, .12, 'triangle', .13); break;
        case 'gameover': [400, 320, 240, 160].forEach((f, i) => this.beep(f, i * .12, .16, 'sawtooth', .12)); break;
      }
    },
  };

  const soundBtn = document.getElementById('soundBtn');
  function refreshSoundBtn() { soundBtn.textContent = '音效：' + (SoundFX.enabled ? '开' : '关'); }
  refreshSoundBtn();
  soundBtn.addEventListener('click', () => {
    SoundFX.enabled = !SoundFX.enabled;
    localStorage.setItem(SOUND_KEY, SoundFX.enabled ? 'on' : 'off');
    refreshSoundBtn();
    if (SoundFX.enabled) SoundFX.play('rotate');
  });

  /* ---------- DOM ---------- */
  const boardCanvas = document.getElementById('board');
  const nextCanvas = document.getElementById('nextCanvas');
  const scoreVal = document.getElementById('scoreVal');
  const highVal = document.getElementById('highVal');
  const linesVal = document.getElementById('linesVal');
  const levelVal = document.getElementById('levelVal');
  const timeVal = document.getElementById('timeVal');
  const startOverlay = document.getElementById('startOverlay');
  const pauseOverlay = document.getElementById('pauseOverlay');
  const overOverlay = document.getElementById('overOverlay');

  let highScore = 0;
  let currentLevel = 1;

  api('/api/games/highscore').then(res => {
    highScore = res.data.highscore;
    highVal.textContent = highScore;
  }).catch(() => {});

  /* ---------- 引擎实例 ---------- */
  const game = new Tetris(boardCanvas, nextCanvas, {
    onStats(stats) {
      scoreVal.textContent = stats.score;
      linesVal.textContent = stats.lines;
      levelVal.textContent = stats.level;
      timeVal.textContent = formatDuration(stats.duration);
      if (stats.score > highScore) {
        highScore = stats.score;
        highVal.textContent = highScore;
      }
    },
    onEvent(name) { SoundFX.play(name); },
    onGameOver(result) { saveGameResult(result); },
  });

  /* ---------- 遮罩 / 开始 / 重开 ---------- */
  function showOverlay(name) {
    [startOverlay, pauseOverlay, overOverlay].forEach(o => o.classList.add('hidden'));
    if (name) document.getElementById(name).classList.remove('hidden');
  }

  function beginGame(level) {
    currentLevel = level;
    showOverlay(null);
    SoundFX.ensure();
    scoreVal.textContent = linesVal.textContent = '0';
    levelVal.textContent = level;
    timeVal.textContent = '00:00';
    game.start(level);
  }

  document.querySelectorAll('.diff-btn').forEach(btn =>
    btn.addEventListener('click', () => beginGame(parseInt(btn.dataset.level, 10))));
  document.getElementById('againSameBtn').addEventListener('click', () => beginGame(currentLevel));
  document.getElementById('changeDiffBtn').addEventListener('click', () => showOverlay('startOverlay'));

  /* ---------- 暂停 / 继续 / 重开 ---------- */
  function togglePause() {
    if (game.state !== 'playing' && game.state !== 'paused') return;
    game.togglePause();
    pauseOverlay.classList.toggle('hidden', game.state !== 'paused');
  }
  document.getElementById('pauseBtn').addEventListener('click', togglePause);
  document.getElementById('resumeBtn').addEventListener('click', togglePause);
  document.getElementById('restartBtn').addEventListener('click', () => {
    if (game.state === 'idle') return;
    if (game.state === 'over') { showOverlay('startOverlay'); return; }
    beginGame(currentLevel);
  });

  /* ---------- 键盘控制 ---------- */
  document.addEventListener('keydown', (e) => {
    const key = e.key;
    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' '].includes(key)) {
      e.preventDefault();
    }
    if (key === 'p' || key === 'P') { togglePause(); return; }
    if (game.state !== 'playing') return;
    switch (key) {
      case 'ArrowLeft': game.move(-1); break;
      case 'ArrowRight': game.move(1); break;
      case 'ArrowUp': game.rotate(); break;
      case 'ArrowDown': game.softDrop(); break;
      case ' ': game.hardDrop(); break;
    }
  });

  /* ---------- 对局结束保存成绩（F-10） ---------- */
  async function saveGameResult(result) {
    document.getElementById('finalScore').textContent = result.score;
    document.getElementById('finalLines').textContent = result.lines_cleared;
    document.getElementById('finalLevel').textContent = result.level;
    document.getElementById('finalDuration').textContent = formatDuration(result.duration);
    showOverlay('overOverlay');

    const tip = document.getElementById('saveTip');
    tip.textContent = '正在保存成绩…';
    tip.style.color = 'var(--text-dim)';
    try {
      await api('/api/games', { method: 'POST', body: result });
      tip.textContent = '✓ 成绩已保存，可在个人中心查看';
      tip.style.color = 'var(--green)';
    } catch (err) {
      tip.textContent = '✗ ' + (err.message || '成绩保存失败');
      tip.style.color = 'var(--red)';
    }
  }
})();
