from app.config.config import SUPPORTED_LOCALES


def get_validated_language(session) -> str:
    """セッションから言語を取得し、SUPPORTED_LOCALESに対して検証します。

    Returns:
        str: 検証された言語コード（デフォルトは "ja"）
    """
    language = session.get("language", "ja")
    if language not in SUPPORTED_LOCALES:
        language = "ja"
    return language
