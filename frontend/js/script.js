const SERVER_URL = "http://127.0.0.1:8000/api";
let activeUserPhone = localStorage.getItem("authenticated_user_phone") || "";

let currentFolderId = "null"; 
let navigationBreadcrumbsCache = [{ id: "null", name: "Home" }];
let rawDirectoryFiles = [];
let rawDirectoryFolders = [];

window.onload = function() {
    if (activeUserPhone) {
        triggerLayoutTransition('view-dashboard-wrapper');
        syncFileSystemExplorerNodes();
    }
};

// --- ROUTING LOGIC ---
function switchRoute(routeName) {
    document.getElementById('route-drive').classList.add('hidden-layout');
    document.getElementById('route-gallery').classList.add('hidden-layout');
    
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    
    const targetRoute = document.getElementById(`route-${routeName}`);
    targetRoute.classList.remove('hidden-layout');
    
    // Restart animation
    targetRoute.classList.remove('fade-in');
    void targetRoute.offsetWidth; // Trigger reflow
    targetRoute.classList.add('fade-in');
    
    event.currentTarget.classList.add('active');

    if (routeName === 'gallery') {
        renderGalleryRoute();
    }
}

// --- GALLERY LOGIC ---
function renderGalleryRoute() {
    const grid = document.getElementById('gallery-grid');
    grid.innerHTML = ""; 

    // Assume common image types based on mime_type or file extension fallback
    const imageFiles = rawDirectoryFiles.filter(file => {
        if (file.mime_type && file.mime_type.startsWith('image/')) return true;
        const ext = file.filename.split('.').pop().toLowerCase();
        return ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext);
    });

    if (imageFiles.length === 0) {
        grid.innerHTML = `<p style="color: var(--text-muted); grid-column: 1 / -1; text-align:center; padding: 40px;">No images found in the current directory.</p>`;
        return;
    }

    imageFiles.forEach((file, index) => {
        const div = document.createElement('div');
        div.className = 'gallery-item';
        div.style.animationDelay = `${index * 0.05}s`; // Staggered animation
        
        const downloadUrl = `${SERVER_URL}/drive/download/${file._id}?phone_number=${encodeURIComponent(activeUserPhone)}`;

        div.innerHTML = `
            <a href="${downloadUrl}" target="_blank" style="text-decoration: none;">
                <span class="gallery-icon">🖼️</span>
                <div class="gallery-name">${file.filename}</div>
                <div style="font-size: 11px; color: var(--text-muted); margin-top: 5px;">${formatBytes(file.size)}</div>
            </a>
        `;
        grid.appendChild(div);
    });
}

// --- UI UTILS ---
function printFeedback(msg, styleClass = "slate") {
    const banner = document.getElementById('message-banner');
    banner.style.display = "block"; 
    banner.innerText = msg;
    
    if (styleClass === "green") { banner.style.backgroundColor = "#E8F5E9"; banner.style.color = "#2E7D32"; border = "1px solid #A5D6A7"; }
    else if (styleClass === "orange") { banner.style.backgroundColor = "#FFF3E0"; banner.style.color = "#EF6C00"; border = "1px solid #FFCC80"; }
    else if (styleClass === "red") { banner.style.backgroundColor = "#FFEBEE"; banner.style.color = "#C62828"; border = "1px solid #EF9A9A"; }
    else { banner.style.backgroundColor = "#F0F4F8"; banner.style.color = "#222222"; border = "1px solid #DFE5EC"; }
    
    banner.style.border = border;
    setTimeout(() => { banner.style.display = 'none'; }, 3000);
}

function triggerLayoutTransition(targetId) {
    document.getElementById('view-phone').classList.add('hidden-layout');
    document.getElementById('view-otp').classList.add('hidden-layout');
    document.getElementById('view-dashboard-wrapper').classList.add('hidden-layout');
    document.getElementById(targetId).classList.remove('hidden-layout');
}

