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
        if (e.keyCode >= 112 && e.keyCode <= 116) e.preventDefault(); // F1-F5
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

    function pollInput() {
        const now = performance.now();
        const dt = Math.min((now - lastTime) / 1000, 0.1); // Cap at 100ms
        lastTime = now;

        const state = {
            mouseX,
            mouseY,
            mouseDown: Array.from(mouseDown),
            mousePressed: Array.from(mousePressed),
            mouseReleased: Array.from(mouseReleased),
            wheelDelta,
            keysPressed: Array.from(keysPressed),
            keysDown: Array.from(keysDown),
            dt,
            fileImport: pendingFileImport,
        };

        // Clear per-frame state
        keysPressed.clear();
        mousePressed.clear();
        mouseReleased.clear();
        wheelDelta = 0;
        pendingFileImport = null;

        return state;
    }

    function setFileImport(content) {
        pendingFileImport = content;
    }

    function requestFileDialog() {
        wantFileDialog = true;
    }

    return { pollInput, setFileImport, requestFileDialog };
})();
