// ── app.js — DOG Rune Flow Intel Dashboard ─────────────────────────── */

const API_BASE = 'https://rickthor.pythonanywhere.com/api';

// Exchange color map — must match seed_clusters.py entity_name values
const EXCHANGE_COLORS = {
    'Binance':  '#f0b90b',
    'OKX':      '#22d3a1',
    'Coinbase': '#3b82f6',
    'Bybit':    '#f59e0b',
    'Kraken':   '#7c3aed',
    'Gate.io':  '#ec4899',
};

let currentData = null;
let activeRange = '24h';

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n) {
    if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B';
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M';
    if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return n.toLocaleString();
}

function fmtUSD(n) {
    return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
}

function fmtFull(n) {
    return n.toLocaleString() + ' DOG';
}

function signal(net) {
    if (net > 0) return '<span class="signal bullish">ACCUMULATE</span>';
    if (net < 0) return '<span class="signal bearish">DISTRIBUTE</span>';
    return '<span class="signal neutral">NEUTRAL</span>';
}

function showTooltip(html, event) {
    const tip = document.getElementById('tooltip');
    tip.innerHTML = html;
    tip.classList.add('visible');
    posTooltip(event);
}

function hideTooltip() {
    document.getElementById('tooltip').classList.remove('visible');
}

function posTooltip(event) {
    const tip = document.getElementById('tooltip');
    const x = event.clientX + 12;
    const y = event.clientY - 10;
    tip.style.left = Math.min(x, window.innerWidth - 280) + 'px';
    tip.style.top  = Math.min(y, window.innerHeight - 100) + 'px';
}

document.addEventListener('mousemove', e => {
    if (document.getElementById('tooltip').classList.contains('visible')) posTooltip(e);
});

// ── Mock Data (fallback when server is offline) ───────────────────────────────

function getMockData(range) {
    const multiplier = range === '30d' ? 30 : range === '7d' ? 7 : 1;
    return {
        price_usd: 0.0072,
        hours: range === '30d' ? 720 : range === '7d' ? 168 : 24,
        total_inflow:   865_000_000 * multiplier,
        total_outflow:  255_000_000 * multiplier,
        net_accumulation: 610_000_000 * multiplier,
        total_inflow_usd:   865_000_000 * multiplier * 0.0072,
        total_outflow_usd:  255_000_000 * multiplier * 0.0072,
        net_accumulation_usd: 610_000_000 * multiplier * 0.0072,
        exchanges: [
            { name: 'Binance',  inflow: 330_000_000*multiplier, outflow: 120_000_000*multiplier, net_flow: 210_000_000*multiplier, inflow_usd: 330e6*multiplier*0.0072, outflow_usd: 120e6*multiplier*0.0072, net_flow_usd: 210e6*multiplier*0.0072 },
            { name: 'OKX',      inflow: 160_000_000*multiplier, outflow:  40_000_000*multiplier, net_flow: 120_000_000*multiplier, inflow_usd: 160e6*multiplier*0.0072, outflow_usd:  40e6*multiplier*0.0072, net_flow_usd: 120e6*multiplier*0.0072 },
            { name: 'Bybit',    inflow: 210_000_000*multiplier, outflow:  55_000_000*multiplier, net_flow: 155_000_000*multiplier, inflow_usd: 210e6*multiplier*0.0072, outflow_usd:  55e6*multiplier*0.0072, net_flow_usd: 155e6*multiplier*0.0072 },
            { name: 'Kraken',   inflow:  95_000_000*multiplier, outflow:  30_000_000*multiplier, net_flow:  65_000_000*multiplier, inflow_usd:  95e6*multiplier*0.0072, outflow_usd:  30e6*multiplier*0.0072, net_flow_usd:  65e6*multiplier*0.0072 },
            { name: 'Coinbase', inflow:  20_000_000*multiplier, outflow:  80_000_000*multiplier, net_flow: -60_000_000*multiplier, inflow_usd:  20e6*multiplier*0.0072, outflow_usd:  80e6*multiplier*0.0072, net_flow_usd: -60e6*multiplier*0.0072 },
            { name: 'Gate.io',  inflow:  50_000_000*multiplier, outflow:  10_000_000*multiplier, net_flow:  40_000_000*multiplier, inflow_usd:  50e6*multiplier*0.0072, outflow_usd:  10e6*multiplier*0.0072, net_flow_usd:  40e6*multiplier*0.0072 },
        ],
        wallets: [
            { exchange: 'Binance', address: '34xp4vRoCGJym3x...', reason: 'Public Proof-of-Reserves', balance: 42000000 },
            { exchange: 'OKX', address: 'bc1qxy2kgdygjrsq...', reason: 'Public Proof-of-Reserves', balance: 15000000 },
            { exchange: 'Unknown', address: 'bc1q_heuristic_...', reason: 'Heuristic: Co-spent with known hot wallet', balance: 2500000 }
        ]
    };
}