// --- API LOGIC ---
async function executeSessionHandshake() {
    const inputVal = document.getElementById('phone-field').value.trim();
    if (!inputVal) return alert("Phone number required.");
    activeUserPhone = inputVal;
    printFeedback("Connecting to server...", "orange");

    try {
        const check = await fetch(`${SERVER_URL}/auth/check-session`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone_number: activeUserPhone })
        });
        const sessionStatus = await check.json();

        if (sessionStatus.status === "authenticated") {
            localStorage.setItem("authenticated_user_phone", activeUserPhone);
            triggerLayoutTransition('view-dashboard-wrapper');
            printFeedback("Welcome back! Session restored.", "green");
            syncFileSystemExplorerNodes();
            return;
        }

        const res = await fetch(`${SERVER_URL}/auth/send-code`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone_number: activeUserPhone })
        });
        if (res.ok) {
            triggerLayoutTransition('view-otp');
            printFeedback("Code sent! Check your Telegram App.", "green");
        } else { printFeedback("Access Denied", "red"); }
    } catch (e) { printFeedback("Server connection failed.", "red"); }
}

async function executeOtpVerification() {
    const otpVal = document.getElementById('otp-field').value.trim();
    try {
        const res = await fetch(`${SERVER_URL}/auth/verify-code`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone_number: activeUserPhone, otp_code: otpVal })
        });
        if (res.ok) {
            localStorage.setItem("authenticated_user_phone", activeUserPhone);
            triggerLayoutTransition('view-dashboard-wrapper');
            printFeedback("Login successful!", "green");
            syncFileSystemExplorerNodes();
        } else { printFeedback("Invalid passcode", "red"); }
    } catch (e) { printFeedback("Verification failed.", "red"); }
}

async function syncFileSystemExplorerNodes() {
    try {
        const url = `${SERVER_URL}/drive/explorer/nodes?phone_number=${encodeURIComponent(activeUserPhone)}&parent_folder_id=${currentFolderId}`;
        const res = await fetch(url);
        const data = await res.json();
        
        if (res.ok) {
            rawDirectoryFiles = data.files;
            rawDirectoryFolders = data.folders;
            renderExplorerGrid(rawDirectoryFolders, rawDirectoryFiles);
            renderBreadcrumbTrail();
            
            // If gallery is currently active, re-render it with new data
            if (!document.getElementById('route-gallery').classList.contains('hidden-layout')) {
                renderGalleryRoute();
            }
        }
    } catch (e) { printFeedback("Failed to load directory data.", "red"); }
}

function renderBreadcrumbTrail() {
    const trailContainer = document.getElementById('breadcrumbs-trail');
    trailContainer.innerHTML = "";
    
    navigationBreadcrumbsCache.forEach((crumb, index) => {
        const nodeSpan = document.createElement('span');
        if (index === navigationBreadcrumbsCache.length - 1) {
            nodeSpan.innerHTML = `<span style="color:var(--text-main);">${crumb.name}</span>`;
        } else {
            nodeSpan.innerHTML = `<span class="crumb-node" onclick="navigateBreadcrumbDepth(${index})">${crumb.name}</span> <span style="margin: 0 8px; color: #ccc;">/</span> `;
        }
        trailContainer.appendChild(nodeSpan);
    });
}

function navigateBreadcrumbDepth(targetIndex) {
    const selectedCrumb = navigationBreadcrumbsCache[targetIndex];
    navigationBreadcrumbsCache = navigationBreadcrumbsCache.slice(0, targetIndex + 1);
    currentFolderId = selectedCrumb.id;
    syncFileSystemExplorerNodes();
}

