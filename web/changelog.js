/**
 * changelog.js — render site changelog from web/changelog.txt
 *
 * File format:
 *   YYYY-MM-DD<TAB>message
 *   YYYY-MM-DD|message
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

    let text;
    try {
        const resp = await fetch('changelog.txt', { cache: 'no-cache' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        text = await resp.text();
    } catch (_err) {
        setMessage('Failed to load changelog.', 'changelog-error');
        return;
    }

    const lines = text
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line.length > 0 && !line.startsWith('#'));

    const groups = new Map();
    for (const line of lines) {
        const match = line.match(/^(\d{4}-\d{2}-\d{2})\s*(?:\t|\|)\s*(.+)$/);
        if (!match) continue;
        const date = match[1];
        const message = match[2];
        if (!groups.has(date)) groups.set(date, []);
        groups.get(date).push(message);
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
        for (const message of groups.get(date)) {
            const li = document.createElement('li');
            li.textContent = message;
            ul.appendChild(li);
        }
        article.appendChild(ul);

        host.appendChild(article);
    }
})();

