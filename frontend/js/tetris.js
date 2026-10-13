/* ======================================================================
   俄罗斯方块核心引擎（纯 Canvas 渲染 + 原生 JS）
   功能：7-bag 随机方块、移动/旋转(带踢墙)/软降/硬降、幽灵投影、
        碰撞与触顶判定、整行消除、连消加分、等级递进、下一块预览
   等级速度与后端 difficulty_level 表保持一致：
        interval = max(800 - (level-1)*55, 80) ms，每消除 10 行升 1 级
   ====================================================================== */

const TETRIS_COLS = 10;
const TETRIS_ROWS = 20;
const CELL = 30;                 // 主棋盘每格像素
const MAX_LEVEL = 15;
const LINES_PER_LEVEL = 10;

// 七种标准方块形状与配色
const SHAPES = {
  I: { color: '#22d3ee', matrix: [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]] },
  J: { color: '#60a5fa', matrix: [[1,0,0],[1,1,1],[0,0,0]] },
  L: { color: '#fb923c', matrix: [[0,0,1],[1,1,1],[0,0,0]] },
  O: { color: '#facc15', matrix: [[1,1],[1,1]] },
  S: { color: '#4ade80', matrix: [[0,1,1],[1,1,0],[0,0,0]] },
  T: { color: '#c084fc', matrix: [[0,1,0],[1,1,1],[0,0,0]] },
  Z: { color: '#f87171', matrix: [[1,1,0],[0,1,1],[0,0,0]] },
};
const TYPES = Object.keys(SHAPES);
const LINE_SCORES = [0, 100, 300, 500, 800];   // 0/1/2/3/4 行基础分（再 × 等级）

function rotateMatrixCW(m) {
  const n = m.length;
  const out = Array.from({ length: n }, () => Array(n).fill(0));
  for (let r = 0; r < n; r++)
    for (let c = 0; c < n; c++)
      out[c][n - 1 - r] = m[r][c];
  return out;
}

class Tetris {
  constructor(boardCanvas, nextCanvas, callbacks = {}) {
    this.boardCtx = boardCanvas.getContext('2d');
    this.nextCtx = nextCanvas.getContext('2d');
    this.cb = callbacks;

    this.state = 'idle';        // idle | playing | paused | over
    this.startLevel = 1;
    this.resetData();

    this._raf = null;
    this._lastFrame = 0;
    this._dropAcc = 0;
    this._playedMs = 0;
    this._lastTimerEmit = 0;
  }

  resetData() {
    this.board = Array.from({ length: TETRIS_ROWS }, () => Array(TETRIS_COLS).fill(null));
    this.bag = [];
    this.current = null;
    this.next = null;
    this.stats = { score: 0, lines: 0, level: this.startLevel, duration: 0 };
    this.startTime = null;
    this.endTime = null;
  }

  /* ---------------- 对局生命周期 ---------------- */
  start(startLevel) {
    cancelAnimationFrame(this._raf);
    this.startLevel = Math.min(Math.max(1, startLevel || 1), MAX_LEVEL);
    this.resetData();
    this.stats.level = this.startLevel;
    this.state = 'playing';
    this.startTime = new Date();
    this.endTime = null;
    this.next = this._takeFromBag();
    this._spawn();
    this._lastFrame = performance.now();
    this._dropAcc = 0;
    this._playedMs = 0;
    this._emitStats();
    this._loop(this._lastFrame);
  }

  togglePause() {
    if (this.state === 'playing') {
      this.state = 'paused';
    } else if (this.state === 'paused') {
      this.state = 'playing';
      this._lastFrame = performance.now();
    }
  }

  /* ---------------- 7-bag 随机发块 ---------------- */
  _takeFromBag() {
    if (this.bag.length === 0) {
      this.bag = TYPES.slice();
      for (let i = this.bag.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [this.bag[i], this.bag[j]] = [this.bag[j], this.bag[i]];
      }
    }
    const type = this.bag.pop();
    return {
      type,
      color: SHAPES[type].color,
      matrix: SHAPES[type].matrix.map(row => row.slice()),
    };
  }

  _spawn() {
    this.current = this.next;
    this.next = this._takeFromBag();
    const size = this.current.matrix.length;
    this.current.x = Math.floor((TETRIS_COLS - size) / 2);
    this.current.y = (type => type === 'I' ? -1 : 0)(this.current.type);
    this._drawNext();
    // 新方块出生即碰撞 -> 游戏结束（触顶判定）
    if (this._collide(this.current.matrix, this.current.x, this.current.y)) {
      this._gameOver();
    }
  }

