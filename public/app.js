// Lightless Syncshell Group Examiner - Frontend Logic
let appData = {
    groups: [],
    members: {},
    summary: {}
};

let currentFilter = 'all';
let currentSearch = '';
let activeGroup = null;
let activeTab = 'tab-overlaps';
let memberSearchQuery = '';
let currentSort = 'leave-impact';
let currentSortDirection = 'asc';
let currentLayout = 'grid';
let currentCharacterUid = null;
let onlineOnly = false;
let networkInstance = null;
let latestDataRequest = 0;

// DOM Elements
const els = {
    groupsContainer: document.getElementById('groups-container'),
    searchBar: document.getElementById('group-search'),
    filterBtns: document.querySelectorAll('.filter-buttons [data-filter]'),
    loadingSpinner: document.getElementById('loading-spinner'),
    refreshBtn: document.getElementById('refresh-btn'),
    dataStatus: document.getElementById('data-status'),
    
    // Summary Widgets
    metricGroups: document.getElementById('metric-groups'),
    metricPlayers: document.getElementById('metric-players'),
    metricPlayersLabel: document.getElementById('metric-players-label'),
    metricRedundancy: document.getElementById('metric-redundancy'),
    metricRedundancyLabel: document.getElementById('metric-redundancy-label'),
    metricSafeLeave: document.getElementById('metric-safe-leave'),
    
    // Drawer Elements
    detailDrawer: document.getElementById('detail-drawer'),
    drawerBackdrop: document.getElementById('drawer-backdrop'),
    drawerClose: document.getElementById('drawer-close'),
    drawerGroupName: document.getElementById('drawer-group-name'),
    drawerGroupGid: document.getElementById('drawer-group-gid'),
    drawerMetricTotal: document.getElementById('drawer-metric-total'),
    drawerMetricTotalLabel: document.getElementById('drawer-metric-total-label'),
    drawerMetricUnique: document.getElementById('drawer-metric-unique'),
    drawerMetricUniqueLabel: document.getElementById('drawer-metric-unique-label'),
    drawerMetricRedundant: document.getElementById('drawer-metric-redundant'),
    drawerMetricRedundantLabel: document.getElementById('drawer-metric-redundant-label'),
    drawerExplanation: document.getElementById('drawer-explanation'),
    drawerOnlineSummary: document.getElementById('drawer-online-summary'),
    
    // Tabs & Lists
    tabButtons: document.querySelectorAll('.tab-btn'),
    tabPanes: document.querySelectorAll('.tab-pane'),
    overlapsList: document.getElementById('overlaps-list'),
    uniquesList: document.getElementById('uniques-list'),
    allMembersList: document.getElementById('all-members-list'),
    memberSearch: document.getElementById('member-search'),
    tabCountUniques: document.getElementById('tab-count-uniques'),
    tabCountAll: document.getElementById('tab-count-all'),
    tabUniquesLabel: document.getElementById('tab-uniques-label'),
    tabAllLabel: document.getElementById('tab-all-label'),

    // Data Source Banner
    dataSourceBanner: document.getElementById('data-source-banner'),
    bannerIcon: document.getElementById('banner-icon'),
    bannerTitle: document.getElementById('banner-title'),
    bannerDescription: document.getElementById('banner-description'),

    // Sort & Layout View Controls
    sortSelect: document.getElementById('group-sort'),
    sortDirectionBtns: document.querySelectorAll('[data-sort-direction]'),
    playerScope: document.getElementById('player-scope'),
    viewGridBtn: document.getElementById('view-grid-btn'),
    viewListBtn: document.getElementById('view-list-btn'),
    viewNetworkBtn: document.getElementById('view-network-btn'),
    networkContainer: document.getElementById('network-container'),

    // Character Switcher
    characterSelect: document.getElementById('character-select')
};

