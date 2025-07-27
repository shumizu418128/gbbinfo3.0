// 検索フォームの送信処理
function handleSearchFormSubmit(event) {
    event.preventDefault();
    const formData = new FormData(this);
    const searchQuery = formData.get('question');
    const loadingElement = document.getElementById('loading');

    // キーワードボタンのテキストと一致するかチェック
    const keywordButtons = document.getElementById('keyword-buttons');
    if (keywordButtons) {
        // キーワードボタン内の全てのbuttonを取得
        const buttons = keywordButtons.getElementsByTagName('button');
        for (const button of buttons) {
            // ボタンのテキストと検索クエリが一致する場合
            if (button.textContent === searchQuery) {
                // onclick属性から処理内容を取得して実行
                const onclickAttr = button.getAttribute('onclick');
                if (onclickAttr) {
                    const match = onclickAttr.match(/showKeywordOptions\('(.+)'\)/);
                    if (match) {
                        const optionType = match[1];
                        document.querySelector('.popup').style.display = 'block';
                        document.querySelector('.background-popup-keyword').style.display = 'block';
                        document.getElementById(`${optionType}Options`).style.display = 'block';
                        return;
                    }
                }
            }
        }
    }

    loadingElement.style.display = 'block';

    const sendRequest = (retryCount = 0) => {
        console.log(JSON.stringify(Object.fromEntries(formData)));
        fetch(this.action, {
            method: "POST",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(Object.fromEntries(formData))
        })
        .then(response => response.json())
        .then(data => {
            if (data?.url) {
                window.location.href = data.url;
            } else if (retryCount < 5) {
                // 5回まで再試行
                sendRequest(retryCount + 1);
            } else {
                loadingElement.style.display = 'none';
            }
        })
        .catch(() => {
            if (retryCount < 5) {
                // エラーの場合も5回まで再試行
                sendRequest(retryCount + 1);
            } else {
                loadingElement.style.display = 'none';
                alert('エラーが発生しました。もう一度お試しください。');
            }
        });
    };

    sendRequest();
}

// ナビゲーションメニューの開閉処理
function toggleSearchMenu() {
    const searchMenu = document.getElementById('search-menu-nav');
    searchMenu.style.display = (searchMenu.style.display === 'none' || searchMenu.style.display === '') ? 'block' : 'none';

    const searchIcon = document.getElementById('search-icon');
    const closeIcon = document.getElementById('close-icon');
    const searchMsg = document.getElementById('search-msg');

    if (searchMenu.style.display === 'block') {
        searchMsg.textContent = 'とじる';
        searchIcon.style.display = 'none';
        closeIcon.style.display = 'block';
    } else {
        searchMsg.textContent = 'さがす';
        searchIcon.style.display = 'block';
        closeIcon.style.display = 'none';
    }
}

// 参加者検索処理
// biome-ignore lint/correctness/noUnusedVariables: base.htmlで使ってる
function searchParticipants(year) {
    const input = document.getElementById('keyword').value;
    const loadingElement = document.getElementById('loading');
    const resultElement = document.getElementById('participants-search-result');
    const exactMatch = document.getElementById('exact-match-message');

    if (input) {
        loadingElement.style.display = 'block';

        fetch(`/${year}/search_participants`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({keyword: input})
        })
        .then(response => response.json())
        .then(data => {
            const input = document.getElementById('keyword').value;
            let exactMatchFound = false;

            const table = data.map(participant => {
                if (participant.name === input.toUpperCase()) {
                    exactMatchFound = true;
                }
                return `<tr>
                    <td>
                        ${participant.is_cancelled ? '【辞退】<br><s>' : ''}
                        ${participant.name}
                        <div id="small-text">${participant.members}</div>
                        ${participant.is_cancelled ? '</s>' : ''}
                    </td>
                    <td>
                        ${participant.is_cancelled ? `<s>${participant.category}</s>` : participant.category}
                    </td>
                    <td style="${participant.ticket_class.length > 11 ? 'font-size: 12px;' : ''}">
                        ${participant.is_cancelled ? `<s>${participant.ticket_class}</s>` : participant.ticket_class}
                    </td>
                </tr>`;
            }).join('');

            resultElement.innerHTML = table ? table : '<p>-</p>';
            loadingElement.style.display = 'none';
            if (!exactMatchFound) {
                exactMatch.style.display = 'block';
                exactMatch.textContent = `not found: "${input}" は見つかりませんでした。`;
            } else {
                exactMatch.style.display = 'none';
            }
        })
        .catch(error => console.error('Error:', error));
    } else {
        document.getElementById('participants-search-result').innerHTML = '<p>-</p>';
        loadingElement.style.display = 'none';
        exactMatch.style.display = 'none';
    }
}