// ── Fetch & Render Pipeline ───────────────────────────────────────────────────

async function loadData(range) {
    activeRange = range;

    try {
        const resp = await fetch(`${API_BASE}/flows?range=${range}`, { signal: AbortSignal.timeout(5000) });
        if (!resp.ok) throw new Error('Server error');
        currentData = await resp.json();
        console.log('[App] Live data loaded.');
    } catch (e) {
        console.warn('[App] Server offline — using mock data.', e.message);
        currentData = getMockData(range);
    }

    renderAll(currentData);
}

function renderAll(data) {
    renderKPIs(data);
    renderSankey(data);
    renderBarChart(data);
    renderTable(data);

    const priceEl = document.getElementById('dog-price');
    if (priceEl) priceEl.textContent = `$${data.price_usd.toFixed(6)}`;

    const updEl = document.getElementById('last-updated');
    if (updEl) updEl.textContent = new Date().toLocaleTimeString();
}

// ── KPI Cards ─────────────────────────────────────────────────────────────────

function renderKPIs(data) {
    document.getElementById('kpi-inflow').textContent  = `+${fmt(data.total_inflow)} DOG`;
    document.getElementById('kpi-outflow').textContent = `-${fmt(data.total_outflow)} DOG`;
    const net = data.net_accumulation;
    document.getElementById('kpi-net').textContent = `${net >= 0 ? '+' : ''}${fmt(net)} DOG`;

    document.getElementById('kpi-inflow-usd').textContent  = fmtUSD(data.total_inflow_usd);
    document.getElementById('kpi-outflow-usd').textContent = fmtUSD(data.total_outflow_usd);
    document.getElementById('kpi-net-usd').textContent     = fmtUSD(data.net_accumulation_usd);
}

// ── Sankey Diagram ────────────────────────────────────────────────────────────

