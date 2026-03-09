const CENTRAL_API_URL = "http://localhost:8000"; 
let rootPaths = []; 
let expanded = new Set();
let loaded = new Set();
let analysisResults = []; 
let currentMoveProposals = [];
let customFolders = [];

// 1. 트리 관리 (기존과 동일)
async function addFiles() {
    try {
        const res = await (await fetch(`${CENTRAL_API_URL}/dialog/file`)).json();
        if (res.paths?.length) { res.paths.forEach(p => updateRootPaths(p, false)); renderTree(); }
    } catch(e) { alert("서버 연결 실패."); }
}
async function addFolder() {
    try {
        const res = await (await fetch(`${CENTRAL_API_URL}/dialog/folder`)).json();
        if (res.paths?.length) { res.paths.forEach(p => updateRootPaths(p, true)); renderTree(); }
    } catch(e) { alert("서버 연결 실패."); }
}
function updateRootPaths(p, isDir) {
    const normalizedP = p.replace(/\\$/, "");
    if (rootPaths.some(r => r.path === normalizedP)) return;
    rootPaths.push({ path: normalizedP, isDir: isDir });
    document.getElementById('btn-next-step').disabled = false;
}
function renderTree() {
    const container = document.getElementById('file-tree');
    container.innerHTML = '';
    rootPaths.forEach(root => {
        const lastSlash = root.path.lastIndexOf('\\');
        const parentPath = root.path.substring(0, lastSlash);
        const rootName = root.path.substring(lastSlash + 1);
        const group = document.createElement('div');
        group.className = 'tree-group-box';
        group.innerHTML = `<span class="parent-path">${parentPath}\\</span>`;
        group.appendChild(buildNode(rootName, root.path, root.isDir, true));
        container.appendChild(group);
    });
    document.getElementById('tree-divider').style.display = 'block';
    document.getElementById('tree-scroll-area').style.display = 'block';
}
function buildNode(name, path, isDir, isRoot = false) {
    const node = document.createElement('div');
    const row = document.createElement('div');
    row.className = 'tree-row';
    const isExpanded = expanded.has(path);
    row.innerHTML = `<span class="toggle">${isDir ? (isExpanded ? '▼' : '▶') : ''}</span><span class="tree-icon">${isDir ? '📁' : '📄'}</span><span class="tree-name">${name}</span>`;
    node.appendChild(row);
    if (isDir) {
        const wrap = document.createElement('div');
        wrap.className = `tree-children-wrapper ${isExpanded ? '' : 'collapsed'}`;
        const inner = document.createElement('div');
        inner.className = `tree-children-inner ${isRoot ? 'nested-scroll' : ''}`;
        wrap.appendChild(inner);
        node.appendChild(wrap);
        row.onclick = async () => {
            if (expanded.has(path)) {
                expanded.delete(path); wrap.classList.add('collapsed'); row.querySelector('.toggle').innerText = '▶';
            } else {
                expanded.add(path); wrap.classList.remove('collapsed'); row.querySelector('.toggle').innerText = '▼';
                if (!loaded.has(path)) await loadChildren(path, inner);
            }
        };
    }
    return node;
}
async function loadChildren(p, c) {
    try {
        const data = await (await fetch(`${CENTRAL_API_URL}/list/directory?path=${encodeURIComponent(p)}`)).json();
        c.innerHTML = ''; loaded.add(p);
        if (data.items) data.items.forEach(i => c.appendChild(buildNode(i.name, i.path, i.is_dir, false)));
    } catch(e) {}
}

// 2. 파일 분석 (Step 2) - 파일별 진행도 구현
async function nextStep() {
    document.getElementById('container').className = 'active-state';
    const pdfQueue = document.getElementById('pdf-queue'), unclassified = document.getElementById('unclassified-list');
    pdfQueue.innerHTML = ''; unclassified.innerHTML = '';
    analysisResults = [];
    const allFiles = [];
    for (let r of rootPaths) await collect(r.path, allFiles);
    
    if (allFiles.length === 0) {
        pdfQueue.innerHTML = '<div style="padding: 20px; text-align: center;">분석할 파일이 없습니다.</div>';
        return;
    }

    // 1. 모든 파일을 먼저 "대기 중" 상태로 띄움
    const fileItems = {};
    for (let f of allFiles) {
        const item = document.createElement('div');
        item.className = 'analysis-item-box';
        const filename = f.split('\\').pop();
        item.innerHTML = `
            <div style="font-weight:bold; font-size:0.85rem;">${filename}</div>
            <div class="status-label" style="font-size:0.7rem; color:#94a3b8;">대기 중...</div>
        `;
        pdfQueue.appendChild(item);
        fileItems[f] = item;
    }

    // 2. 순차적으로 분석 진행하며 UI 업데이트
    for (let f of allFiles) {
        const item = fileItems[f];
        const statusLabel = item.querySelector('.status-label');
        statusLabel.innerText = "분석 중 (임베딩 추출)...";
        statusLabel.style.color = "#6366f1";

        try {
            const r = await (await fetch(`${CENTRAL_API_URL}/analyze/file?path=${encodeURIComponent(f)}`)).json();
            analysisResults.push(r);
            
            if (r.status === "success") {
                statusLabel.innerText = "분석 완료";
                statusLabel.style.color = "#10b981"; // 초록색
            } else {
                statusLabel.innerText = `분석 실패: ${r.error || "알 수 없는 오류"}`;
                statusLabel.style.color = "#ef4444"; // 빨간색
                unclassified.appendChild(item); // 실패 시 하단으로 이동
            }
        } catch(e) {
            statusLabel.innerText = "서버 연결 오류";
            statusLabel.style.color = "#ef4444";
            unclassified.appendChild(item);
            analysisResults.push({path: f, status: "failed", error: "서버 연결 오류"});
        }
    }
    document.getElementById('btn-start-classify').disabled = false;
}

