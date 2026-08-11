import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const inputSource = readFileSync(new URL('../../web/input.js', import.meta.url), 'utf8');
const rendererSource = readFileSync(new URL('../../web/renderer.js', import.meta.url), 'utf8');

class FakeEventTarget {
    constructor() {
        this.listeners = new Map();
    }

    addEventListener(type, callback) {
        const callbacks = this.listeners.get(type) || [];
        callbacks.push(callback);
        this.listeners.set(type, callbacks);
    }

    dispatch(type, event = {}) {
        for (const callback of this.listeners.get(type) || []) callback(event);
    }
}

function makeCanvas(context = {}) {
    const canvas = new FakeEventTarget();
    canvas.width = 900;
    canvas.height = 630;
    canvas.style = {};
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0 });
    canvas.getContext = () => context;
    return canvas;
}

test('input ignores boot time and reports hidden/long-stall catch-up once', () => {
    let now = 0;
    const document = new FakeEventTarget();
    const window = new FakeEventTarget();
    const canvas = makeCanvas();
    document.hidden = false;
    document.visibilityState = 'visible';
    document.getElementById = (id) => id === 'game-canvas' ? canvas : null;

    const context = vm.createContext({
        console,
        document,
        window,
        performance: { now: () => now },
    });
    vm.runInContext(inputSource, context);

    now = 5_000;
    assert.equal(context.Input.consumeInactiveSeconds(), 0, 'boot time is not offline time');

    document.hidden = true;
    document.visibilityState = 'hidden';
    document.dispatch('visibilitychange');
    now = 8_250;
    document.hidden = false;
    document.visibilityState = 'visible';
    document.dispatch('visibilitychange');
    assert.equal(context.Input.consumeInactiveSeconds(), 3.25);
    assert.equal(context.Input.consumeInactiveSeconds(), 0, 'elapsed time is consumed once');

    context.Input.pollInput();
    now = 10_750;
    const stalledFrame = context.Input.pollInput();
    assert.equal(stalledFrame.dt, 0);
    assert.equal(context.Input.consumeInactiveSeconds(), 2.5);
});

test('renderer performs no frame scheduling while hidden and resumes once visible', async () => {
    const document = new FakeEventTarget();
    const window = new FakeEventTarget();
    const ctx = new Proxy({}, {
        get(target, prop) {
            if (!(prop in target)) target[prop] = () => {};
            return target[prop];
        },
        set(target, prop, value) {
            target[prop] = value;
            return true;
        },
    });
    const canvas = makeCanvas(ctx);
    document.hidden = true;
    document.visibilityState = 'hidden';
    document.getElementById = () => canvas;
    document.createElement = () => makeCanvas(ctx);

    let rafCallback = null;
    let rafCalls = 0;
    let timeoutCalls = 0;
    const context = vm.createContext({
        console,
        document,
        window,
        performance: { now: () => 100 },
        devicePixelRatio: 1,
        requestAnimationFrame(callback) {
            rafCalls += 1;
            rafCallback = callback;
        },
        setTimeout(callback) {
            timeoutCalls += 1;
            callback();
        },
        Input: { wasRecentlyActive: () => false },
    });
    vm.runInContext(rendererSource, context);

    const frame = context.Renderer.waitFrame();
    assert.equal(rafCalls, 0);
    assert.equal(timeoutCalls, 0);

    document.hidden = false;
    document.visibilityState = 'visible';
    document.dispatch('visibilitychange');
    assert.equal(rafCalls, 1);
    rafCallback(100);
    await frame;
    assert.equal(context.Renderer.getRuntimeStats().resolvedFrames, 1);
});
