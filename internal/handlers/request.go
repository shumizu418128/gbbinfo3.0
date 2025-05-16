package handlers

import (
    "fmt"
	"net/http"
	"net/url"
	"strconv"
	"strings"

	"github.com/labstack/echo/v4"
)

// RequestHandler: リクエストを処理するハンドラの型
type RequestHandler struct {
    defaultHandler *DefaultHandler
}

// NewRequestHandler: RequestHandlerのコンストラクタ
// コンストラクタ = インスタンスを作成する関数
func NewRequestHandler() *RequestHandler {
    return &RequestHandler{
        defaultHandler: NewDefaultHandler(),
    }
}

// Handle: リクエストを処理する
func (h *RequestHandler) Handle(c echo.Context) error {
    // 年度・内容をURLから取得
    var path string = c.Request().URL.Path

    // 年度を取得 othersの場合は0とする
	var yearStr string = strings.Split(path, "/")[1]
    var year int
    var err error
    if yearStr == "others" {
        year = -1
    } else {
        year, err = strconv.Atoi(yearStr)
        if err != nil {
            fmt.Println(err)
            return c.String(http.StatusBadRequest, "Invalid year")
        }
    }

    // 内容を取得
	var content string = strings.Split(path, "/")[2]

    // クエリを取得
    var query url.Values = c.Request().URL.Query()

    // 年度・内容をハンドラに渡す

    // 日本代表 query不要
    if content == "japan" {
        return h.japanHandler.Handle(c, year, content)
    }

    // 韓国代表 query不要
    if content == "korea" {
        return h.koreaHandler.Handle(c, year, content)
    }

    // others
    if content == "others" {
        return h.othersHandler.Handle(c, year, content, query)
    }

    // 出場者
    if content == "participants" {
        return h.participantsHandler.Handle(c, year, content, query)
    }

    // 大会結果 query不要
    if content == "results" {
        return h.resultsHandler.Handle(c, year, content)
    }

    // ルール
    if content == "rule" {
        return h.ruleHandler.Handle(c, year, content, query)
    }

    // 世界地図 query不要
    if content == "worldmap" {
        return h.worldmapHandler.Handle(c, year, content)
    }

    // 特に対応が必要ない場合はdefaultHandlerに渡す
    return h.defaultHandler.Handle(c, year, content, query)

}
