package i18n

import (
    "encoding/binary"
    "io"
    "os"
)

type moHeader struct {
    Magic          uint32
    FormatVersion  uint32
    StringCount    uint32
    OriginalOffset uint32
    TranslationOffset uint32
    HashTableSize  uint32
    HashOffset     uint32
}

func loadMoFile(path string) (map[string]string, error) {
    file, err := os.Open(path)
    if err != nil {
        return nil, err
    }
    defer file.Close()

    var header moHeader
    if err := binary.Read(file, binary.LittleEndian, &header); err != nil {
        return nil, err
    }

    // 文字列テーブルの読み込み
    messages := make(map[string]string)

    // オリジナル文字列の読み込み
    file.Seek(int64(header.OriginalOffset), io.SeekStart)
    for i := uint32(0); i < header.StringCount; i++ {
        var length, offset uint32
        if err := binary.Read(file, binary.LittleEndian, &length); err != nil {
            return nil, err
        }
        if err := binary.Read(file, binary.LittleEndian, &offset); err != nil {
            return nil, err
        }

        // 文字列の読み込み
        buf := make([]byte, length)
        if _, err := file.ReadAt(buf, int64(offset)); err != nil {
            return nil, err
        }
        key := string(buf)

        // 翻訳文字列の読み込み
        if err := binary.Read(file, binary.LittleEndian, &length); err != nil {
            return nil, err
        }
        if err := binary.Read(file, binary.LittleEndian, &offset); err != nil {
            return nil, err
        }

        buf = make([]byte, length)
        if _, err := file.ReadAt(buf, int64(offset)); err != nil {
            return nil, err
        }
        value := string(buf)

        messages[key] = value
    }

    return messages, nil
}