function renderSankey(data) {
    const container = document.getElementById('sankey-diagram');
    d3.select('#sankey-diagram').selectAll('*').remove();

    const width  = container.clientWidth;
    const height = container.clientHeight;

    const svg = d3.select('#sankey-diagram').append('svg')
        .attr('width', width)
        .attr('height', height);

    // Build acyclic graph: Retail In → Exchange Hot → [Accumulated | Retail Out]
    const nodes = [{ id: 0, name: 'Retail In', color: '#4b5563' }];
    const links = [];

    let nodeIdx = 1;
    const exchangeNodeMap = {};

    data.exchanges.forEach(ex => {
        const hotId  = nodeIdx++;
        const accId  = nodeIdx++;
        const outId  = 0; // shared "Retail Out" placeholder handled below

        exchangeNodeMap[ex.name] = { hotId, accId };

        nodes.push({ id: hotId, name: ex.name,                   color: EXCHANGE_COLORS[ex.name] || '#6b7280' });
        nodes.push({ id: accId, name: ex.name + ' Accumulated', color: EXCHANGE_COLORS[ex.name] || '#6b7280', isAccum: true });

        if (ex.inflow > 0) {
            links.push({ source: 0, target: hotId, value: ex.inflow });
        }
        if (ex.inflow > 0) {
            links.push({ source: hotId, target: accId, value: Math.max(0, ex.net_flow) });
        }
    });

    // Add shared Retail Out node
    const retailOutId = nodeIdx++;
    nodes.push({ id: retailOutId, name: 'Retail Out', color: '#374151' });

    data.exchanges.forEach(ex => {
        const { hotId } = exchangeNodeMap[ex.name];
        if (ex.outflow > 0) {
            links.push({ source: hotId, target: retailOutId, value: ex.outflow });
        }
    });

    // Filter out zero-value links (can cause layout errors)
    const validLinks = links.filter(l => l.value > 0);

    const sankey = d3.sankey()
        .nodeId(d => d.id)
        .nodeWidth(18)
        .nodePadding(28)
        .extent([[20, 20], [width - 20, height - 20]]);

    let layout;
    try {
        layout = sankey({ nodes: nodes.map(d => ({ ...d })), links: validLinks.map(d => ({ ...d })) });
    } catch (e) {
        console.warn('[Sankey] Layout error:', e);
        return;
    }

    const defs = svg.append('defs');

    // Draw links
    svg.append('g').selectAll('path')
        .data(layout.links)
        .join('path')
        .attr('class', 'sankey-link')
        .attr('d', d3.sankeyLinkHorizontal())
        .attr('stroke', d => d.source.color)
        .attr('stroke-width', d => Math.max(1, d.width))
        .attr('stroke-opacity', 0.18)
        .on('mouseenter', (event, d) => {
            d3.select(event.currentTarget).attr('stroke-opacity', 0.55);
            const usd = fmtUSD(d.value * data.price_usd);
            showTooltip(`${d.source.name} → ${d.target.name}\n${fmt(d.value)} DOG\n${usd}`, event);
        })
        .on('mouseleave', (event) => {
            d3.select(event.currentTarget).attr('stroke-opacity', 0.18);
            hideTooltip();
        });

    // Draw node rects
    const node = svg.append('g').selectAll('g')
        .data(layout.nodes)
        .join('g')
        .attr('class', 'sankey-node')
        .attr('transform', d => `translate(${d.x0},${d.y0})`)
        .on('mouseenter', (event, d) => {
            const usd = fmtUSD((d.value || 0) * data.price_usd);
            showTooltip(`${d.name}\n${fmt(d.value || 0)} DOG\n${usd}`, event);
        })
        .on('mouseleave', hideTooltip);

    node.append('rect')
        .attr('height', d => Math.max(1, d.y1 - d.y0))
        .attr('width', sankey.nodeWidth())
        .attr('fill', d => d.color)
        .attr('rx', 4)
        .attr('opacity', d => d.isAccum ? 1 : 0.85);

    // Glow on accumulated nodes
    node.filter(d => d.isAccum)
        .append('rect')
        .attr('height', d => Math.max(1, d.y1 - d.y0))
        .attr('width', sankey.nodeWidth())
        .attr('fill', d => d.color)
        .attr('rx', 4)
        .attr('filter', 'blur(6px)')
        .attr('opacity', 0.4);

    // Labels
    node.append('text')
        .attr('class', 'sankey-label')
        .attr('x', d => d.x0 < width / 2 ? sankey.nodeWidth() + 8 : -8)
        .attr('y', d => (d.y1 - d.y0) / 2 - 6)
        .attr('text-anchor', d => d.x0 < width / 2 ? 'start' : 'end')
        .attr('dy', '0.35em')
        .text(d => d.name);

    node.append('text')
        .attr('class', 'sankey-amount')
        .attr('x', d => d.x0 < width / 2 ? sankey.nodeWidth() + 8 : -8)
        .attr('y', d => (d.y1 - d.y0) / 2 + 10)
        .attr('text-anchor', d => d.x0 < width / 2 ? 'start' : 'end')
        .attr('dy', '0.35em')
        .text(d => fmt(d.value || 0) + ' DOG');
}

