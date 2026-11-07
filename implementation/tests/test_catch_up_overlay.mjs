import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const rendererSource = readFileSync(new URL('../../web/renderer.js', import.meta.url), 'utf8');

function load({ hidden = false } = {}) {
    const listeners = new Map();
    const els = {
        'catch-up': { hidden: true },
        'catch-up-status': { textContent: '' },
        'catch-up-bar-fill': { style: { width: '' } },
    };
    const ctx = new Proxy({}, { get(t, p) { if (!(p in t)) t[p] = () => {}; return t[p]; }, set(t, p, v) { t[p] = v; return true; } });
    const canvas = { width: 900, height: 630, style: {}, getContext: () => ctx, addEventListener() {} };
    const document = {
        hidden, visibilityState: hidden ? 'hidden' : 'visible',
        getElementById: (id) => (id === 'game-canvas' ? canvas : els[id] || null),
        createElement: () => ({ getContext: () => ctx, style: {} }),
        addEventListener: (t, f) => listeners.set(t, f),
    };
    const raf = [], timers = [];
    const context = vm.createContext({
        console, document, window: { addEventListener() {} }, devicePixelRatio: 1,
        performance: { now: () => 0 },
        requestAnimationFrame: (cb) => raf.push(cb),
        setTimeout: (cb, ms) => timers.push({ cb, ms }),
        MessageChannel,
    });
    vm.runInContext(rendererSource, context);
    const setHidden = (h) => { document.hidden = h; document.visibilityState = h ? 'hidden' : 'visible'; };
    return { Renderer: context.Renderer, els, raf, timers, setHidden };
}

test('overlay is shown with its text and resolves only after a painted frame', async () => {
    const { Renderer, els, raf } = load();
    let resolved = false;
    const p = Renderer.showBusy('Simulating 20m 00s of time away...').then(() => { resolved = true; });
    assert.equal(els['catch-up'].hidden, false);
    assert.equal(els['catch-up-status'].textContent, 'Simulating 20m 00s of time away...');
    raf.shift()(16); await Promise.resolve();
    assert.equal(resolved, false, 'not before the overlay frame is painted');
    raf.shift()(33); await p;
    assert.equal(resolved, true);
    Renderer.hideBusy();
    assert.equal(els['catch-up'].hidden, true);
});

test('throttled frames: a timeout releases the wait', async () => {
    const { Renderer, raf, timers } = load();
    let resolved = false;
    const p = Renderer.showBusy('x').then(() => { resolved = true; });
    assert.equal(timers[0].ms, 250);
    timers[0].cb(); await p;
    assert.equal(resolved, true);
    raf.shift()(1); raf.length && raf.shift()(2);  // late frames are harmless
});

test('hidden tab: no waiting at all', async () => {
    const { Renderer, raf } = load({ hidden: true });
    await Renderer.showBusy('x');
    assert.equal(raf.length, 0);
});

test('progress bar follows setBusyProgress and resets on show', async () => {
    const { Renderer, els } = load();
    Renderer.showBusy('x');
    assert.equal(els['catch-up-bar-fill'].style.width, '0.0%');
    Renderer.setBusyProgress(0.456);
    assert.equal(els['catch-up-bar-fill'].style.width, '45.6%');
    Renderer.setBusyProgress(7);
    assert.equal(els['catch-up-bar-fill'].style.width, '100.0%');
});

test('yieldToBrowser: visible waits for a frame, hidden only takes a quick turn', async () => {
    const { Renderer, raf, setHidden } = load();
    let resolved = false;
    const p = Renderer.yieldToBrowser().then(() => { resolved = true; });
    await new Promise(r => setTimeout(r, 5));
    assert.equal(resolved, false, 'waits for the frame while visible');
    raf.shift()(16);
    await p;
    assert.equal(resolved, true);

    setHidden(true);
    await Renderer.yieldToBrowser();          // resolves via MessageChannel, no frame needed
    assert.equal(raf.length, 0);
});
