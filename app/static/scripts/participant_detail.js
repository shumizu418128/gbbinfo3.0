// CSRFトークンを取得する関数
function getCSRFToken() {
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput) {
        return csrfInput.value;
    }

    // メタタグからも探してみる
    const metaCSRF = document.querySelector('meta[name="csrf-token"]');
    if (metaCSRF) {
        return metaCSRF.getAttribute('content');
    }

    console.error('CSRFトークンが見つかりません');
    return '';
}

// YouTube動画を埋め込む関数
function embedYouTubeVideo(videoUrl) {
    const youtubeContainer = document.querySelector('.youtube-embed-video');

    if (videoUrl && youtubeContainer) {
        // YouTube動画を左右方向中央に配置する（16:9アスペクト比維持）
        const wrapper = document.createElement('div');
        wrapper.style.display = 'flex';
        wrapper.style.justifyContent = 'center';
        wrapper.style.alignItems = 'center';
        wrapper.style.width = '100%';

        // 16:9アスペクト比を維持するコンテナ
        const aspectRatioContainer = document.createElement('div');
        aspectRatioContainer.style.position = 'relative';
        aspectRatioContainer.style.width = '100%';
        aspectRatioContainer.style.maxWidth = '560px';

        // モダンブラウザではaspect-ratioを使用
        if (CSS.supports('aspect-ratio', '16 / 9')) {
            aspectRatioContainer.style.aspectRatio = '16 / 9';
        } else {
            // 古いブラウザ向けのフォールバック（paddingトリック）
            aspectRatioContainer.style.paddingBottom = '56.25%'; // 9/16 * 100%
            aspectRatioContainer.style.height = '0';
        }

        const iframe = document.createElement('iframe');
        iframe.src = videoUrl;
        iframe.title = 'YouTube video player';
        iframe.frameBorder = '0';
        iframe.allow = 'autoplay; encrypted-media; picture-in-picture; web-share';
        iframe.referrerPolicy = 'strict-origin-when-cross-origin';
        iframe.allowFullscreen = true;
        iframe.style.position = 'absolute';
        iframe.style.top = '0';
        iframe.style.left = '0';
        iframe.style.width = '100%';
        iframe.style.height = '100%';

        aspectRatioContainer.appendChild(iframe);
        wrapper.appendChild(aspectRatioContainer);

        youtubeContainer.innerHTML = '';
        youtubeContainer.appendChild(wrapper);
    }
}

// Tavily検索結果からHTMLを生成する関数
function createSearchResultHTML(urls, title) {
    if (!urls || urls.length === 0) {
        return '';
    }

    let html = `<table>
        <thead>
            <tr>
                <th style="width: 32px;"></th>
                <th>${title}</th>
            </tr>
        </thead>
        <tbody>`;

    urls.forEach(url => {
        html += `<tr>
            <td>
                ${url.favicon ? `<img src="${url.favicon}" style="width: 16px;">` : ''}
            </td>
            <td>
                <a href="${url.url}" target="_blank" rel="noopener noreferrer">
                    ${url.title}
                </a>
            </td>
        </tr>`;
    });

    html += '</table>';
    return html;
}

// Tavily検索を実行する関数
// biome-ignore lint/correctness/noUnusedVariables: 使ってる
function tavilySearch(beatboxerId, mode) {
    const accountUrlsContainer = document.querySelector('.account-urls');
    const finalUrlsContainer = document.querySelector('.final-urls');

    if (!accountUrlsContainer || !finalUrlsContainer) {
        console.error('account-urls または final-urls 要素が見つかりません');
        return;
    }

    // ローディング表示
    finalUrlsContainer.innerHTML = '<p>loading...</p>';

    // POSTリクエストでTavily検索を実行
    const formData = new URLSearchParams();
    formData.append('beatboxer_id', beatboxerId);
    formData.append('mode', mode || 'single');

    fetch('/beatboxer_tavily_search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCSRFToken()
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // YouTube動画の埋め込み
        if (data.youtube_embed_url) {
            embedYouTubeVideo(data.youtube_embed_url);
        }

        // アカウントURLの表示
        if (data.account_urls && data.account_urls.length > 0) {
            accountUrlsContainer.innerHTML = createSearchResultHTML(data.account_urls, 'SNS');
        } else {
            accountUrlsContainer.innerHTML = '';
        }

        // その他のURLの表示
        if (data.final_urls && data.final_urls.length > 0) {
            finalUrlsContainer.innerHTML = createSearchResultHTML(data.final_urls, 'WEB');
        } else {
            finalUrlsContainer.innerHTML = '<p>関連サイトが見つかりませんでした。</p>';
        }
    })
    .catch(error => {
        console.error('Tavily検索エラー:', error);
        finalUrlsContainer.innerHTML = '<p>関連サイトを取得できませんでした。</p>';
    });
}

// DOMContentLoadedイベントリスナー
document.addEventListener('DOMContentLoaded', () => {
    // CSRFトークンをMetaタグから取得する場合の処理も追加
    if (!document.querySelector('[name=csrfmiddlewaretoken]')) {
        const metaCSRF = document.querySelector('meta[name="csrf-token"]');
        if (metaCSRF) {
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'csrfmiddlewaretoken';
            hiddenInput.value = metaCSRF.getAttribute('content');
            document.body.appendChild(hiddenInput);
        }
    }
});