  /* ---------------- 碰撞 / 边界检测 ---------------- */
  _collide(matrix, px, py) {
    for (let r = 0; r < matrix.length; r++) {
      for (let c = 0; c < matrix[r].length; c++) {
        if (!matrix[r][c]) continue;
        const x = px + c;
        const y = py + r;
        if (x < 0 || x >= TETRIS_COLS || y >= TETRIS_ROWS) return true;
        if (y >= 0 && this.board[y][x]) return true;
      }
    }
    return false;
  }

  /* ---------------- 玩家操作（F-05） ---------------- */
  move(dx) {
    if (this.state !== 'playing') return;
    if (!this._collide(this.current.matrix, this.current.x + dx, this.current.y)) {
      this.current.x += dx;
      this._event('move');
      this._draw();
    }
  }

  rotate() {
    if (this.state !== 'playing') return;
    if (this.current.type === 'O') return;
    const rotated = rotateMatrixCW(this.current.matrix);
    // 简易踢墙：原位 -> 左右 1 格 -> 左右 2 格 -> 上移 1 格
    const kicks = [[0,0],[-1,0],[1,0],[-2,0],[2,0],[0,-1]];
    for (const [kx, ky] of kicks) {
      if (!this._collide(rotated, this.current.x + kx, this.current.y + ky)) {
        this.current.matrix = rotated;
        this.current.x += kx;
        this.current.y += ky;
        this._event('rotate');
        this._draw();
        return;
      }
    }
  }

  softDrop() {
    if (this.state !== 'playing') return;
    if (!this._collide(this.current.matrix, this.current.x, this.current.y + 1)) {
      this.current.y++;
      this.stats.score += 1;
      this._dropAcc = 0;
      this._emitStats();
      this._draw();
    } else {
      this._lock();
    }
  }

  hardDrop() {
    if (this.state !== 'playing') return;
    let dist = 0;
    while (!this._collide(this.current.matrix, this.current.x, this.current.y + 1)) {
      this.current.y++;
      dist++;
    }
    this.stats.score += dist * 2;
    this._event('harddrop');
    this._lock();
  }

  /* ---------------- 落定 / 消行 / 计分（F-06） ---------------- */
  _lock() {
    const m = this.current.matrix;
    let aboveTop = false;
    for (let r = 0; r < m.length; r++) {
      for (let c = 0; c < m[r].length; c++) {
        if (!m[r][c]) continue;
        const x = this.current.x + c;
        const y = this.current.y + r;
        if (y < 0) { aboveTop = true; continue; }
        this.board[y][x] = this.current.color;
      }
    }
    if (aboveTop) { this._gameOver(); return; }

    // 检测并消除整行
    const fullRows = [];
    for (let r = TETRIS_ROWS - 1; r >= 0; r--) {
      if (this.board[r].every(cell => cell !== null)) fullRows.push(r);
    }
    if (fullRows.length > 0) {
      fullRows.forEach(r => {
        this.board.splice(r, 1);
        this.board.unshift(Array(TETRIS_COLS).fill(null));
      });
      const n = fullRows.length;
      this.stats.score += LINE_SCORES[n] * this.stats.level;
      this.stats.lines += n;
      this._event(n >= 4 ? 'tetris' : 'clear');

      // 难度等级递进（F-07）
      const newLevel = Math.min(this.startLevel + Math.floor(this.stats.lines / LINES_PER_LEVEL), MAX_LEVEL);
      if (newLevel > this.stats.level) {
        this.stats.level = newLevel;
        this._event('levelup');
      }
    } else {
      this._event('lock');
    }
    this._emitStats();
    this._spawn();
    this._draw();
  }

  _gameOver() {
    this.state = 'over';
    this.endTime = new Date();
    cancelAnimationFrame(this._raf);
    this._draw();
    this._event('gameover');
    this.cb.onGameOver && this.cb.onGameOver({
      score: this.stats.score,
      lines_cleared: this.stats.lines,
      level: this.stats.level,
      duration: Math.round(this._playedMs / 1000),
      start_time: formatDateTime(this.startTime),
      end_time: formatDateTime(this.endTime),
    });
  }

  /* ---------------- 主循环：重力下落 + 计时 ---------------- */
  _loop = (now) => {
    if (this.state === 'over') return;
    const delta = now - this._lastFrame;
    this._lastFrame = now;

    if (this.state === 'playing') {
      this._playedMs += delta;
      this._dropAcc += delta;
      const interval = Math.max(800 - (this.stats.level - 1) * 55, 80);
      while (this._dropAcc >= interval) {
        this._dropAcc -= interval;
        if (!this._collide(this.current.matrix, this.current.x, this.current.y + 1)) {
          this.current.y++;
        } else {
          this._lock();
          break;
        }
      }
      // 计时显示每秒刷新一次
      const sec = Math.floor(this._playedMs / 1000);
      if (sec !== this.stats.duration) {
        this.stats.duration = sec;
        if (now - this._lastTimerEmit > 200) {
          this._lastTimerEmit = now;
          this._emitStats();
        }
      }
    }
    this._draw();
    this._raf = requestAnimationFrame(this._loop);
  };