// Fetch Data from Python Backend
async function fetchData(uid = null) {
    const request = ++latestDataRequest;
    showLoading(true);
    els.dataStatus.className = 'status-indicator status-loading';
    els.dataStatus.textContent = 'Syncing...';
    
    try {
        const url = uid ? `/api/data?uid=${encodeURIComponent(uid)}` : '/api/data';
        const response = await fetch(url);
        if (!response.ok) throw new Error('API server returned error status');
        
        const data = await response.json();
        if (request !== latestDataRequest) return;
        appData = data;
        
        // Update status UI
        els.dataStatus.className = 'status-indicator status-online';
        els.dataStatus.textContent = 'Connected';
        
        // Update stats, character lists, and diagnostics banner
        updateCharacterSelector();
        const onlineAvailable = Boolean(appData.summary.online);
        els.playerScope.querySelector('option[value="online"]').disabled = !onlineAvailable;
        if (!onlineAvailable) {
            onlineOnly = false;
            els.playerScope.value = 'all';
        }
        updateDiagnosticsBanner();
        renderAnalysis();
    } catch (err) {
        if (request !== latestDataRequest) return;
        console.error('Error fetching data:', err);
        els.dataStatus.className = 'status-indicator';
        els.dataStatus.textContent = 'Server Offline';
        alert('Could not connect to local server. Please ensure the Python server is running and try again.');
    } finally {
        if (request === latestDataRequest) showLoading(false);
    }
}

function renderAnalysis() {
    updateSummary();
    renderGroups();

    if (activeGroup) {
        const refreshedGroup = appData.groups.find(g => g.gid === activeGroup.gid);
        if (refreshedGroup) {
            openDrawer(refreshedGroup);
        } else {
            closeDrawer();
        }
    }
}

function groupStats(group) {
    return onlineOnly ? group.online : group;
}

function formatRedundancy(value) {
    return value == null ? '—' : `${value}%`;
}

function onlineCount(group) {
    const unknown = group.online.unknown_members_count;
    const suffix = unknown ? ` · ${unknown} unknown` : '';
    return `${group.online.total_members} / ${group.total_members}${suffix}`;
}

function showLoading(show) {
    if (show) {
        els.loadingSpinner.classList.remove('hidden');
        els.groupsContainer.classList.add('hidden');
    } else {
        els.loadingSpinner.classList.add('hidden');
        els.groupsContainer.classList.toggle('hidden', currentLayout === 'network');
    }
}

// Update Character Selector Options
function updateCharacterSelector() {
    if (!appData.characters) return;
    
    // Clear and rebuild options
    els.characterSelect.innerHTML = '';
    
    appData.characters.forEach(char => {
        const option = document.createElement('option');
        option.value = char.uid;
        
        let label = `${char.name} (${char.uid})`;
        if (char.is_active) {
            label += ' (Active)';
        }
        if (!char.has_report) {
            label += ' [No Diagnostics Report]';
        }
        
        option.textContent = label;
        option.selected = char.is_current;
        els.characterSelect.appendChild(option);
    });
    
    currentCharacterUid = appData.current_character;
}

// Update Dashboard Statistics
function updateSummary() {
    const summary = onlineOnly ? appData.summary.online : appData.summary;
    els.metricGroups.textContent = appData.summary.total_groups;
    els.metricPlayers.textContent = summary.total_unique_players;
    els.metricPlayersLabel.textContent = onlineOnly ? 'Distinct Online Players' : 'Unique Sync Players';
    els.metricRedundancy.textContent = formatRedundancy(summary.average_redundancy_pct);
    els.metricRedundancyLabel.textContent = onlineOnly ? 'Average Online Redundancy' : 'Average Redundancy';
    els.metricSafeLeave.textContent = appData.summary.safe_to_leave_gids ? appData.summary.safe_to_leave_gids.length : '0';
}

// Update Diagnostic Data Source Notice
function updateDiagnosticsBanner() {
    if (!appData.data_source) {
        els.dataSourceBanner.classList.add('hidden');
        return;
    }
    
    els.dataSourceBanner.classList.remove('hidden', 'banner-success', 'banner-warning');
    
    if (appData.data_source === 'diagnostics_report') {
        els.dataSourceBanner.classList.add('banner-success');
        els.bannerIcon.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
        `;
        els.bannerTitle.textContent = 'Complete Syncshell Analysis Active';
        const presence = appData.summary.online;
        let onlineNotice = presence
            ? 'Online counts reflect this snapshot. Generate a new report and click Refresh Logs to update them.'
            : 'This report has no online status for syncshell members.';
        if (presence?.unknown_players_count) {
            onlineNotice += ` Online status is unknown for ${presence.unknown_players_count} players.`;
        }
        els.bannerDescription.innerHTML = `Diagnostics snapshot <strong>${escapeHtml(appData.diagnostics_timestamp)}</strong> (${escapeHtml(appData.diagnostics_file)}). ${onlineNotice}`;
    } else {
        els.dataSourceBanner.classList.add('banner-warning');
        els.bannerIcon.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
        `;
        els.bannerTitle.textContent = 'Incremental Log Sync Mode (Incomplete Data)';
        els.bannerDescription.innerHTML = `Trace logs provide incomplete memberships and no online status. In FFXIV, open <strong>LightlessSync settings &gt; Diagnostics</strong> and click <strong>Generate Diagnostics Report</strong>, then click <strong>Refresh Logs</strong> here.`;
    }
}

