// ポップアップの表示
function showPopup() {
    const backgroundPopup = document.querySelector(".background-popup");
    const popup = document.querySelector(".popup");
    if (backgroundPopup && popup) {
        backgroundPopup.style.display = "block";
        popup.style.display = "block";
    }
}

// ポップアップの非表示
// biome-ignore lint/correctness/noUnusedVariables: 複数のファイルにまたがって使用されている
function closePopup() {
    const backgroundPopup = document.querySelector(".background-popup");
    const popup = document.querySelector(".popup");
    if (backgroundPopup && popup) {
        backgroundPopup.style.display = "none";
        popup.style.display = "none";
    }
}

// ドロップダウンの開閉
// biome-ignore lint/correctness/noUnusedVariables: bottom_navigation.htmlで使用
function toggleDropdown() {
    var dropdownContent = document.getElementById("dropdown-content");
    dropdownContent.style.display = dropdownContent.style.display === "none" ? "block" : "none";
}

// PWA インストールボタンの処理
let deferredPrompt;
const installButton = document.getElementById("installButton");

function handleInstallButtonClick() {
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then((choiceResult) => {
        if (choiceResult.outcome === "accepted") {
            console.log("ユーザーがアプリのインストールを受け入れました。");
        } else {
            console.log("ユーザーがアプリのインストールを拒否しました。");
        }
        deferredPrompt = null;
    });
}

function handleBeforeInstallPrompt(e) {
    e.preventDefault();
    deferredPrompt = e;
    installButton.style.visibility = "visible";
}

function handleAppInstalled() {
    console.log("アプリがインストールされました。");
    installButton.style.visibility = "hidden";
}

// 通知の取得と表示
async function loadNotice() {
    try {
        const response = await fetch('/notice');
        const data = await response.json();

        if (data.notice && data.notice.trim() !== '' && data.timestamp) {
            const noticeDivs = document.querySelectorAll('.notice');
            noticeDivs.forEach((noticeDiv) => {
                const postIt = document.createElement('div');
                postIt.className = 'post-it-notice';

                const noticeIcon = '<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#222222"><path d="M440-440h80v-200h-80v200Zm40 120q17 0 28.5-11.5T520-360q0-17-11.5-28.5T480-400q-17 0-28.5 11.5T440-360q0 17 11.5 28.5T480-320ZM160-200v-80h80v-280q0-83 50-147.5T420-792v-28q0-25 17.5-42.5T480-880q25 0 42.5 17.5T540-820v28q80 20 130 84.5T720-560v280h80v80H160Zm320-300Zm0 420q-33 0-56.5-23.5T400-160h160q0 33-23.5 56.5T480-80ZM320-280h320v-280q0-66-47-113t-113-47q-66 0-113 47t-47 113v280Z"/></svg>'
                const paragraph = document.createElement('p');
                paragraph.innerHTML = noticeIcon + '<br><strong>管理人からのお知らせ</strong><br>' + data.notice + "<br><br>最終更新<br>" + data.timestamp;

                postIt.appendChild(paragraph);
                noticeDiv.appendChild(postIt);
            });
        }
    } catch (error) {
        console.error('お知らせの取得に失敗しました:', error);
    }
}

// イベントリスナーの登録
window.onload = () => {
    showPopup();
};

// ドロップダウンのクリックイベント
function handleDocumentClick(event) {
    var dropdownContent = document.getElementById("dropdown-content");
    var dropdownButton = document.getElementById("bottom-dropdown");
    if (dropdownContent && dropdownButton && dropdownContent.style.display === 'block') {
        if (!dropdownButton.contains(event.target)) {
            dropdownContent.style.display = 'none';
        }
    }
}

document.addEventListener('click', handleDocumentClick);

window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
window.addEventListener("appinstalled", handleAppInstalled);

if (installButton) {
    installButton.addEventListener("click", handleInstallButtonClick);
}

// 注目キーワードの表示
// biome-ignore lint/correctness/noUnusedVariables: top.htmlで使用
function showKeywordOptions(keyword) {
    document.querySelector(".background-popup-keyword").style.display = "block";
    document.querySelector(".popup").style.display = "block";

    if (keyword === 'wildcard') {
        document.getElementById('wildcardOptions').style.display = 'block';
        document.getElementById('resultOptions').style.display = 'none';
    } else if (keyword === 'result') {
        document.getElementById('resultOptions').style.display = 'block';
        document.getElementById('wildcardOptions').style.display = 'none';
    }
}

// 注目キーワードの非表示
// biome-ignore lint/correctness/noUnusedVariables: top.htmlで使用
function closeKeywordOptions() {
    document.querySelector(".background-popup-keyword").style.display = "none";
    document.querySelector(".popup").style.display = "none";
    document.getElementById('wildcardOptions').style.display = 'none';
    document.getElementById('resultOptions').style.display = 'none';
}
