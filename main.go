package main

import (
	"fmt"
	"net/http"
	"strings"
	"strconv"
	"net/url"
)

// GBBINFO-JPN対応年度
var AVAILABLE_YEARS = []int{2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017}

// handleRequest: すべてのハンドラ関数の起点
func handleRequest(w http.ResponseWriter, r *http.Request) {
    // queryがあれば取得
    query := r.URL.Query()

    // strings.Splitは文字列のスライス（[]string）を返す
    // インデックスでアクセスするとstring型になる
    var content string = strings.Split(r.URL.Path, "/")[2]

    // 年の取得 (othersページの場合は"others"が入る)
    yearStr := strings.Split(r.URL.Path, "/")[1]
    year, err := strconv.Atoi(yearStr)

    // othersページの場合、別ハンドラに渡す
    if yearStr == "others" {
        handleOthers(w, r, query)
        return
    }
    // yearの数値変換エラー そもそもこのエラーは起こらないはず
    if err != nil {
        http.Error(w, "Invalid year format", http.StatusBadRequest)
        return
    }

    // 2022年のみ、GBBが中止されているので、すべてtopにリダイレクト
    if year == 2022 && content != "top" {
        http.Redirect(w, r, "/2022/top", http.StatusSeeOther)
        return
    }

    // ルートはtopにリダイレクト
    if r.URL.Path == "/" {
        var latest_year int = AVAILABLE_YEARS[len(AVAILABLE_YEARS)-1]
        var latest_top_path string = "/" + strconv.Itoa(latest_year) + "/top"
        http.Redirect(w, r, latest_top_path, http.StatusSeeOther)
        return
    }

    // 特定の処理が必要なページは、別ハンドラに渡す
    switch content {
        case "top":
            handleTop(w, r, query)
            return
        case "participants":
            handleParticipants(w, r, query)
            return
        case "result":
            handleResult(w, r, query)
            return
        case "rule":
            handleRule(w, r, query)
            return
        // 以下クエリパラメータ不要
        case "japan":
            handleJapan(w, r)
            return
        case "korea":
            handleKorea(w, r)
            return
        case "world_map":
            handleWorldMap(w, r)
            return
    }

    // htmlファイルを返す
    var file_path string = "templates/" + content + ".html"
    http.ServeFile(w, r, file_path)
}

// 仮のハンドラ関数
func handleTop(w http.ResponseWriter, r *http.Request, query url.Values) {
    fmt.Fprintf(w, "トップページ")
}

func handleParticipants(w http.ResponseWriter, r *http.Request, query url.Values) {
    fmt.Fprintf(w, "参加者一覧ページ")
}

func handleResult(w http.ResponseWriter, r *http.Request, query url.Values) {
    fmt.Fprintf(w, "結果ページ")
}

func handleRule(w http.ResponseWriter, r *http.Request, query url.Values) {
    fmt.Fprintf(w, "ルールページ")
}

func handleJapan(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "日本代表ページ")
}

func handleKorea(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "韓国代表ページ")
}

func handleWorldMap(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "世界地図ページ")
}

func handleOthers(w http.ResponseWriter, r *http.Request, query url.Values) {
    fmt.Fprintf(w, "その他ページ")
}

func main() {
    http.HandleFunc("/", handleRequest)
    http.ListenAndServe(":10000", nil)
	fmt.Println("Server started at http://localhost:10000")
}