// Render Groups List Grid
function renderGroups() {
    els.groupsContainer.innerHTML = '';
    
    if (currentLayout === 'network') {
        els.groupsContainer.classList.add('hidden');
        els.networkContainer.classList.remove('hidden');
        renderNetworkGraph();
        return;
    } else {
        els.networkContainer.classList.add('hidden');
        els.groupsContainer.classList.remove('hidden');
    }
    
    // Set layout class list/grid
    els.groupsContainer.className = currentLayout === 'grid' ? 'groups-grid' : 'groups-grid list-view';
    
    const filtered = appData.groups.filter(group => {
        // Search Filter
        const nameMatch = group.name.toLowerCase().includes(currentSearch.toLowerCase());
        const gidMatch = group.gid.toLowerCase().includes(currentSearch.toLowerCase());
        const matchSearch = nameMatch || gidMatch;
        
        // Impact Filter
        const matchFilter = currentFilter === 'all' || group.leave_impact === currentFilter;
        
        return matchSearch && matchFilter;
    });

    // Apply the selected sort key and direction
    filtered.sort((a, b) => {
        if (currentSort === 'name-asc') {
            const direction = currentSortDirection === 'asc' ? 1 : -1;
            return a.name.localeCompare(b.name) * direction;
        }

        let aValue;
        let bValue;
        if (currentSort === 'leave-impact') {
            aValue = a.unique_members_count;
            bValue = b.unique_members_count;
        } else if (currentSort === 'redundancy') {
            aValue = groupStats(a).redundancy_pct;
            bValue = groupStats(b).redundancy_pct;
        } else if (currentSort === 'members') {
            aValue = groupStats(a).total_members;
            bValue = groupStats(b).total_members;
        } else if (currentSort === 'unique-online') {
            aValue = a.online?.unique_members_count ?? 0;
            bValue = b.online?.unique_members_count ?? 0;
        } else {
            return 0;
        }

        if (aValue == null && bValue == null) return 0;
        if (aValue == null) return 1;
        if (bValue == null) return -1;
        const direction = currentSortDirection === 'asc' ? 1 : -1;
        return (aValue - bValue) * direction;
    });
    
    if (filtered.length === 0) {
        els.groupsContainer.innerHTML = `
            <div class="no-data-msg" style="grid-column: 1 / -1; padding: 4rem;">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:1rem; opacity:0.5;"><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
                <p>No syncshells match your search or filter criteria.</p>
            </div>
        `;
        return;
    }
    
    filtered.forEach(group => {
        const stats = groupStats(group);
        const card = document.createElement('div');
        card.className = `group-card impact-${group.leave_impact.toLowerCase()}`;
        card.id = `group-card-${group.gid}`;
        
        // Visual indicator of impact color
        let impactBadgeClass = `badge-impact-${group.leave_impact.toLowerCase()}`;
        
        // Redundancy fill % representation
        const barWidth = stats.redundancy_pct ?? 0;
        
        card.innerHTML = `
            <div class="card-header">
                <div class="card-title">
                    <h3>${escapeHtml(group.name)}</h3>
                    <span class="gid">${group.gid}</span>
                </div>
                <span class="badge ${impactBadgeClass}" title="Leave impact across all players">${group.leave_impact} Impact</span>
            </div>
            <div class="card-body">
                <div class="stat-row">
                    <span class="label">${group.online ? 'Online / total players' : 'Synced Players'}</span>
                    <span class="val">${group.online ? onlineCount(group) : group.total_members}</span>
                </div>
                <div class="stat-row">
                    <span class="label">${onlineOnly ? 'Shared online players' : 'Shared with other groups'}</span>
                    <span class="val">${stats.shared_members_count}</span>
                </div>
                <div class="stat-row">
                    <span class="label">${group.online ? 'Unique online / total' : 'Unique to this group'}</span>
                    <span class="val text-warning">${group.online ? `${group.online.unique_members_count} / ${group.unique_members_count}` : group.unique_members_count}</span>
                </div>
                
                <div class="redundancy-progress-container">
                    <div class="progress-header">
                        <span>${onlineOnly ? 'Online Redundancy' : 'Redundancy Ratio'}</span>
                        <span>${formatRedundancy(stats.redundancy_pct)}</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${barWidth}%"></div>
                    </div>
                </div>
            </div>
            <div class="card-footer">
                <span>Click to analyze overlap</span>
                <span class="interactive-hint">
                    Analyze
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
                </span>
            </div>
        `;
        
        card.addEventListener('click', () => openDrawer(group));
        els.groupsContainer.appendChild(card);
    });
}