// ── Bar Chart ─────────────────────────────────────────────────────────────────

function renderBarChart(data) {
    d3.select('#bar-chart').selectAll('*').remove();

    const container = document.getElementById('bar-chart');
    const W = container.clientWidth;
    const H = container.clientHeight;
    const margin = { top: 20, right: 20, bottom: 50, left: 80 };
    const w = W - margin.left - margin.right;
    const h = H - margin.top  - margin.bottom;

    const svg = d3.select('#bar-chart').append('svg')
        .attr('width', W).attr('height', H)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    const exchanges = data.exchanges;
    const keys = ['inflow', 'outflow', 'net_flow'];
    const colors = { inflow: '#22d3a1', outflow: '#f43f5e', net_flow: '#f5a623' };
    const labels = { inflow: 'Inflow', outflow: 'Outflow', net_flow: 'Net' };

    const x0 = d3.scaleBand().domain(exchanges.map(d => d.name)).range([0, w]).padding(0.25);
    const x1 = d3.scaleBand().domain(keys).range([0, x0.bandwidth()]).padding(0.08);

    const maxVal = d3.max(exchanges, d => Math.max(d.inflow, d.outflow, Math.abs(d.net_flow)));
    const y = d3.scaleLinear().domain([-(maxVal * 0.3), maxVal * 1.1]).range([h, 0]);

    // Zero line
    svg.append('line')
        .attr('x1', 0).attr('x2', w)
        .attr('y1', y(0)).attr('y2', y(0))
        .attr('stroke', 'rgba(255,255,255,0.1)')
        .attr('stroke-width', 1);

    // Gridlines
    svg.append('g')
        .attr('class', 'grid')
        .call(d3.axisLeft(y).ticks(5).tickSize(-w).tickFormat(''))
        .selectAll('line')
        .attr('stroke', 'rgba(255,255,255,0.04)')
        .attr('stroke-dasharray', '3,4');
    svg.select('.grid .domain').remove();

    // Y axis
    svg.append('g')
        .call(d3.axisLeft(y).ticks(5).tickFormat(d => fmt(d)))
        .selectAll('text')
        .attr('fill', '#4b4f6b')
        .attr('font-family', "'JetBrains Mono', monospace")
        .attr('font-size', 10);
    svg.select('.domain').remove();
    svg.selectAll('.tick line').attr('display', 'none');

    // X axis
    svg.append('g')
        .attr('transform', `translate(0,${h})`)
        .call(d3.axisBottom(x0).tickSize(0))
        .selectAll('text')
        .attr('fill', '#8b8fa8')
        .attr('font-size', 11)
        .attr('font-family', "'Inter', sans-serif")
        .attr('dy', '1.2em');
    svg.selectAll('.domain').remove();

    // Bars
    const xGroup = svg.append('g').selectAll('g')
        .data(exchanges)
        .join('g')
        .attr('transform', d => `translate(${x0(d.name)},0)`);

    xGroup.selectAll('rect')
        .data(d => keys.map(k => ({ key: k, value: d[k], exchange: d.name, data: d })))
        .join('rect')
        .attr('x', d => x1(d.key))
        .attr('y', d => d.value >= 0 ? y(d.value) : y(0))
        .attr('height', d => Math.abs(y(d.value) - y(0)))
        .attr('width', x1.bandwidth())
        .attr('fill', d => colors[d.key])
        .attr('rx', 3)
        .attr('opacity', 0.85)
        .on('mouseenter', (event, d) => {
            d3.select(event.currentTarget).attr('opacity', 1);
            const usd = fmtUSD(d.data[d.key + '_usd'] || d.value * data.price_usd);
            showTooltip(`${d.exchange} · ${labels[d.key]}\n${fmt(d.value)} DOG\n${usd}`, event);
        })
        .on('mouseleave', (event) => {
            d3.select(event.currentTarget).attr('opacity', 0.85);
            hideTooltip();
        });

    // Legend
    const legend = svg.append('g').attr('transform', `translate(${w - 180}, -15)`);
    Object.entries(labels).forEach(([key, label], i) => {
        const g = legend.append('g').attr('transform', `translate(${i * 65}, 0)`);
        g.append('rect').attr('width', 10).attr('height', 10).attr('fill', colors[key]).attr('rx', 2);
        g.append('text').attr('x', 14).attr('y', 9).text(label)
            .attr('fill', '#8b8fa8').attr('font-size', 10).attr('font-family', "'Inter', sans-serif");
    });
}

