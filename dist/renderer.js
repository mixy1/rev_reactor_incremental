/**
 * renderer.js — Canvas2D batch renderer for Rev Reactor web port.
 *
 * Reads a Float64Array of draw commands from Python and executes them
 * as Canvas2D calls.  One FFI call per frame instead of ~300.
 *
 * Opcodes:
 *   0  CLEAR_BG        r,g,b,a                          (5 values)
 *   1  FILL_RECT        x,y,w,h,r,g,b,a                 (9 values)
 *   2  STROKE_RECT      x,y,w,h,r,g,b,a                 (9 values)
 *   3  DRAW_TEXT         strIdx,x,y,size,r,g,b,a         (9 values)
 *   4  TEXTURE_PRO       texId,sx,sy,sw,sh,dx,dy,dw,dh,r,g,b,a  (14 values)
 *   5  TEXTURE_EX        texId,x,y,rot,scale,r,g,b,a    (10 values)
 *   6  BEGIN_SCISSOR     x,y,w,h                         (5 values)
 *   7  END_SCISSOR       (none)                           (1 value)
 */

globalThis.Renderer = (() => {
    const canvas = document.getElementById('game-canvas');
    const ctx = canvas.getContext('2d');

    // Texture registry: id -> { img, name }
    const textures = {};       // id -> Image
    const texturesByName = {}; // name -> { id, img }
    let nextId = 1;

    // Temp canvas for color tinting
    let _tintCanvas = null;
    let _tintCtx = null;

    function getTintCanvas(w, h) {
        if (!_tintCanvas) {
            _tintCanvas = document.createElement('canvas');
            _tintCtx = _tintCanvas.getContext('2d');
        }
        if (_tintCanvas.width < w) _tintCanvas.width = w;
        if (_tintCanvas.height < h) _tintCanvas.height = h;
        return { canvas: _tintCanvas, ctx: _tintCtx };
    }

    function registerTexture(name, img) {
        const id = nextId++;
        textures[id] = img;
        texturesByName[name] = { id, img };
        return id;
    }

    function getTextureInfo(name) {
        const entry = texturesByName[name];
        if (!entry) return null;
        return {
            id: entry.id,
            width: entry.img.naturalWidth || entry.img.width,
            height: entry.img.naturalHeight || entry.img.height,
        };
    }

    function rgba(r, g, b, a) {
        return `rgba(${r|0},${g|0},${b|0},${(a/255).toFixed(3)})`;
    }

    function measureTextWidth(text, size) {
        ctx.font = `${size}px monospace`;
        return ctx.measureText(text).width;
    }

    /**
     * Draw a texture with tint handling.
     * Fast paths for common tint patterns; offscreen composite for color tints.
     */
    function drawImageTinted(img, sx, sy, sw, sh, dx, dy, dw, dh, r, g, b, a) {
        if (r === 255 && g === 255 && b === 255 && a === 255) {
            // No tint — direct draw (fast path, ~90% of calls)
            ctx.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh);
            return;
        }

        if (r === 255 && g === 255 && b === 255) {
            // Alpha-only tint
            const prev = ctx.globalAlpha;
            ctx.globalAlpha = a / 255;
            ctx.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh);
            ctx.globalAlpha = prev;
            return;
        }

        // Grayscale dim: fall through to multiply-composite path
        // (approximating with alpha makes textures transparent, not darker)

        // Color tint (e.g. green highlight) — offscreen composite
        const tw = Math.ceil(Math.abs(sw));
        const th = Math.ceil(Math.abs(sh));
        if (tw === 0 || th === 0) return;

        const { canvas: tc, ctx: tctx } = getTintCanvas(tw, th);
        tctx.clearRect(0, 0, tw, th);

        // Draw source region
        tctx.globalCompositeOperation = 'source-over';
        tctx.globalAlpha = 1;
        tctx.drawImage(img, sx, sy, sw, sh, 0, 0, tw, th);

        // Multiply with tint color
        tctx.globalCompositeOperation = 'multiply';
        tctx.fillStyle = `rgb(${r|0},${g|0},${b|0})`;
        tctx.fillRect(0, 0, tw, th);

        // Restore alpha from original
        tctx.globalCompositeOperation = 'destination-in';
        tctx.drawImage(img, sx, sy, sw, sh, 0, 0, tw, th);

        // Blit to main canvas
        const prev = ctx.globalAlpha;
        ctx.globalAlpha = a / 255;
        ctx.drawImage(tc, 0, 0, tw, th, dx, dy, dw, dh);
        ctx.globalAlpha = prev;
    }

    /**
     * Main entry point: process the command buffer.
     * @param {Float64Array} cmds - Command array from Python
     * @param {Array<string>} strings - String table for text commands
     */
    function renderBatch(cmds, strings) {
        const len = cmds.length;
        let i = 0;

        while (i < len) {
            const op = cmds[i++];

            switch (op) {
                case 0: { // CLEAR_BG: r,g,b,a
                    const r = cmds[i++], g = cmds[i++], b = cmds[i++], a = cmds[i++];
                    ctx.fillStyle = rgba(r, g, b, a);
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    break;
                }
                case 1: { // FILL_RECT: x,y,w,h,r,g,b,a
                    const x = cmds[i++], y = cmds[i++], w = cmds[i++], h = cmds[i++];
                    const r = cmds[i++], g = cmds[i++], b = cmds[i++], a = cmds[i++];
                    const prev = ctx.globalAlpha;
                    ctx.globalAlpha = a / 255;
                    ctx.fillStyle = `rgb(${r|0},${g|0},${b|0})`;
                    ctx.fillRect(x, y, w, h);
                    ctx.globalAlpha = prev;
                    break;
                }
                case 2: { // STROKE_RECT: x,y,w,h,r,g,b,a
                    const x = cmds[i++], y = cmds[i++], w = cmds[i++], h = cmds[i++];
                    const r = cmds[i++], g = cmds[i++], b = cmds[i++], a = cmds[i++];
                    const prev = ctx.globalAlpha;
                    ctx.globalAlpha = a / 255;
                    ctx.strokeStyle = `rgb(${r|0},${g|0},${b|0})`;
                    ctx.lineWidth = 1;
                    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
                    ctx.globalAlpha = prev;
                    break;
                }
                case 3: { // DRAW_TEXT: strIdx,x,y,size,r,g,b,a
                    const strIdx = cmds[i++] | 0;
                    const x = cmds[i++], y = cmds[i++], size = cmds[i++];
                    const r = cmds[i++], g = cmds[i++], b = cmds[i++], a = cmds[i++];
                    ctx.font = `${size}px monospace`;
                    ctx.fillStyle = rgba(r, g, b, a);
                    ctx.textBaseline = 'top';
                    ctx.fillText(strings[strIdx] || '', x, y);
                    break;
                }
                case 4: { // TEXTURE_PRO: texId,sx,sy,sw,sh,dx,dy,dw,dh,r,g,b,a
                    const texId = cmds[i++] | 0;
                    const sx = cmds[i++], sy = cmds[i++], sw = cmds[i++], sh = cmds[i++];
                    const dx = cmds[i++], dy = cmds[i++], dw = cmds[i++], dh = cmds[i++];
                    const r = cmds[i++], g = cmds[i++], b = cmds[i++], a = cmds[i++];
                    const img = textures[texId];
                    if (img) {
                        drawImageTinted(img, sx, sy, sw, sh, dx, dy, dw, dh, r, g, b, a);
                    }
                    break;
                }
                case 5: { // TEXTURE_EX: texId,x,y,rot,scale,r,g,b,a
                    const texId = cmds[i++] | 0;
                    const x = cmds[i++], y = cmds[i++];
                    const rot = cmds[i++], scale = cmds[i++];
                    const r = cmds[i++], g = cmds[i++], b = cmds[i++], a = cmds[i++];
                    const img = textures[texId];
                    if (img) {
                        const w = img.naturalWidth * scale;
                        const h = img.naturalHeight * scale;
                        if (rot === 0) {
                            drawImageTinted(img, 0, 0, img.naturalWidth, img.naturalHeight,
                                          x, y, w, h, r, g, b, a);
                        } else {
                            ctx.save();
                            ctx.translate(x + w/2, y + h/2);
                            ctx.rotate(rot * Math.PI / 180);
                            drawImageTinted(img, 0, 0, img.naturalWidth, img.naturalHeight,
                                          -w/2, -h/2, w, h, r, g, b, a);
                            ctx.restore();
                        }
                    }
                    break;
                }
                case 6: { // BEGIN_SCISSOR: x,y,w,h
                    const x = cmds[i++], y = cmds[i++], w = cmds[i++], h = cmds[i++];
                    ctx.save();
                    ctx.beginPath();
                    ctx.rect(x, y, w, h);
                    ctx.clip();
                    break;
                }
                case 7: { // END_SCISSOR
                    ctx.restore();
                    break;
                }
                default:
                    console.warn('Unknown opcode:', op, 'at index', i - 1);
                    return; // Bail out to avoid desync
            }
        }
    }

    return {
        canvas,
        ctx,
        registerTexture,
        getTextureInfo,
        measureTextWidth,
        renderBatch,
        textures,
    };
})();
