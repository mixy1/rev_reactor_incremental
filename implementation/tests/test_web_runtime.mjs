import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const inputSource = readFileSync(new URL('../../web/input.js', import.meta.url), 'utf8');
const rendererSource = readFileSync(new URL('../../web/renderer.js', import.meta.url), 'utf8');
const gameHtmlSource = readFileSync(new URL('../../web/game.html', import.meta.url), 'utf8');
const gameBridgeSource = gameHtmlSource.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const indexHtmlSource = readFileSync(new URL('../../web/index.html', import.meta.url), 'utf8');
const indexScripts = [...indexHtmlSource.matchAll(/<script>\s*([\s\S]*?)<\/script>/g)];
const hostBridgeSource = indexScripts[1][1];

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
    assert.equal(context.Input.pollInput().saveRequested, true);
    assert.equal(context.Input.pollInput().saveRequested, false, 'lifecycle save is edge-triggered');
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

test('renderer wakes one pending frame so hidden-page state can be saved', async () => {
    const document = new FakeEventTarget();
    const window = new FakeEventTarget();
    const ctx = new Proxy({}, {
        get(target, prop) {
            if (!(prop in target)) target[prop] = () => {};
            return target[prop];
        },
    });
    const canvas = makeCanvas(ctx);
    document.hidden = false;
    document.visibilityState = 'visible';
    document.getElementById = () => canvas;
    document.createElement = () => makeCanvas(ctx);

    let rafCallback = null;
    let saveRequests = 0;
    const context = vm.createContext({
        console,
        document,
        window,
        performance: { now: () => 250 },
        devicePixelRatio: 1,
        requestAnimationFrame(callback) {
            rafCallback = callback;
        },
        setTimeout() {
            throw new Error('unexpected timeout');
        },
        Input: {
            wasRecentlyActive: () => true,
            requestLifecycleSave: () => { saveRequests += 1; },
        },
    });
    vm.runInContext(rendererSource, context);

    const frame = context.Renderer.waitFrame();
    assert.ok(rafCallback, 'visible frame is initially waiting for rAF');
    document.hidden = true;
    document.visibilityState = 'hidden';
    document.dispatch('visibilitychange');
    await frame;

    assert.equal(saveRequests, 1);
    assert.equal(context.Renderer.getRuntimeStats().resolvedFrames, 1);
    rafCallback(300); // The obsolete rAF callback must be harmless.
    assert.equal(context.Renderer.getRuntimeStats().resolvedFrames, 1);
});

test('sandbox bridge retries host-state synchronization until save state arrives', async () => {
    const document = new FakeEventTarget();
    const window = new FakeEventTarget();
    const parentMessages = [];
    const parent = {
        postMessage(message) {
            parentMessages.push(message);
        },
    };
    window.parent = parent;
    document.hidden = false;

    const intervals = [];
    const clearedIntervals = new Set();
    const context = vm.createContext({
        console,
        document,
        window,
        localStorage: {
            getItem: () => null,
            setItem: () => {},
        },
        setTimeout: () => 1,
        setInterval(callback, delay) {
            const id = intervals.length + 1;
            intervals.push({ id, callback, delay });
            return id;
        },
        clearInterval(id) {
            clearedIntervals.add(id);
        },
    });
    vm.runInContext(gameBridgeSource, context);

    const countRequests = () => parentMessages.filter(
        message => message.type === 'rev-reactor-host-state-request'
    ).length;
    assert.equal(countRequests(), 1);

    const retry = intervals.find(interval => interval.delay === 250);
    assert.ok(retry, 'host synchronization installs a retry timer');
    retry.callback();
    assert.equal(countRequests(), 2);

    const ready = window.RevReactorHostBridge.waitUntilReady();
    window.dispatch('message', {
        data: {
            type: 'rev-reactor-host-state',
            theme: 'decayed',
            saveText: '{"saved":true}',
        },
    });
    assert.equal(await ready, true);
    assert.equal(window.RevReactorHostBridge.getSaveText(), '{"saved":true}');
    assert.equal(window.RevReactorHostBridge.getTheme(), 'decayed');
    assert.ok(clearedIntervals.has(retry.id));

    retry.callback();
    assert.equal(countRequests(), 2, 'retry stops after host state arrives');
});

test('host bridge survives blocked localStorage and retains the latest save in memory', () => {
    const document = new FakeEventTarget();
    const window = new FakeEventTarget();
    const frame = new FakeEventTarget();
    const postedToChild = [];
    frame.dataset = { baseSrc: 'game.html' };
    frame.contentWindow = {
        postMessage(message) {
            postedToChild.push(message);
        },
    };
    document.hidden = false;
    document.getElementById = (id) => id === 'game-frame' ? frame : null;

    const context = vm.createContext({
        console: { warn: () => {} },
        document,
        window,
        localStorage: {
            getItem() { throw new Error('blocked'); },
            setItem() { throw new Error('blocked'); },
        },
        setInterval: () => 1,
        URL,
    });
    vm.runInContext(hostBridgeSource, context);

    window.dispatch('message', {
        source: frame.contentWindow,
        data: { type: 'rev-reactor-save-write', saveText: '{"tick":42}' },
    });
    window.dispatch('message', {
        source: frame.contentWindow,
        data: { type: 'rev-reactor-host-state-request' },
    });

    const stateMessages = postedToChild.filter(message => message.type === 'rev-reactor-host-state');
    assert.equal(stateMessages.at(-1).saveText, '{"tick":42}');
});
