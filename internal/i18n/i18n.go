package i18n

import (
	"os"
	"path/filepath"
	"sync"
)

// Translation: 国際化のための構造体
type Translation struct {
    Messages map[string]string
    mu       sync.RWMutex
}

// I18n: 国際化のための構造体
type I18n struct {
    translations map[string]*Translation
    defaultLang  string
    mu           sync.RWMutex
}

// New: I18nのコンストラクタ
// コンストラクタ = インスタンスを作成する関数
func New(defaultLang string) *I18n {
    return &I18n{
        translations: make(map[string]*Translation),
        defaultLang:  defaultLang,
    }
}

// LoadTranslations: 翻訳ファイルを読み込む関数
func (i *I18n) LoadTranslations(translationsDir string) error {
	// ロックを取得 (データの競合を防ぐため)
    i.mu.Lock()

	// ロックを解放
	defer i.mu.Unlock()

    // translationsディレクトリ内の各言語ディレクトリを走査
    entries, err := os.ReadDir(translationsDir)
    if err != nil {
        return err
    }

	// 各言語ディレクトリを走査
    for _, entry := range entries {
		// ディレクトリでない場合はスキップ
        if !entry.IsDir() {
            continue
        }

		// 言語ディレクトリの名前を取得
        lang := entry.Name()

		// .moファイルのパスを取得
        moPath := filepath.Join(translationsDir, lang, "LC_MESSAGES", "messages.mo")

        // .moファイルを読み込んでJSONに変換
		// loadMoFile: .moファイルを読み込む関数 (i18n/mo.go)
        messages, err := loadMoFile(moPath)
        if err != nil {
            continue // エラーがあっても次の言語を試す
        }

		// 翻訳データを保存
        i.translations[lang] = &Translation{
            Messages: messages,
        }
    }

	// エラーがない場合はnilを返す
	// nil = エラーがないことを表す
    return nil
}

// GetTranslation: 翻訳データを取得する関数
func (i *I18n) GetTranslation(lang string) string {
	// ロックを取得 (データの競合を防ぐため)
    i.mu.RLock()

	// ロックを解放
    defer i.mu.RUnlock()

	// 翻訳データが存在する場合はその言語を返す
    if _, ok := i.translations[lang]; ok {
        return lang
    }

	// 翻訳データが存在しない場合はデフォルト言語を返す
    return i.defaultLang
}

// Translate: 翻訳データを取得する関数
func (i *I18n) Translate(lang, key string) string {
	// ロックを取得 (データの競合を防ぐため)
    i.mu.RLock()

	// ロックを解放
    defer i.mu.RUnlock()

	// 翻訳データが存在する場合はその言語を返す
    if trans, ok := i.translations[lang]; ok {
        trans.mu.RLock()
        if msg, ok := trans.Messages[key]; ok {
			// ロックを解放
            trans.mu.RUnlock()
            return msg
        }

		// 翻訳データが存在しない場合はロックを解放
        trans.mu.RUnlock()
    }

    // 翻訳が見つからない場合はデフォルト言語を試す
    if lang != i.defaultLang {
        return i.Translate(i.defaultLang, key)
    }

    return key
}
