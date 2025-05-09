package main

import (
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"

	"github.com/labstack/echo/v4"
	"gopkg.in/yaml.v3"
)
type Config struct {
    AvailableYears []int `yaml:"AVAILABLE_YEARS"`
}

var (
    config []byte
    configData Config
    err error
    AVAILABLE_YEARS []int
    LATEST_YEAR int
)

func init() {
    // config.yamlを読み込む
    config, err = os.ReadFile("config.yaml")
    if err != nil {
        log.Fatalf("Failed to read config.yaml: %v", err)
    }
    // config.yamlを "構造体" に変換
    err = yaml.Unmarshal(config, &configData)
    if err != nil {
        log.Fatalf("Failed to parse config.yaml: %v", err)
    }
    AVAILABLE_YEARS = configData.AvailableYears
    LATEST_YEAR = AVAILABLE_YEARS[0]
}

// handleRequest: すべてのハンドラ関数の起点
func handleRequest(c echo.Context) error {
    // queryがあれば取得
    query := c.QueryParams()

    // strings.Splitは文字列のスライス（[]string）を返す
    // インデックスでアクセスするとstring型になる
    var content string = strings.Split(c.Request().URL.Path, "/")[2]

    // 年の取得 (othersページの場合は"others"が入る)
    yearStr := strings.Split(c.Path(), "/")[1]
    year, err := strconv.Atoi(yearStr)

    // othersページの場合、別ハンドラに渡す
    if yearStr == "others" {
        return handleOthers(c, query)
    }
    // yearの数値変換エラー そもそもこのエラーは起こらないはず
    if err != nil {
        return c.String(http.StatusBadRequest, "Invalid year format")
    }

    // 2022年のみ、GBBが中止されているので、すべてtopにリダイレクト
    if year == 2022 && content != "top" {
        return c.Redirect(http.StatusSeeOther, "/2022/top")
    }

    // ルートはtopにリダイレクト
    if c.Path() == "/" {
        var latest_top_path string = "/" + strconv.Itoa(LATEST_YEAR) + "/top"
        return c.Redirect(http.StatusSeeOther, latest_top_path)
    }

    // 特定の処理が必要なページは、別ハンドラに渡す
    switch content {
        case "top":
            return handleTop(c, query)
        case "participants":
            return handleParticipants(c, query)
        case "result":
            return handleResult(c, query)
        case "rule":
            return handleRule(c, query)
        // 以下クエリパラメータ不要
        case "japan":
            return handleJapan(c)
        case "korea":
            return handleKorea(c)
        case "world_map":
            return handleWorldMap(c)
    }

    // htmlファイルを返す
    var file_path string = "templates/" + content + ".html"
    return c.File(file_path)
}

// 仮のハンドラ関数
func handleTop(c echo.Context, query url.Values) error {
    return c.String(http.StatusOK, "トップページ")
}

func handleParticipants(c echo.Context, query url.Values) error {
    return c.String(http.StatusOK, "参加者一覧ページ")
}

func handleResult(c echo.Context, query url.Values) error {
    return c.String(http.StatusOK, "結果ページ")
}

func handleRule(c echo.Context, query url.Values) error {
    return c.String(http.StatusOK, "ルールページ")
}

func handleJapan(c echo.Context) error {
    return c.String(http.StatusOK, "日本代表ページ")
}

func handleKorea(c echo.Context) error {
    return c.String(http.StatusOK, "韓国代表ページ")
}

func handleWorldMap(c echo.Context) error {
    return c.String(http.StatusOK, "世界地図ページ")
}

func handleOthers(c echo.Context, query url.Values) error {
    return c.String(http.StatusOK, "その他ページ")
}

func main() {
	e := echo.New()
	e.GET("/", handleRequest)
	e.Start(":10000")
	fmt.Println("Server started at http://localhost:10000")
}
