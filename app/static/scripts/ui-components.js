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
const installButton = document.getElementById("install-button");
const scrollTopButton = document.getElementById("scroll-top-button");

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
        const response = await fetch('/notice', { method: 'POST', credentials: 'same-origin' });
        const data = await response.json();

        if (data.notice && data.notice.trim() !== '' && data.timestamp) {
            const noticeDivs = document.querySelectorAll('.post-it-notice');
            noticeDivs.forEach((noticeDiv) => {
                const noticeContent = noticeDiv.querySelector('.notice-content');
                const noticeTimestamp = noticeDiv.querySelector('.notice-timestamp');

                if (noticeContent && noticeTimestamp) {
                    noticeContent.textContent = data.notice;
                    noticeTimestamp.textContent = data.timestamp;
                    noticeDiv.style.display = 'block';
                }
            });
        }
    } catch (error) {
        console.error('お知らせの取得に失敗しました:', error);
    }
}

// イベントリスナーの登録
window.onload = () => {
    showPopup();
    loadNotice();
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

function handleScrollTopButtonVisibility() {
    if (!scrollTopButton) {
        return;
    }
    if (window.scrollY > 200) {
        scrollTopButton.classList.add("is-visible");
    } else {
        scrollTopButton.classList.remove("is-visible");
    }
}

function handleScrollTopButtonClick() {
    window.scrollTo({ top: 0, behavior: "smooth" });
}

if (scrollTopButton) {
    scrollTopButton.addEventListener("click", handleScrollTopButtonClick);
    handleScrollTopButtonVisibility();
    window.addEventListener("scroll", handleScrollTopButtonVisibility, { passive: true });
}

// スクロール時にオーバーレイをスワイプアップ（パフォーマンス最適化版）
(function() {
    const overlay = document.getElementById("white-overlay");
    const bottomSection = document.getElementById("bottom-section");

    if (!overlay) {
        return;
    }

    let ticking = false;
    const threshold = 200;

    function updateOverlay() {
        const scrollY = window.scrollY;

        // 最下部の位置を計算
        let bottomThreshold = Infinity;
        if (bottomSection) {
            const rect = bottomSection.getBoundingClientRect();
            const bottomSectionTop = rect.top + scrollY;
            bottomThreshold = bottomSectionTop - window.innerHeight;
        }

        // 最下部に近づいている場合（最下部から200px手前から開始）
        if (bottomSection && scrollY >= bottomThreshold - threshold) {
            // 最下部に到達するまでの進捗を計算
            const bottomProgress = Math.min((scrollY - (bottomThreshold - threshold)) / threshold, 1);
            // 最下部に到達したら完全に下に隠す
            const translateY = bottomProgress * 100;
            overlay.style.transform = `translateY(${translateY}%)`;
        } else {
            // 通常時：常にすべて表示
            overlay.style.transform = "translateY(0%)";
        }

        ticking = false;
    }

    function onScroll() {
        if (!ticking) {
            window.requestAnimationFrame(updateOverlay);
            ticking = true;
        }
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    // 初期状態を設定
    updateOverlay();
})();