  /* ---------------- 渲染 ---------------- */
  _draw() {
    const ctx = this.boardCtx;
    ctx.clearRect(0, 0, TETRIS_COLS * CELL, TETRIS_ROWS * CELL);

    // 背景网格
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let x = 1; x < TETRIS_COLS; x++) {
      ctx.beginPath(); ctx.moveTo(x * CELL + .5, 0); ctx.lineTo(x * CELL + .5, TETRIS_ROWS * CELL); ctx.stroke();
    }
    for (let y = 1; y < TETRIS_ROWS; y++) {
      ctx.beginPath(); ctx.moveTo(0, y * CELL + .5); ctx.lineTo(TETRIS_COLS * CELL, y * CELL + .5); ctx.stroke();
    }

    // 已落定方块
    for (let r = 0; r < TETRIS_ROWS; r++)
      for (let c = 0; c < TETRIS_COLS; c++)
        if (this.board[r][c]) this._drawCell(ctx, c, r, this.board[r][c], CELL, 1);

    if (this.current && this.state !== 'over') {
      // 幽灵投影
      let ghostY = this.current.y;
      while (!this._collide(this.current.matrix, this.current.x, ghostY + 1)) ghostY++;
      this._drawPiece(ctx, this.current.matrix, this.current.x, ghostY, this.current.color, CELL, true);
      // 当前方块
      this._drawPiece(ctx, this.current.matrix, this.current.x, this.current.y, this.current.color, CELL, false);
    }
  }

  _drawPiece(ctx, matrix, px, py, color, size, ghost) {
    for (let r = 0; r < matrix.length; r++)
      for (let c = 0; c < matrix[r].length; c++)
        if (matrix[r][c] && py + r >= 0)
          this._drawCell(ctx, px + c, py + r, color, size, ghost ? 0.22 : 1);
  }

  _drawCell(ctx, col, row, color, size, alpha) {
    const x = col * size, y = row * size, pad = 1;
    ctx.save();
    ctx.globalAlpha = alpha;
    if (alpha < 1) {
      // 幽灵方块：仅描边
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x + 3, y + 3, size - 6, size - 6);
    } else {
      const grad = ctx.createLinearGradient(x, y, x + size, y + size);
      grad.addColorStop(0, color);
      grad.addColorStop(1, this._shade(color, -30));
      ctx.fillStyle = grad;
      ctx.fillRect(x + pad, y + pad, size - pad * 2, size - pad * 2);
      // 高光
      ctx.fillStyle = 'rgba(255,255,255,.28)';
      ctx.fillRect(x + pad, y + pad, size - pad * 2, 4);
      ctx.fillRect(x + pad, y + pad, 4, size - pad * 2);
      // 暗边
      ctx.fillStyle = 'rgba(0,0,0,.22)';
      ctx.fillRect(x + pad, y + size - pad - 4, size - pad * 2, 4);
    }
    ctx.restore();
  }

  _drawNext() {
    const ctx = this.nextCtx;
    const W = ctx.canvas.width;
    ctx.clearRect(0, 0, W, W);
    if (!this.next) return;
    const size = 24;
    const m = this.next.matrix;
    // 按实际占用边界居中
    let minR = 99, maxR = -1, minC = 99, maxC = -1;
    for (let r = 0; r < m.length; r++)
      for (let c = 0; c < m[r].length; c++)
        if (m[r][c]) { minR = Math.min(minR, r); maxR = Math.max(maxR, r); minC = Math.min(minC, c); maxC = Math.max(maxC, c); }
    const pieceW = (maxC - minC + 1) * size;
    const pieceH = (maxR - minR + 1) * size;
    const offX = (W - pieceW) / 2 - minC * size;
    const offY = (W - pieceH) / 2 - minR * size;
    ctx.save();
    ctx.translate(offX, offY);
    for (let r = minR; r <= maxR; r++)
      for (let c = minC; c <= maxC; c++)
        if (m[r][c]) this._drawCell(ctx, c, r, this.next.color, size, 1);
    ctx.restore();
  }

  _shade(hex, amount) {
    const n = parseInt(hex.slice(1), 16);
    const clamp = v => Math.max(0, Math.min(255, v));
    const r = clamp((n >> 16) + amount), g = clamp(((n >> 8) & 255) + amount), b = clamp((n & 255) + amount);
    return `rgb(${r},${g},${b})`;
  }

  _event(name) { this.cb.onEvent && this.cb.onEvent(name); }
  _emitStats() { this.cb.onStats && this.cb.onStats(this.stats); }
}
