package handlers

import (
	"net/http"
	"net/url"
	"strconv"

	"github.com/labstack/echo/v4"
	"github.com/shumizu418128/gbbinfo3.0/internal/config"
)

// JapanHandler: 日本代表のハンドラの型
type JapanHandler struct {
    // 必要に応じて依存関係を注入
}

// NewJapanHandler: JapanHandlerのコンストラクタ
// コンストラクタ = インスタンスを作成する関数
func NewJapanHandler() *JapanHandler {
    return &JapanHandler{}
}

// Handle: 日本代表のハンドラ
func (h *JapanHandler) Handle(c echo.Context, year int, content string) error {
	// テンプレートに渡すデータを準備
	// 日本代表出場者を取得

    return c.Render(http.StatusOK, "japan.html", map[string]interface{}{
        "year": year,
    })
}
