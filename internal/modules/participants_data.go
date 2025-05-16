package models

type ParticipantData struct {
    Name        string
    Category    string
    TicketClass string
    IsoCode     int
    Members     []string
}

// 出場者を取得
func GetParticipants(year int, category string) ([]ParticipantData, error) {
    // ここに処理を書く
}
