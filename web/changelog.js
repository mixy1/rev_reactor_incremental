/**
 * changelog.js — render site changelog from changelog.json
 */

(async function () {
    const host = document.getElementById('changelog-entries');
    if (!host) return;

    function setMessage(text, cls) {
        host.innerHTML = '';
        const p = document.createElement('p');
        p.className = cls;
        p.textContent = text;
        host.appendChild(p);
    }

    let entries;
    try {
        const resp = await fetch('changelog.json', { cache: 'no-cache' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        entries = await resp.json();
    } catch (_err) {
        setMessage('Failed to load changelog.', 'changelog-error');
        return;
    }

    if (!Array.isArray(entries)) {
        setMessage('Invalid changelog format.', 'changelog-error');
        return;
    }

    const groups = new Map();
    for (const entry of entries) {
        const ts = String(entry.ts ?? '');
        const message = String(entry.message ?? '');
        if (!ts || !message) continue;
        const date = ts.slice(0, 10);
        if (!groups.has(date)) groups.set(date, []);
        groups.get(date).push({ ts, message });
    }

    if (groups.size === 0) {
        setMessage('No changelog entries found.', 'changelog-empty');
        return;
    }

    host.innerHTML = '';
    const dates = Array.from(groups.keys()).reverse();
    for (const date of dates) {
        const article = document.createElement('article');
        article.className = 'changelog-entry';

        const dateEl = document.createElement('div');
        dateEl.className = 'changelog-date';
        dateEl.textContent = date;
        article.appendChild(dateEl);

        const ul = document.createElement('ul');
        for (const item of groups.get(date)) {
            const li = document.createElement('li');
            li.textContent = `${item.ts} ${item.message}`;
            ul.appendChild(li);
        }
        article.appendChild(ul);

        host.appendChild(article);
    }
})();
