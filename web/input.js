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
    let lastActivityTime = lastTime;
    let hiddenAt = document.hidden ? lastTime : null;
    let pendingInactiveSeconds = 0;
    let runtimeStarted = false;
    let lifecycleSaveRequested = false;

    function noteActivity() {
        lastActivityTime = performance.now();
    }

    // ── Keyboard ────────────────────────────────────────────────────

    document.addEventListener('keydown', (e) => {
        noteActivity();
        // Prevent browser defaults for game keys
        if (e.keyCode >= 112 && e.keyCode <= 115) e.preventDefault(); // F1-F4
        if (e.keyCode === 32) e.preventDefault(); // Space

        if (!keysDown.has(e.keyCode)) {
            keysPressed.add(e.keyCode);
        }
        keysDown.add(e.keyCode);
    });

    document.addEventListener('keyup', (e) => {
        noteActivity();
        keysDown.delete(e.keyCode);
    });

    // ── Mouse ───────────────────────────────────────────────────────

    function updateMousePosition(e) {
        noteActivity();
        const rect = canvas.getBoundingClientRect();
        mouseX = e.clientX - rect.left;
        mouseY = e.clientY - rect.top;
    }

    canvas.addEventListener('mousemove', updateMousePosition);
    // Keep position updated while dragging outside the canvas.
    document.addEventListener('mousemove', (e) => {
        if (mouseDown.size > 0) {
            updateMousePosition(e);
        }
    });

    canvas.addEventListener('mousedown', (e) => {
        noteActivity();
        // Prevent browser auto-scroll on middle click
        if (e.button === 1) e.preventDefault();

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
        noteActivity();
        mouseDown.delete(e.button);
        mouseReleased.add(e.button);
    });

    // Release held state even when mouseup happens outside the canvas.
    document.addEventListener('mouseup', (e) => {
        mouseDown.delete(e.button);
        mouseReleased.add(e.button);
    });

    // Prevent context menu (game uses right-click for selling)
    canvas.addEventListener('contextmenu', (e) => {
        e.preventDefault();
    });

    // ── Mouse wheel ─────────────────────────────────────────────────

    canvas.addEventListener('wheel', (e) => {
        noteActivity();
        e.preventDefault();
        // Normalize: positive = scroll up (zoom in / scroll up)
        wheelDelta += -e.deltaY / 100;
    }, { passive: false });

    function releaseHeldInput() {
        keysDown.clear();
        mouseDown.clear();
    }

    function requestLifecycleSave() {
        lifecycleSaveRequested = true;
        releaseHeldInput();
    }

    window.addEventListener('blur', releaseHeldInput);
    document.addEventListener('visibilitychange', () => {
        const now = performance.now();
        lastTime = now;
        releaseHeldInput();
        if (document.hidden || document.visibilityState !== 'visible') {
            requestLifecycleSave();
            if (hiddenAt === null) hiddenAt = now;
            return;
        }
        if (hiddenAt !== null) {
            pendingInactiveSeconds += Math.max(0, now - hiddenAt) / 1000;
            hiddenAt = null;
        }
        noteActivity();
    });
    window.addEventListener('pagehide', () => {
        requestLifecycleSave();
    });

    // Do not clear held buttons on mouseleave; we need drag actions to
    // continue when cursor exits and re-enters the game area.

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
        saveRequested: false,
    };

    function _copySetToArr(set, arr) {
        arr.length = 0;
        for (const v of set) arr.push(v);
    }

    function pollInput() {
        const now = performance.now();
        const rawDt = (now - lastTime) / 1000;
        // Hidden time and long browser/device stalls are consumed separately
        // as deterministic catch-up instead of being lost to the frame cap.
        let dt;
        if (rawDt > 1.0) {
            pendingInactiveSeconds += rawDt;
            dt = 0;
        } else {
            dt = Math.min(rawDt, 0.1);
        }
        lastTime = now;

        _state.mouseX = mouseX;
        _state.mouseY = mouseY;
        _state.wheelDelta = wheelDelta;
        _state.dt = dt;
        _state.saveRequested = lifecycleSaveRequested;
        lifecycleSaveRequested = false;

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

    function consumeInactiveSeconds() {
        if (!runtimeStarted) {
            // Save loading already accounts for wall time before the Python
            // runtime starts. Reset here to avoid counting boot time twice.
            const now = performance.now();
            runtimeStarted = true;
            lastTime = now;
            pendingInactiveSeconds = 0;
            hiddenAt = document.hidden ? now : null;
            return 0;
        }
        const elapsed = pendingInactiveSeconds;
        pendingInactiveSeconds = 0;
        return elapsed;
    }

    function wasRecentlyActive(windowMs = 1200) {
        return performance.now() - lastActivityTime <= windowMs;
    }

    return {
        pollInput,
        setFileImport,
        requestFileDialog,
        requestLifecycleSave,
        consumeInactiveSeconds,
        wasRecentlyActive,
    };
})();
