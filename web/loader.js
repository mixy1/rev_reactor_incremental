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

    setProgress(10, `Loading ${manifest.length} sprites...`);

    const images = {};
    let loaded = 0;

    await Promise.all(manifest.map((name) => {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                images[name] = img;
                Renderer.registerTexture(name, img);
                loaded++;
                const pct = 10 + (loaded / manifest.length) * 30;
                setProgress(pct, `Sprites: ${loaded}/${manifest.length}`);
                resolve();
            };
            img.onerror = () => {
                console.warn('Failed to load sprite:', name);
                loaded++;
                resolve();
            };
            img.src = 'assets/sprites/' + name;
        });
    }));

    // ── 2. Initialize Pyodide ───────────────────────────────────────

    setProgress(45, 'Loading Pyodide runtime...');

    const pyodide = await loadPyodide();

    setProgress(65, 'Loading Python source files...');

    // ── 3. Write Python source files to Pyodide virtual FS ──────────

    const srcBase = '../implementation/src/';
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

    for (let i = 0; i < pyFiles.length; i++) {
        const file = pyFiles[i];
        const pct = 65 + (i / pyFiles.length) * 15;
        setProgress(pct, `Loading: ${file}`);
        try {
            const resp = await fetch(srcBase + file);
            const text = await resp.text();
            pyodide.FS.writeFile('/home/pyodide/src/' + file, text);
        } catch (e) {
            console.error('Failed to load Python file:', file, e);
        }
    }

    // Load data files
    for (const { src, dst } of dataFiles) {
        try {
            const resp = await fetch(srcBase + src);
            const text = await resp.text();
            pyodide.FS.writeFile('/home/pyodide/src/' + dst, text);
        } catch (e) {
            console.error('Failed to load data file:', src, e);
        }
    }

    // Load layout.json from implementation root
    try {
        const resp = await fetch('../implementation/layout.json');
        const text = await resp.text();
        pyodide.FS.writeFile('/home/pyodide/src/layout.json', text);
    } catch (e) {
        console.warn('layout.json not found, using defaults');
    }

    setProgress(85, 'Initializing game...');

    // ── 4. Set up JS bridge and start game ──────────────────────────

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
                try {
                    pyodide.runPython(`
from game.save import _handle_file_import
_handle_file_import(${JSON.stringify(reader.result)})
`);
                } catch (err) {
                    console.error('Import error:', err);
                }
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