// Open Detail Drawer
function openDrawer(group) {
    activeGroup = group;
    const stats = groupStats(group);
    els.drawerGroupName.textContent = group.name;
    els.drawerGroupGid.textContent = group.gid;
    
    els.drawerMetricTotal.textContent = stats.total_members;
    els.drawerMetricTotalLabel.textContent = onlineOnly ? 'Online Players' : 'Total Members';
    els.drawerMetricUnique.textContent = stats.unique_members_count;
    els.drawerMetricUniqueLabel.textContent = onlineOnly ? 'Unique Online Players' : 'Unique Members';
    els.drawerMetricRedundant.textContent = formatRedundancy(stats.redundancy_pct);
    els.drawerMetricRedundantLabel.textContent = onlineOnly ? 'Online Redundancy' : 'Redundancy';
    els.drawerOnlineSummary.hidden = !group.online;
    if (group.online) {
        els.drawerOnlineSummary.textContent = `Online / total players: ${onlineCount(group)}. Unique online players: ${group.online.unique_members_count}.`;
    }
    els.drawerExplanation.textContent = `Leave impact across all players: ${group.leave_impact}. Leaving this group would remove syncshell coverage for ${group.unique_members_count} unique players in the analyzed data.`;
    
    // Tab badge counters
    els.tabUniquesLabel.textContent = onlineOnly ? 'Unique online players' : 'Unique players';
    els.tabAllLabel.textContent = onlineOnly ? 'Online players' : 'All players';
    els.tabCountUniques.textContent = stats.unique_members_count;
    els.tabCountAll.textContent = stats.total_members;
    
    // Reset member search within drawer
    els.memberSearch.value = '';
    memberSearchQuery = '';
    
    // Render the tabs list data
    renderDrawerTabs();
    
    // Show drawer
    els.detailDrawer.classList.add('visible');
    els.drawerBackdrop.classList.add('visible');
}

function closeDrawer() {
    activeGroup = null;
    els.detailDrawer.classList.remove('visible');
    els.drawerBackdrop.classList.remove('visible');
}

