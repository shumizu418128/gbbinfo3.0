package main

import (
	"fmt"
	"net/http"
)

func route(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello, World!")
}

func test_page(w http.ResponseWriter, r *http.Request) {
    http.ServeFile(w, r, "test.html")
}

func main() {
    http.HandleFunc("/", route)
    http.HandleFunc("/test", test_page)
    http.ListenAndServe(":10000", nil)
	fmt.Println("Server started at http://localhost:10000")
}