function drillDownFolder(folderId, folderName) {
    currentFolderId = folderId;
    navigationBreadcrumbsCache.push({ id: folderId, name: folderName });
    syncFileSystemExplorerNodes();
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024, sizes = ['Bytes', 'KB', 'MB', 'GB'], i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function renderExplorerGrid(folders, files) {
    const tbody = document.getElementById('file-table-body');
    tbody.innerHTML = "";
    
    if (folders.length === 0 && files.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding: 30px; color:var(--text-muted);">This folder is empty.</td></tr>`;
        return;
    }

    folders.forEach(dir => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td data-label="Name"><span class="folder-item" onclick="drillDownFolder('${dir._id}', '${dir.folder_name}')">📁 ${dir.folder_name}</span></td>
            <td data-label="Size" style="color:var(--text-muted);">Folder</td>
            <td data-label="Actions" class="action-cell">
                <button type="button" class="btn-action btn-danger" onclick="executeFolderDeletion('${dir._id}')">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });

    files.forEach(file => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td data-label="Name"><span class="file-item">📄 ${file.filename}</span></td>
            <td data-label="Size" style="color:var(--text-muted);">${formatBytes(file.size)}</td>
            <td data-label="Actions" class="action-cell">
                <a class="btn-action" href="${SERVER_URL}/drive/download/${file._id}?phone_number=${encodeURIComponent(activeUserPhone)}" target="_blank">Download</a>
                <button type="button" class="btn-action btn-danger" onclick="executeFileDeletion('${file._id}')">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function executeFileDeletion(fileId) {
    if (!confirm("Are you sure you want to delete this file?")) return;
    printFeedback("Deleting file...", "orange");
    try {
        const res = await fetch(`${SERVER_URL}/drive/file/${fileId}?phone_number=${encodeURIComponent(activeUserPhone)}`, { method: 'DELETE' });
        if (res.ok) {
            printFeedback("File deleted.", "green");
            syncFileSystemExplorerNodes();
        } else { printFeedback("Failed to delete.", "red"); }
    } catch (e) { printFeedback("Network error.", "red"); }
}

async function executeFolderDeletion(folderId) {
    if (!confirm("⚠️ Deleting this folder will erase ALL subfolders and files inside it. Proceed?")) return;
    printFeedback("Deleting folder...", "orange");
    try {
        const res = await fetch(`${SERVER_URL}/drive/folder/${folderId}?phone_number=${encodeURIComponent(activeUserPhone)}`, { method: 'DELETE' });
        if (res.ok) {
            printFeedback("Folder deleted.", "green");
            syncFileSystemExplorerNodes();
        } else { printFeedback("Failed to delete.", "red"); }
    } catch (e) { printFeedback("Network error.", "red"); }
}

async function executeFolderCreation() {
    const field = document.getElementById('folder-name-field');
    const folderName = field.value.trim();
    if (!folderName) return alert("Please enter a folder name.");
    
    printFeedback("Creating folder...", "orange");
    try {
        const res = await fetch(`${SERVER_URL}/drive/folder/create`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder_name: folderName, phone_number: activeUserPhone, parent_folder_id: currentFolderId })
        });
        if (res.ok) {
            printFeedback("Folder created.", "green");
            field.value = "";
            syncFileSystemExplorerNodes();
        }
    } catch (e) { printFeedback("Error creating folder.", "red"); }
}

async function executeCloudUpload() {
    const fileInput = document.getElementById('file-payload');
    if (fileInput.files.length === 0) return alert("Please select a file to upload.");
    printFeedback("Uploading file...", "orange");

    const payload = new FormData();
    payload.append("phone_number", activeUserPhone);
    payload.append("parent_folder_id", currentFolderId);
    payload.append("file", fileInput.files[0]);

    try {
        const res = await fetch(`${SERVER_URL}/drive/upload`, { method: 'POST', body: payload });
        if (res.ok) {
            printFeedback("Upload complete!", "green");
            fileInput.value = "";
            syncFileSystemExplorerNodes();
        } else { printFeedback("Upload failed.", "red"); }
    } catch (e) { printFeedback("Upload error.", "red"); }
}

function filterFileExplorer() {
    const query = document.getElementById('search-input').value.toLowerCase().trim();
    const filteredFolders = rawDirectoryFolders.filter(f => f.folder_name.toLowerCase().includes(query));
    const filteredFiles = rawDirectoryFiles.filter(f => f.filename.toLowerCase().includes(query));
    renderExplorerGrid(filteredFolders, filteredFiles);
}

function executeSessionPurge() {
    localStorage.clear(); activeUserPhone = ""; triggerLayoutTransition('view-phone');
    printFeedback("Logged out successfully.", "slate");
}