/**
 * input.js — Keyboard + mouse input capture for Rev Reactor web port.
 *
 * Captures all input events on the canvas and provides a pollInput()
 * function that returns a snapshot of the current frame's input state
 * and clears per-frame flags (pressed/released).
 */

globalThis.Input = (() => {
    const canvas = document.getElementById('game-canvas');

    // Per-frame edge-triggered state (cleared each poll)
    const keysPressed = new Set();    // keyCode pressed this frame
    const mousePressed = new Set();   // button pressed this frame
    const mouseReleased = new Set();  // button released this frame

    // Held state (persistent across frames)
    const keysDown = new Set();       // keyCode currently held
    const mouseDown = new Set();      // button currently held

    let mouseX = 0;
    let mouseY = 0;
    let wheelDelta = 0;
    let pendingFileImport = null;  // Set by file input handler
    let wantFileDialog = false;    // Set by Python, consumed by next mousedown

    // Timing
    let lastTime = performance.now();

    // ── Keyboard ────────────────────────────────────────────────────

    document.addEventListener('keydown', (e) => {
        // Prevent browser defaults for game keys
        if (e.keyCode >= 112 && e.keyCode <= 115) e.preventDefault(); // F1-F4
        if (e.keyCode === 32) e.preventDefault(); // Space

        if (!keysDown.has(e.keyCode)) {
            keysPressed.add(e.keyCode);
        }
        keysDown.add(e.keyCode);
    });

    document.addEventListener('keyup', (e) => {
        keysDown.delete(e.keyCode);
    });

    // ── Mouse ───────────────────────────────────────────────────────

    canvas.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        mouseX = e.clientX - rect.left;
        mouseY = e.clientY - rect.top;
    });

    canvas.addEventListener('mousedown', (e) => {
        if (!mouseDown.has(e.button)) {
            mousePressed.add(e.button);
        }
        mouseDown.add(e.button);

        // Trigger file dialog from user gesture context
        if (wantFileDialog) {
            wantFileDialog = false;
            const fi = document.getElementById('file-input');
            if (fi) {
                fi.value = '';
                fi.click();
            }
        }
    });

    canvas.addEventListener('mouseup', (e) => {
        mouseDown.delete(e.button);
        mouseReleased.add(e.button);
    });

    // Prevent context menu (game uses right-click for selling)
    canvas.addEventListener('contextmenu', (e) => {
        e.preventDefault();
    });

    // ── Mouse wheel ─────────────────────────────────────────────────

    canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        // Normalize: positive = scroll up (zoom in / scroll up)
        wheelDelta += -e.deltaY / 100;
    }, { passive: false });

    // Handle mouse leaving the canvas
    canvas.addEventListener('mouseleave', () => {
        mouseDown.clear();
    });

    // ── Poll interface ──────────────────────────────────────────────

    // Pre-allocated arrays and state object — reused every frame
    const _mdArr = [];
    const _mpArr = [];
    const _mrArr = [];
    const _kpArr = [];
    const _kdArr = [];
    const _state = {
        mouseX: 0, mouseY: 0,
        mouseDown: _mdArr, mousePressed: _mpArr, mouseReleased: _mrArr,
        wheelDelta: 0,
        keysPressed: _kpArr, keysDown: _kdArr,
        dt: 0,
    };

    function _copySetToArr(set, arr) {
        arr.length = 0;
        for (const v of set) arr.push(v);
    }

    function pollInput() {
        const now = performance.now();
        const rawDt = (now - lastTime) / 1000;
        // Foreground: keep old tight cap to avoid giant catch-up after hiccups.
        // Background: allow larger dt so hidden-tab timers still progress sim.
        const dtCap = (document.hidden || document.visibilityState !== 'visible') ? 5.0 : 0.1;
        const dt = Math.min(rawDt, dtCap);
        lastTime = now;

        _state.mouseX = mouseX;
        _state.mouseY = mouseY;
        _state.wheelDelta = wheelDelta;
        _state.dt = dt;

        _copySetToArr(mouseDown, _mdArr);
        _copySetToArr(mousePressed, _mpArr);
        _copySetToArr(mouseReleased, _mrArr);
        _copySetToArr(keysPressed, _kpArr);
        _copySetToArr(keysDown, _kdArr);

        // Include file import content only when present (avoids null/None proxy issues)
        if (pendingFileImport !== null) {
            _state.fileImport = pendingFileImport;
            pendingFileImport = null;
        } else {
            delete _state.fileImport;
        }

        // Clear per-frame state
        keysPressed.clear();
        mousePressed.clear();
        mouseReleased.clear();
        wheelDelta = 0;

        return _state;
    }

    function setFileImport(content) {
        pendingFileImport = content;
    }

    function requestFileDialog() {
        wantFileDialog = true;
    }

    return { pollInput, setFileImport, requestFileDialog };
})();
