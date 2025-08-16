// FlaskではCSRFトークンは不要のため、取得処理を削除

// YouTube動画を埋め込む関数
function embedYouTubeVideo(videoUrl) {
    const youtubeContainer = document.querySelector('.youtube-embed-video');

    if (videoUrl && youtubeContainer) {
        const wrapper = document.createElement('div');
        wrapper.style.display = 'flex';
        wrapper.style.justifyContent = 'center';
        wrapper.style.alignItems = 'center';
        wrapper.style.width = '100%';

        const aspectRatioContainer = document.createElement('div');
        aspectRatioContainer.style.position = 'relative';
        aspectRatioContainer.style.width = '100%';
        aspectRatioContainer.style.maxWidth = '560px';

        if (CSS.supports('aspect-ratio', '16 / 9')) {
            aspectRatioContainer.style.aspectRatio = '16 / 9';
        } else {
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
        return Promise.reject(new Error('必要な要素が見つかりません'));
    }
    finalUrlsContainer.innerHTML = '<p>loading...</p>';
    return fetch('/beatboxer_tavily_search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            beatboxer_id: beatboxerId,
            mode: mode
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.youtube_embed_url) {
            embedYouTubeVideo(data.youtube_embed_url);
        }
        if (data.account_urls && data.account_urls.length > 0) {
            accountUrlsContainer.innerHTML = createSearchResultHTML(data.account_urls, 'SNS');
        } else {
            accountUrlsContainer.innerHTML = '';
        }
        if (data.final_urls && data.final_urls.length > 0) {
            finalUrlsContainer.innerHTML = createSearchResultHTML(data.final_urls, 'WEB');
        } else {
            finalUrlsContainer.innerHTML = '<p>関連サイトが見つかりませんでした。</p>';
        }
    })
    .catch(error => {
        console.error('Tavily検索エラー:', error);
        finalUrlsContainer.innerHTML = '<p>関連サイトを取得できませんでした。</p>';
        throw error;
    });
}

function answerTranslation(beatboxerId, mode) {
    const answerContainer = document.querySelector('.answer');
    if (!answerContainer) {
        console.error('answer 要素が見つかりません');
        return;
    }
    fetch('/answer_translation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            beatboxer_id: beatboxerId,
            mode: mode
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        const text = data.answer || "";
        if (!text) {
            return;
        }
        answerContainer.innerHTML = `<div class="post-it"></div>`;
        const postIt = answerContainer.querySelector('.post-it');
        let i = 0;
        function typeWriter() {
            if (i < text.length) {
                postIt.textContent += text.charAt(i);
                i++;
                setTimeout(typeWriter, 20);
            }
        }
        typeWriter();
    });
}