// ── Exchange Table ─────────────────────────────────────────────────────────────

function renderTable(data) {
    const tbody = document.getElementById('table-body');
    if (!data.exchanges || data.exchanges.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">No exchange data found.</td></tr>';
        return;
    }

    // Sort by net_flow descending
    const sorted = [...data.exchanges].sort((a, b) => b.net_flow - a.net_flow);

    tbody.innerHTML = sorted.map(ex => {
        const color = EXCHANGE_COLORS[ex.name] || '#6b7280';
        return `
        <tr>
            <td>
                <span class="exchange-dot" style="background:${color}; box-shadow: 0 0 6px ${color}60;"></span>
                ${ex.name}
            </td>
            <td style="color: #22d3a1;">+${fmt(ex.inflow)}</td>
            <td style="color: #22d3a1;">${fmtUSD(ex.inflow_usd)}</td>
            <td style="color: #f43f5e;">-${fmt(ex.outflow)}</td>
            <td style="color: #f43f5e;">${fmtUSD(ex.outflow_usd)}</td>
            <td style="color: ${ex.net_flow >= 0 ? '#f5a623' : '#f43f5e'}; font-weight:700;">
                ${ex.net_flow >= 0 ? '+' : ''}${fmt(ex.net_flow)}
            </td>
            <td>${signal(ex.net_flow)}</td>
        </tr>`;
    }).join('');
}

// ── Wallet Registry ────────────────────────────────────────────────────────────

async function loadWallets() {
    let wallets = [];
    try {
        const resp = await fetch(`${API_BASE}/wallets`, { signal: AbortSignal.timeout(5000) });
        if (resp.ok) wallets = await resp.json();
    } catch (e) {
        // use mock if offline
        wallets = currentData ? currentData.wallets : [];
    }

    const tbody = document.getElementById('wallet-body');
    if (!wallets || wallets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading-cell">No wallets found or DB not initialized.</td></tr>';
        return;
    }

    tbody.innerHTML = wallets.map(w => {
        const color = EXCHANGE_COLORS[w.exchange] || '#6b7280';
        return `
        <tr>
            <td>
                <span class="exchange-dot" style="background:${color}; box-shadow: 0 0 6px ${color}60;"></span>
                ${w.exchange}
            </td>
            <td style="font-family: var(--font-mono); color: var(--text-2);">${w.address}</td>
            <td style="color: var(--gold);">${fmt(w.balance)} DOG</td>
            <td style="color: var(--text-2); font-size: 0.8rem;">${w.reason || 'Manual entry'}</td>
        </tr>`;
    }).join('');
}

// ── Range Tabs ────────────────────────────────────────────────────────────────

document.getElementById('range-tabs').addEventListener('click', e => {
    const tab = e.target.closest('.tab');
    if (!tab) return;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    loadData(tab.dataset.range);
});

// ── Refresh Button ─────────────────────────────────────────────────────────────

async function refreshData() {
    const btn = document.getElementById('refresh-btn');
    btn.classList.add('spinning');
    try {
        await fetch(`${API_BASE}/refresh`, { signal: AbortSignal.timeout(15000) });
    } catch (e) { /* offline is fine */ }
    await loadData(activeRange);
    await loadWallets();
    btn.classList.remove('spinning');
}

// ── Resize Handler ────────────────────────────────────────────────────────────

let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (currentData) renderAll(currentData); }, 200);
});

// ── Init ──────────────────────────────────────────────────────────────────────

loadData('24h').then(loadWallets);