async function collect(p, files) {
    try {
        const d = await (await fetch(`${CENTRAL_API_URL}/list/directory?path=${encodeURIComponent(p)}`)).json();
        if (d.is_file) files.push(p);
        else if (d.items) for (let i of d.items) await collect(i.path, files);
    } catch(e) {}
}

// 3. 분류 및 이동 (기존과 동일하되 가독성 유지)
async function startClassification() {
    const moveTree = document.getElementById('move-tree');
    moveTree.innerHTML = '<div style="padding: 20px; text-align: center;">클러스터링 중...</div>';
    
    const res = await (await fetch(`${CENTRAL_API_URL}/classify`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(analysisResults)
    })).json();

    currentMoveProposals = res.move_proposals;
    refreshClassificationUI();
    document.getElementById('btn-confirm-move').disabled = false;
}

function addNewFolder() {
    const name = prompt("새 폴더 이름을 입력하세요:");
    if (name) {
        if (!customFolders.includes(name)) {
            customFolders.push(name);
            refreshClassificationUI();
        }
    }
}

function createMoveItem(path) {
    const item = document.createElement('div');
    item.className = 'move-item-box';
    item.draggable = true;
    item.setAttribute('data-path', path);
    item.innerHTML = `<div style="font-size:0.8rem;">📄 ${path.split('\\').pop()}</div>`;
    item.ondragstart = (e) => { e.dataTransfer.setData("text/plain", path); };
    return item;
}

function handleDropToFolder(e, targetFolder) {
    e.preventDefault();
    const path = e.dataTransfer.getData("text/plain");
    currentMoveProposals = currentMoveProposals.filter(p => p.original_path !== path);
    currentMoveProposals.push({
        original_path: path,
        target_folder: targetFolder,
        target_full_path: `outputs\\${targetFolder}\\${path.split('\\').pop()}`
    });
    refreshClassificationUI();
}

function handleDropToManual(e) {
    e.preventDefault();
    const path = e.dataTransfer.getData("text/plain");
    currentMoveProposals = currentMoveProposals.filter(p => p.original_path !== path);
    refreshClassificationUI();
}

function refreshClassificationUI() {
    const moveTree = document.getElementById('move-tree'), manual = document.getElementById('manual-list');
    const folders = {};
    const proposedPaths = new Set(currentMoveProposals.map(p => p.original_path));

    currentMoveProposals.forEach(p => {
        if (!folders[p.target_folder]) folders[p.target_folder] = [];
        folders[p.target_folder].push(p);
    });
    
    customFolders.forEach(name => {
        if (!folders[name]) folders[name] = [];
    });

    moveTree.innerHTML = '';
    for (let [folder, files] of Object.entries(folders)) {
        const group = document.createElement('div'); 
        group.className = 'tree-group-box';
        group.setAttribute('data-folder', folder);
        group.innerHTML = `<div class="tree-row"><span class="tree-icon">📁</span><span class="tree-name">${folder}</span></div>`;
        group.ondragover = (e) => e.preventDefault();
        group.ondrop = (e) => handleDropToFolder(e, folder);
        files.forEach(f => group.appendChild(createMoveItem(f.original_path)));
        moveTree.appendChild(group);
    }

    manual.innerHTML = '';
    analysisResults.forEach(r => {
        if (!proposedPaths.has(r.path)) {
            manual.appendChild(createMoveItem(r.path));
        }
    });
}

async function confirmMove() {
    const proposedPaths = new Set(currentMoveProposals.map(p => p.original_path));
    const unassigned = analysisResults.filter(r => !proposedPaths.has(r.path));

    if (unassigned.length > 0) {
        const choice = prompt(
            `이동을 지정하지 않은 파일이 ${unassigned.length}개 있습니다.\n\n` +
            `1: 무시하고 지정된 파일만 이동\n` +
            `2: '미분류(unclassified)' 폴더로 모두 이동\n` +
            `3: 돌아가서 작업 계속 (취소)`
        );

        if (choice === "1") {
            // 그대로 진행
        } else if (choice === "2") {
            unassigned.forEach(r => {
                currentMoveProposals.push({
                    original_path: r.path,
                    target_folder: "unclassified",
                    target_full_path: `outputs\\unclassified\\${r.filename || r.path.split('\\').pop()}`
                });
            });
        } else {
            return; 
        }
    } else {
        if (!confirm("파일 이동을 확정하시겠습니까?")) return;
    }

    try {
        await fetch(`${CENTRAL_API_URL}/execute_move`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(currentMoveProposals)
        });
        alert("이동 완료!");
        location.reload();
    } catch(e) {
        alert("이동 실행 중 오류 발생");
    }
}
