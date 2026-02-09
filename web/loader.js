/**
 * loader.js — Pyodide bootstrap and asset preloading for Rev Reactor web port.
 *
 * 1. Preloads all PNG sprites as Image objects
 * 2. Initializes Pyodide and writes Python source files to virtual FS
 * 3. Sets up the JS↔Python bridge
 * 4. Starts the game loop
 */

(async function () {
    const loadingBar = document.getElementById('loading-bar');
    const loadingStatus = document.getElementById('loading-status');
    const loadingDiv = document.getElementById('loading');

    function setProgress(pct, msg) {
        loadingBar.style.width = pct + '%';
        if (msg) loadingStatus.textContent = msg;
    }

    // ── 1. Load sprite manifest and preload images ──────────────────

    setProgress(5, 'Loading sprite manifest...');

    let manifest;
    try {
        const resp = await fetch('manifest.json');
        manifest = await resp.json();
    } catch (e) {
        loadingStatus.textContent = 'Error: manifest.json not found. Run build_web.sh first.';
        return;
    }

    setProgress(10, `Loading sprites + Pyodide...`);

    // Load sprites and Pyodide in parallel (both are large independent downloads)
    const images = {};
    let spriteCount = 0;

    const spritePromise = Promise.all(manifest.map((name) => {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                images[name] = img;
                Renderer.registerTexture(name, img);
                spriteCount++;
                resolve();
            };
            img.onerror = () => {
                console.warn('Failed to load sprite:', name);
                spriteCount++;
                resolve();
            };
            img.src = 'assets/sprites/' + name;
        });
    }));

    const pyodidePromise = loadPyodide();

    const [, pyodide] = await Promise.all([spritePromise, pyodidePromise]);

    setProgress(50, `Loaded ${spriteCount} sprites + Pyodide`);

    setProgress(65, 'Loading Python source files...');

    // ── 3. Write Python source files to Pyodide virtual FS ──────────

    // Source base: overridable via <meta name="src-base">, defaults to 'src/'
    const srcMeta = document.querySelector('meta[name="src-base"]');
    const srcBase = srcMeta ? srcMeta.content : 'src/';
    const pyFiles = [
        'raylib_compat.py',
        'main.py',
        'assets.py',
        'game/__init__.py',
        'game/types.py',
        'game/store.py',
        'game/simulation.py',
        'game/catalog.py',
        'game/upgrades.py',
        'game/layout.py',
        'game/grid.py',
        'game/save.py',
        'game/ui.py',
    ];

    const dataFiles = [
        { src: 'game/upgrade_data.json', dst: 'game/upgrade_data.json' },
        { src: 'game/component_types.json', dst: 'game/component_types.json' },
        { src: 'game/stringliterals_web.json', dst: 'game/stringliterals_web.json' },
    ];

    // Create directories in VFS
    pyodide.FS.mkdirTree('/home/pyodide/src/game');

    // Fetch all Python, data, and config files in parallel
    const allFiles = [
        ...pyFiles.map(f => ({ url: srcBase + f, dst: f })),
        ...dataFiles.map(f => ({ url: srcBase + f.src, dst: f.dst })),
        { url: srcBase + '../layout.json', dst: 'layout.json', optional: true },
    ];

    let filesLoaded = 0;
    const fileResults = await Promise.all(allFiles.map(async ({ url, dst, optional }) => {
        try {
            const resp = await fetch(url);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const text = await resp.text();
            filesLoaded++;
            const pct = 65 + (filesLoaded / allFiles.length) * 15;
            setProgress(pct, `Files: ${filesLoaded}/${allFiles.length}`);
            return { dst, text };
        } catch (e) {
            if (optional) {
                console.warn(`${dst} not found, using defaults`);
            } else {
                console.error('Failed to load file:', url, e);
            }
            return null;
        }
    }));

    // Write all fetched files to VFS
    for (const result of fileResults) {
        if (result) {
            pyodide.FS.writeFile('/home/pyodide/src/' + result.dst, result.text);
        }
    }

    setProgress(85, 'Initializing game...');

    // ── 4. Set up JS bridge and start game ──────────────────────────

    // Pass Emscripten Module to renderer for zero-copy command buffer reads
    Renderer.setWasmMemory(pyodide._module);

    // Add src to Python path
    pyodide.runPython(`
import sys
sys.path.insert(0, '/home/pyodide/src')
import os
os.chdir('/home/pyodide/src')
`);

    // Register JS bridge functions
    pyodide.runPython(`
import raylib_compat
from pyodide.ffi import create_proxy
from js import Renderer, Input

raylib_compat._set_js_bridge(
    render_batch=create_proxy(Renderer.renderBatch),
    measure_text_fn=create_proxy(Renderer.measureTextWidth),
    get_texture_info=create_proxy(Renderer.getTextureInfo),
    poll_input=create_proxy(Input.pollInput),
)
`);

    // Set up file import handler for save import
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = () => {
                // Queue file content for Python to pick up on next frame poll.
                // Cannot call runPython here — Pyodide doesn't support concurrent
                // Python execution while the async main loop is running.
                Input.setFileImport(reader.result);
            };
            reader.readAsText(file);
        });
    }

    setProgress(95, 'Starting game...');

    // Hide loading screen
    loadingDiv.style.display = 'none';

    // Auto-save on page unload
    window.addEventListener('beforeunload', () => {
        try {
            pyodide.runPython(`
try:
    from game.save import save_game as _auto_save
    from main import _sim_ref
    if _sim_ref is not None:
        _auto_save(_sim_ref, None)
except Exception:
    pass
`);
        } catch (e) {
            // Best-effort save
        }
    });

    // ── 5. Version polling ────────────────────────────────────────────

    (async function versionCheck() {
        let currentVersion;
        try {
            const resp = await fetch('version.txt', { cache: 'no-cache' });
            if (!resp.ok) return;
            currentVersion = (await resp.text()).trim();
        } catch (_) { return; }

        const POLL_MS = 2 * 60 * 1000; // 2 minutes
        const tid = setInterval(async () => {
            if (document.hidden) return;
            try {
                const resp = await fetch('version.txt', { cache: 'no-cache' });
                if (!resp.ok) return;
                const latest = (await resp.text()).trim();
                if (latest !== currentVersion) {
                    clearInterval(tid);
                    const bar = document.createElement('div');
                    bar.style.cssText =
                        'position:fixed;top:0;left:0;right:0;z-index:999;' +
                        'background:#1a6b2a;color:#fff;text-align:center;' +
                        'padding:8px;font-size:14px;cursor:pointer;' +
                        'font-family:Inter,sans-serif;';
                    bar.textContent = 'A new version is available — click to refresh';
                    bar.addEventListener('click', () => location.reload());
                    document.body.prepend(bar);
                }
            } catch (_) { /* retry next interval */ }
        }, POLL_MS);
    })();

    // ── 6. Theme management ─────────────────────────────────────────

    const defaultImages = {};  // name -> original Image (captured at load)
    const altImages = {};      // name -> alt theme Image (lazy-loaded)
    let altLoaded = false;
    let currentTheme = localStorage.getItem('sprite-theme') || 'default';

    // Snapshot the original images so we can restore them later
    for (const [name, entry] of Object.entries(Renderer.texturesByName)) {
        defaultImages[name] = entry.img;
    }

    async function loadAltSprites() {
        if (altLoaded) return;
        const promises = manifest.map((name) => {
            return new Promise((resolve) => {
                const img = new Image();
                img.onload = () => { altImages[name] = img; resolve(); };
                img.onerror = () => { resolve(); };  // fall back to default
                img.src = 'assets/sprites_decayed/' + name;
            });
        });
        await Promise.all(promises);
        altLoaded = true;
    }

    async function setTheme(theme) {
        currentTheme = theme;
        localStorage.setItem('sprite-theme', theme);
        const btn = document.getElementById('theme-toggle');

        if (theme === 'decayed') {
            await loadAltSprites();
            for (const name of manifest) {
                if (altImages[name]) {
                    Renderer.swapTexture(name, altImages[name]);
                }
            }
            if (btn) btn.classList.add('decayed-active');
        } else {
            for (const name of manifest) {
                if (defaultImages[name]) {
                    Renderer.swapTexture(name, defaultImages[name]);
                }
            }
            if (btn) btn.classList.remove('decayed-active');
        }
    }

    // Wire up the toggle button
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            setTheme(currentTheme === 'decayed' ? 'default' : 'decayed');
        });
    }

    // Apply saved theme preference (non-blocking)
    if (currentTheme === 'decayed') {
        setTheme('decayed');
    }

    // Start the game
    try {
        await pyodide.runPythonAsync(`
import main
await main.main()
`);
    } catch (e) {
        console.error('Game error:', e);
        loadingDiv.style.display = 'block';
        loadingStatus.textContent = 'Game error: ' + e.message;
    }
})();