// 検索候補の表示処理
function setupSearchSuggestions(searchForm) {
    const suggestionsContainer = searchForm.closest('.search-container').nextElementSibling;

    searchForm.addEventListener('input', function() {
        const query = this.querySelector('input').value;

        if (query.length > 0) {
            fetch('/search_suggestions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ input: query })
            })
            .then(response => response.json())
            .then(data => {
                suggestionsContainer.innerHTML = '';
                suggestionsContainer.style.display = 'block';

                if (data.suggestions.length > 0) {
                    data.suggestions.forEach(item => {
                        const suggestionItem = document.createElement('div');
                        suggestionItem.classList.add('suggestion-item');
                        suggestionItem.textContent = item;
                        suggestionItem.addEventListener('click', () => {
                            searchForm.querySelector('input').value = item;
                            suggestionsContainer.style.display = 'none';
                            searchForm.querySelector('button').click();
                        });
                        suggestionsContainer.appendChild(suggestionItem);
                    });
                } else {
                    suggestionsContainer.style.display = 'none';
                }
            })
            .catch(error => console.error('Error:', error));
        } else {
            suggestionsContainer.style.display = 'none';
        }
    });
}

// メニューの外側をクリックしたときにメニューを非表示にする処理
function handleClickOutside(event) {
    const searchMenu = document.getElementById('search-menu-nav');
    const bottomNav = document.querySelector('.bottom-navigation');
    const hamburger = document.querySelector('.hamburger-menu');
    const menu = document.querySelector('.menu');

    if (searchMenu && searchMenu.style.display === 'block' && !bottomNav.contains(event.target)) {
        toggleSearchMenu();
    }
    if (menu && menu.style.display === 'block' && !hamburger.contains(event.target)) {
        menu.style.display = 'none';
    }
}

// メニューの開閉処理
// biome-ignore lint/correctness/noUnusedVariables: base.htmlで使ってる
function toggleMenu() {
    const menu = document.querySelector('.menu');
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
}

// キーワードオプションの表示処理
// biome-ignore lint/correctness/noUnusedVariables: top.htmlで使ってる
function showKeywordOptions(type) {
    const popup = document.querySelector('.popup');

    // popup内の全てのdivを取得し、一旦全て非表示
    const allOptions = popup.getElementsByTagName('div');
    for (const option of allOptions) {
        if (option.id?.endsWith('Options')) {
            option.style.display = 'none';
        }
    }

    // 選択されたオプションを表示
    const targetOptions = document.getElementById(type + 'Options');
    if (targetOptions) {
        targetOptions.style.display = 'block';
    }

    // ポップアップと背景を表示
    popup.style.display = 'block';
    document.querySelector('.background-popup-keyword').style.display = 'block';
}

// キーワードオプションを閉じる処理
// biome-ignore lint/correctness/noUnusedVariables: top.htmlで使ってる
function closeKeywordOptions() {
    const popup = document.querySelector('.popup');

    // popup内の全てのdivを非表示
    const allOptions = popup.getElementsByTagName('div');
    for (const option of allOptions) {
        if (option.id?.endsWith('Options')) {
            option.style.display = 'none';
        }
    }

    // ポップアップと背景を非表示
    popup.style.display = 'none';
    document.querySelector('.background-popup-keyword').style.display = 'none';
}

// イベントリスナーの登録
document.addEventListener('DOMContentLoaded', () => {
    // 検索フォーム
    const topSearchForm = document.getElementById('search-form-top');
    const bottomSearchForm = document.getElementById('search-form-bottom');
    const navSearchForm = document.getElementById('search-form-nav');

    if (topSearchForm) {
        topSearchForm.addEventListener('submit', handleSearchFormSubmit);
        setupSearchSuggestions(topSearchForm);
    }
    if (bottomSearchForm) {
        bottomSearchForm.addEventListener('submit', handleSearchFormSubmit);
        setupSearchSuggestions(bottomSearchForm);
    }
    if (navSearchForm) {
        navSearchForm.addEventListener('submit', handleSearchFormSubmit);
        setupSearchSuggestions(navSearchForm);
    }

    // ナビゲーションメニュー
    const bottomNavigationSearch = document.getElementById('bottom-navigation-search');
    bottomNavigationSearch.addEventListener('click', toggleSearchMenu);

    // メニューの外側をクリック
    document.addEventListener('click', handleClickOutside);
});
