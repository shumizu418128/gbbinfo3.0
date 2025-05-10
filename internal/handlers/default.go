package handlers

import (
	"net/http"
	"net/url"
	"strconv"

	"github.com/labstack/echo/v4"
	"github.com/shumizu418128/gbbinfo3.0/internal/config"
)

// DefaultHandler: デフォルトのハンドラの型
type DefaultHandler struct {
    // 必要に応じて依存関係を注入
}

// NewDefaultHandler: DefaultHandlerのコンストラクタ
// コンストラクタ = インスタンスを作成する関数
func NewDefaultHandler() *DefaultHandler {
    return &DefaultHandler{}
}

// Handle: トップページのハンドラ
// ハンドラ = リクエストを処理する関数
func (h *DefaultHandler) Handle(c echo.Context, year int, content string, query url.Values) error {
	var file_path string = "/web/templates/" + strconv.Itoa(year) + "/" + content + ".html"

    // テンプレートに渡すデータを準備
    data := map[string]interface{}{
        "year": year,
		"is_latest_year": year == config.LatestYear,
    }

    return c.Render(http.StatusOK, file_path, data)
}