// Render Lists inside the Drawer depending on the group and active search
function renderDrawerTabs() {
    if (!activeGroup) return;
    const stats = groupStats(activeGroup);
    
    // 1. Render Overlaps Tab
    els.overlapsList.innerHTML = '';
    const sortedOverlaps = Object.entries(stats.overlaps)
        .map(([gid, count]) => {
            const targetGroup = appData.groups.find(g => g.gid === gid);
            return {
                gid,
                count,
                name: targetGroup ? targetGroup.name : gid
            };
        })
        .sort((a, b) => b.count - a.count);
        
    if (sortedOverlaps.length === 0) {
        els.overlapsList.innerHTML = `<div class="no-data-msg">No ${onlineOnly ? 'online ' : ''}players shared with other syncshells.</div>`;
    } else {
        sortedOverlaps.forEach(o => {
            const li = document.createElement('li');
            li.style.cursor = 'pointer';
            li.innerHTML = `
                <div>
                    <span class="name-bold">${escapeHtml(o.name)}</span>
                    <span class="uid-sub">${o.gid}</span>
                </div>
                <span class="overlap-count">${o.count} shared ${onlineOnly ? 'online ' : ''}players</span>
            `;
            // Add click event to pivot to that group details
            li.addEventListener('click', () => {
                const groupObj = appData.groups.find(g => g.gid === o.gid);
                if (groupObj) {
                    openDrawer(groupObj);
                    if (currentLayout === 'network' && networkInstance) {
                        networkInstance.selectNodes([groupObj.gid]);
                        networkInstance.focus(groupObj.gid, {
                            scale: 0.9,
                            animation: {
                                duration: 400,
                                easingFunction: 'easeInOutQuad'
                            }
                        });
                    }
                }
            });
            els.overlapsList.appendChild(li);
        });
    }

    // 2. Render Uniques Tab
    els.uniquesList.innerHTML = '';
    if (stats.unique_members.length === 0) {
        els.uniquesList.innerHTML = `<div class="no-data-msg">No unique ${onlineOnly ? 'online ' : ''}players in the analyzed data.</div>`;
    } else {
        stats.unique_members.forEach(uid => {
            const name = appData.members[uid] || uid;
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="name-bold">${escapeHtml(name)}</span>
                <span class="uid-sub">${uid}</span>
            `;
            els.uniquesList.appendChild(li);
        });
    }

    // 3. Render All Players Tab (with inline search filter)
    renderAllPlayersTab();
}

function renderAllPlayersTab() {
    els.allMembersList.innerHTML = '';
    const stats = groupStats(activeGroup);
    
    // Sort all members by name
    const sortedMembers = [...stats.shared_members, ...stats.unique_members]
        .map(uid => ({
            uid,
            name: appData.members[uid] || uid,
            isUnique: stats.unique_members.includes(uid)
        }))
        .sort((a, b) => a.name.localeCompare(b.name));
        
    // Filter by memberSearchQuery
    const filteredMembers = sortedMembers.filter(m => 
        m.name.toLowerCase().includes(memberSearchQuery.toLowerCase()) || 
        m.uid.toLowerCase().includes(memberSearchQuery.toLowerCase())
    );
    
    if (filteredMembers.length === 0) {
        els.allMembersList.innerHTML = `<div class="no-data-msg">No players matched your search.</div>`;
        return;
    }
    
    filteredMembers.forEach(m => {
        const li = document.createElement('li');
        
        let subText = m.isUnique 
            ? `<span class="badge badge-impact-medium" style="float: right; margin-top:-5px; font-size:0.65rem;">Unique</span>` 
            : `<span class="badge badge-impact-none" style="float: right; margin-top:-5px; font-size:0.65rem;">Shared</span>`;
            
        li.innerHTML = `
            ${subText}
            <span class="name-bold">${escapeHtml(m.name)}</span>
            <span class="uid-sub">${m.uid}</span>
        `;
        els.allMembersList.appendChild(li);
    });
}

// Helpers
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}

// Event Listeners
els.searchBar.addEventListener('input', (e) => {
    currentSearch = e.target.value;
    renderGroups();
});

els.filterBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
        els.filterBtns.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentFilter = e.target.getAttribute('data-filter');
        renderGroups();
    });
});

els.sortSelect.addEventListener('change', (e) => {
    currentSort = e.target.value;
    updateSortDirectionButtons();
    renderGroups();
});

els.sortDirectionBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        currentSortDirection = btn.dataset.sortDirection;
        updateSortDirectionButtons();
        renderGroups();
    });
});

function updateSortDirectionButtons() {
    const isNameSort = els.sortSelect.value === 'name-asc';
    els.sortDirectionBtns.forEach(btn => {
        btn.textContent = isNameSort
            ? (btn.dataset.sortDirection === 'asc' ? 'A to Z' : 'Z to A')
            : (btn.dataset.sortDirection === 'asc' ? 'Low to High' : 'High to Low');
        btn.classList.toggle('active', btn.dataset.sortDirection === currentSortDirection);
    });
}

updateSortDirectionButtons();

els.playerScope.addEventListener('change', (e) => {
    onlineOnly = e.target.value === 'online';
    renderAnalysis();
});

els.characterSelect.addEventListener('change', (e) => {
    currentCharacterUid = e.target.value;
    fetchData(currentCharacterUid);
});

els.viewGridBtn.addEventListener('click', () => {
    currentLayout = 'grid';
    els.viewGridBtn.classList.add('active');
    els.viewListBtn.classList.remove('active');
    els.viewNetworkBtn.classList.remove('active');
    renderGroups();
});

els.viewListBtn.addEventListener('click', () => {
    currentLayout = 'list';
    els.viewListBtn.classList.add('active');
    els.viewGridBtn.classList.remove('active');
    els.viewNetworkBtn.classList.remove('active');
    renderGroups();
});

els.viewNetworkBtn.addEventListener('click', () => {
    currentLayout = 'network';
    els.viewNetworkBtn.classList.add('active');
    els.viewGridBtn.classList.remove('active');
    els.viewListBtn.classList.remove('active');
    renderGroups();
});

els.refreshBtn.addEventListener('click', () => {
    fetchData(currentCharacterUid);
});

els.drawerClose.addEventListener('click', closeDrawer);
els.drawerBackdrop.addEventListener('click', closeDrawer);

// Tab switching logic inside drawer
els.tabButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
        els.tabButtons.forEach(b => b.classList.remove('active'));
        els.tabPanes.forEach(p => p.classList.remove('active'));
        
        e.currentTarget.classList.add('active');
        const tabId = e.currentTarget.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
        activeTab = tabId;
    });
});

// Member search logic inside drawer
els.memberSearch.addEventListener('input', (e) => {
    memberSearchQuery = e.target.value;
    renderAllPlayersTab();
});

// ESC key to close drawer
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && activeGroup) {
        closeDrawer();
    }
});

// Initial Load
fetchData();

// Render Network Graph Visualization using Vis-Network
function renderNetworkGraph() {
    if (networkInstance) {
        networkInstance.destroy();
        networkInstance = null;
    }

    const container = document.getElementById('network-graph');
    if (!container || appData.groups.length === 0) return;

    // Build Nodes
    const nodes = [];
    appData.groups.forEach(group => {
        const stats = groupStats(group);
        // Map Leave Impact to Color
        let borderColor = '#3b82f6'; // Low impact (default)
        if (group.leave_impact === 'None') borderColor = '#10b981';
        else if (group.leave_impact === 'Medium') borderColor = '#f59e0b';
        else if (group.leave_impact === 'High') borderColor = '#ef4444';

        // Size calculation based on player counts
        // Standardize sizes between 15 and 45 for clear legibility
        const size = Math.max(15, Math.min(45, 10 + Math.sqrt(stats.total_members) * 2.5));

        nodes.push({
            id: group.gid,
            label: group.name,
            shape: 'dot',
            size: size,
            borderWidth: 3,
            borderWidthSelected: 5,
            color: {
                background: '#101624', // --bg-input
                border: borderColor,
                highlight: {
                    background: '#1e2942', // --bg-card-hover
                    border: '#6366f1' // --accent-indigo
                },
                hover: {
                    background: '#1e2942',
                    border: borderColor
                }
            },
            font: {
                color: '#e2e8f0', // --color-text-main
                face: 'Outfit',
                size: 13,
                vadjust: 0
            },
            title: (() => {
                const el = document.createElement('div');
                const presence = group.online
                    ? `Online / total players: ${onlineCount(group)}<br>Unique online players: ${group.online.unique_members_count}<br>`
                    : `Synced players: ${group.total_members}<br>`;
                el.innerHTML = `<strong>${escapeHtml(group.name)}</strong><br>` +
                               `<span style="font-family: monospace; font-size: 0.8rem; color: #94a3b8;">${group.gid}</span><br>` +
                               `<hr style="border: 0; border-top: 1px solid #24324f; margin: 4px 0;">` +
                               presence +
                               `Unique players (all): ${group.unique_members_count}<br>` +
                               `${onlineOnly ? 'Online redundancy' : 'Redundancy'}: ${formatRedundancy(stats.redundancy_pct)}<br>` +
                               `Leave impact (all players): <strong style="color: ${borderColor}">${group.leave_impact}</strong>`;
                return el;
            })()
        });
    });

    // Build Edges
    const edges = [];
    const addedEdges = new Set();

    appData.groups.forEach(group => {
        Object.entries(groupStats(group).overlaps).forEach(([otherGid, sharedCount]) => {
            if (sharedCount === 0) return;

            // Normalize edge identification to avoid bidirectional duplicates (e.g. A->B and B->A)
            const edgeKey = group.gid < otherGid ? `${group.gid}_${otherGid}` : `${otherGid}_${group.gid}`;
            if (addedEdges.has(edgeKey)) return;
            addedEdges.add(edgeKey);

            const targetGroup = appData.groups.find(g => g.gid === otherGid);
            const targetName = targetGroup ? targetGroup.name : otherGid;

            // Scale edge width by logarithmic thickness mapping (range 1.5px to 8px)
            const width = Math.max(1.5, Math.min(8, Math.log2(sharedCount) * 1.5));

            // Dynamic spring settings based on overlap count (higher overlap = shorter and stronger springs)
            const restingLength = Math.max(60, 200 - (sharedCount * 5));
            const stiffness = Math.min(0.25, 0.05 + (sharedCount * 0.008));

            edges.push({
                from: group.gid,
                to: otherGid,
                value: sharedCount,
                width: width,
                length: restingLength,
                springConstant: stiffness,
                color: {
                    color: 'rgba(99, 102, 241, 0.25)', // --accent-indigo with opacity
                    highlight: 'rgba(6, 182, 212, 0.8)', // --accent-cyan
                    hover: 'rgba(6, 182, 212, 0.4)'
                },
                title: (() => {
                    const el = document.createElement('div');
                    el.innerHTML = `<strong>${sharedCount} shared ${onlineOnly ? 'online ' : ''}players</strong><br>` +
                                   `<span style="font-size: 0.8rem; color: #94a3b8;">between ${escapeHtml(group.name)} and ${escapeHtml(targetName)}</span>`;
                    return el;
                })()
            });
        });
    });

    const data = {
        nodes: new vis.DataSet(nodes),
        edges: new vis.DataSet(edges)
    };

    const options = {
        physics: {
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {
                gravitationalConstant: -180,
                centralGravity: 0.015,
                springLength: 160,
                springConstant: 0.06,
                damping: 0.4,
                avoidOverlap: 0.8
            },
            stabilization: {
                iterations: 150,
                updateInterval: 25
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 150,
            dragNodes: true,
            dragView: true,
            zoomView: true
        }
    };

    networkInstance = new vis.Network(container, data, options);

    // Set button UI to default (active layout) at start
    updatePhysicsButtonUI(true);

    // Disable physics once stabilized to prevent slow endless spinning/drifting
    networkInstance.on('stabilized', function () {
        networkInstance.setOptions({ physics: { enabled: false } });
        updatePhysicsButtonUI(false);
    });

    // Re-enable physics when drag starts to allow interactive movement
    networkInstance.on('dragStart', function () {
        networkInstance.setOptions({ physics: { enabled: true } });
        updatePhysicsButtonUI(true);
    });

    // Node click selection interaction -> open detail panel drawer
    networkInstance.on('selectNode', function (params) {
        if (params.nodes.length > 0) {
            const clickedGid = params.nodes[0];
            const group = appData.groups.find(g => g.gid === clickedGid);
            if (group) {
                openDrawer(group);
            }
        }
    });
}

// Update Physics Freeze Button styling and text
function updatePhysicsButtonUI(enabled) {
    const btn = document.getElementById('toggle-physics-btn');
    if (!btn) return;
    if (enabled) {
        btn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="9" y1="9" x2="9" y2="15"></line>
                <line x1="15" y1="9" x2="15" y2="15"></line>
            </svg>
            Freeze Layout
        `;
        btn.classList.remove('physics-frozen');
    } else {
        btn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
            Unfreeze Layout
        `;
        btn.classList.add('physics-frozen');
    }
}

// Global listener for Freeze layout button
const togglePhysicsBtn = document.getElementById('toggle-physics-btn');
if (togglePhysicsBtn) {
    togglePhysicsBtn.addEventListener('click', () => {
        if (!networkInstance) return;
        const isPhysicsEnabled = networkInstance.physics.options.enabled !== false;
        const targetState = !isPhysicsEnabled;
        networkInstance.setOptions({ physics: { enabled: targetState } });
        updatePhysicsButtonUI(targetState);
    });
}
