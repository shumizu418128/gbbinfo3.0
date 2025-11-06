"""
participant_edit.py のテストモジュール

python -m pytest app/tests/test_participant_edit.py -v
"""

import unittest

from app.config.config import (
    ISO_CODE_COUNTRY_ISO_ALPHA2_NOT_FOUND,
    ISO_CODE_COUNTRY_NAMES_OR_ALPHA2_NOT_FOUND,
    ISO_CODE_NOT_FOUND,
    MULTI_COUNTRY_TEAM_ISO_CODE,
)
from app.util.participant_edit import edit_country_data, wildcard_rank_sort


class TestEditCountryData(unittest.TestCase):
    """
    edit_country_data関数のテストケース
    """

    def test_iso_code_zero_without_language(self):
        """
        iso_codeが0の場合、空のiso_alpha2リストと"-"の国名が設定されることを確認（言語指定なし）
        """
        beatboxer_data = {"iso_code": 0}
        result = edit_country_data(beatboxer_data)

        self.assertEqual(result["iso_alpha2"], [])
        self.assertEqual(result["country"], "-")

    def test_iso_code_zero_with_language(self):
        """
        iso_codeが0の場合、空のiso_alpha2リストと"-"の国名が設定されることを確認（言語指定あり）
        """
        beatboxer_data = {"iso_code": 0}
        result = edit_country_data(beatboxer_data, language="ja")

        self.assertEqual(result["iso_alpha2"], [])
        self.assertEqual(result["country"], "-")

    def test_iso_code_zero_in_participant(self):
        """
        Participant内のiso_codeが0の場合でも正しく処理されることを確認
        """
        beatboxer_data = {"Participant": {"iso_code": 0}}
        result = edit_country_data(beatboxer_data)

        self.assertEqual(result["iso_alpha2"], [])
        self.assertEqual(result["country"], "-")

    def test_iso_code_zero_in_country(self):
        """
        Country内のiso_codeが0の場合でも正しく処理されることを確認
        """
        beatboxer_data = {"Country": {"iso_code": 0}}
        result = edit_country_data(beatboxer_data)

        self.assertEqual(result["iso_alpha2"], [])
        self.assertEqual(result["country"], "-")

    def test_iso_code_none_raises_error(self):
        """
        iso_codeがNoneの場合、ValueErrorが発生することを確認
        """
        beatboxer_data = {"iso_code": None}

        with self.assertRaises(ValueError) as context:
            edit_country_data(beatboxer_data)

        self.assertEqual(str(context.exception), ISO_CODE_NOT_FOUND)

    def test_iso_code_missing_raises_error(self):
        """
        iso_codeが存在しない場合、ValueErrorが発生することを確認
        """
        beatboxer_data = {}

        with self.assertRaises(ValueError) as context:
            edit_country_data(beatboxer_data)

        self.assertEqual(str(context.exception), ISO_CODE_NOT_FOUND)

    def test_iso_code_zero_takes_priority_over_participant(self):
        """
        iso_codeが0の場合、Participant内のiso_codeより優先されることを確認
        """
        beatboxer_data = {
            "iso_code": 0,
            "Participant": {
                "iso_code": 123
            },
            "Country": {
                "iso_code": 456,
                "names": {"ja": "テスト国"},
                "iso_alpha2": "TS"
            }
        }
        result = edit_country_data(beatboxer_data)

        self.assertEqual(result["iso_alpha2"], [])
        self.assertEqual(result["country"], "-")

    def test_participant_iso_code_zero_takes_priority_over_country(self):
        """
        Participant内のiso_codeが0の場合、Country内のiso_codeより優先されることを確認
        """
        beatboxer_data = {
            "Participant": {"iso_code": 0},
            "Country": {
                "iso_code": 456,
                "names": {"ja": "テスト国"},
                "iso_alpha2": "TS"
            }
        }
        result = edit_country_data(beatboxer_data)

        self.assertEqual(result["iso_alpha2"], [])
        self.assertEqual(result["country"], "-")

    def test_single_country_with_language(self):
        """
        単一国籍の場合、正しく国名とiso_alpha2が設定されることを確認（言語指定あり）
        """
        beatboxer_data = {
            "iso_code": 392,
            "Country": {
                "names": {"ja": "日本", "en": "Japan"},
                "iso_alpha2": "JP"
            }
        }
        result = edit_country_data(beatboxer_data, language="ja")

        self.assertEqual(result["country"], "日本")
        self.assertEqual(result["iso_alpha2"], ["JP"])
        self.assertNotIn("Country", result)

    def test_single_country_without_language(self):
        """
        単一国籍の場合、正しくiso_alpha2が設定されることを確認（言語指定なし）
        """
        beatboxer_data = {
            "iso_code": 392,
            "Country": {
                "names": {"ja": "日本", "en": "Japan"},
                "iso_alpha2": "JP"
            }
        }
        result = edit_country_data(beatboxer_data)

        self.assertEqual(result["iso_alpha2"], ["JP"])
        self.assertNotIn("Country", result)
        self.assertNotIn("country", result)

    def test_multi_country_team_with_language(self):
        """
        複数国籍チームの場合、正しく国名とiso_alpha2が設定されることを確認（言語指定あり）
        """
        beatboxer_data = {
            "iso_code": MULTI_COUNTRY_TEAM_ISO_CODE,
            "Country": {"iso_code": MULTI_COUNTRY_TEAM_ISO_CODE},
            "ParticipantMember": [
                {
                    "Country": {
                        "names": {"ja": "日本", "en": "Japan"},
                        "iso_alpha2": "JP"
                    }
                },
                {
                    "Country": {
                        "names": {"ja": "韓国", "en": "South Korea"},
                        "iso_alpha2": "KR"
                    }
                }
            ]
        }
        result = edit_country_data(beatboxer_data, language="ja")

        self.assertEqual(result["country"], "日本 / 韓国")
        self.assertEqual(result["iso_alpha2"], ["JP", "KR"])
        self.assertNotIn("Country", result)

    def test_multi_country_team_without_language(self):
        """
        複数国籍チームの場合、正しくiso_alpha2が設定されることを確認（言語指定なし）
        """
        beatboxer_data = {
            "iso_code": MULTI_COUNTRY_TEAM_ISO_CODE,
            "Country": {"iso_code": MULTI_COUNTRY_TEAM_ISO_CODE},
            "ParticipantMember": [
                {
                    "Country": {
                        "names": {"ja": "日本", "en": "Japan"},
                        "iso_alpha2": "JP"
                    }
                },
                {
                    "Country": {
                        "names": {"ja": "韓国", "en": "South Korea"},
                        "iso_alpha2": "KR"
                    }
                }
            ]
        }
        result = edit_country_data(beatboxer_data)

        self.assertEqual(result["iso_alpha2"], ["JP", "KR"])
        self.assertNotIn("Country", result)
        self.assertNotIn("country", result)

    def test_invalid_input_type(self):
        """
        beatboxer_dataがdictでない場合、ValueErrorが発生することを確認
        """
        with self.assertRaises(ValueError) as context:
            edit_country_data("invalid")

        self.assertEqual(str(context.exception), "beatboxer_dataはdictである必要があります")

    def test_single_country_missing_country_data_with_language(self):
        """
        単一国籍でCountryデータが不足している場合、ValueErrorが発生することを確認（言語指定あり）
        """
        beatboxer_data = {
            "iso_code": 392,
            "Country": {}
        }

        with self.assertRaises(ValueError) as context:
            edit_country_data(beatboxer_data, language="ja")

        self.assertEqual(str(context.exception), ISO_CODE_COUNTRY_NAMES_OR_ALPHA2_NOT_FOUND)

    def test_single_country_missing_country_data_without_language(self):
        """
        単一国籍でCountryデータが不足している場合、ValueErrorが発生することを確認（言語指定なし）
        """
        beatboxer_data = {
            "iso_code": 392,
            "Country": {}
        }

        with self.assertRaises(ValueError) as context:
            edit_country_data(beatboxer_data)

        self.assertEqual(str(context.exception), ISO_CODE_COUNTRY_ISO_ALPHA2_NOT_FOUND)

    def test_multi_country_team_missing_member_data_with_language(self):
        """
        複数国籍チームでメンバーのCountryデータが不足している場合、ValueErrorが発生することを確認（言語指定あり）
        """
        beatboxer_data = {
            "iso_code": MULTI_COUNTRY_TEAM_ISO_CODE,
            "Country": {"iso_code": MULTI_COUNTRY_TEAM_ISO_CODE},
            "ParticipantMember": [
                {"Country": {}}
            ]
        }

        with self.assertRaises(ValueError) as context:
            edit_country_data(beatboxer_data, language="ja")

        self.assertEqual(str(context.exception), ISO_CODE_COUNTRY_NAMES_OR_ALPHA2_NOT_FOUND)

    def test_multi_country_team_missing_member_data_without_language(self):
        """
        複数国籍チームでメンバーのCountryデータが不足している場合、ValueErrorが発生することを確認（言語指定なし）
        """
        beatboxer_data = {
            "iso_code": MULTI_COUNTRY_TEAM_ISO_CODE,
            "Country": {"iso_code": MULTI_COUNTRY_TEAM_ISO_CODE},
            "ParticipantMember": [
                {"Country": {}}
            ]
        }

        with self.assertRaises(ValueError) as context:
            edit_country_data(beatboxer_data)

        self.assertEqual(str(context.exception), ISO_CODE_COUNTRY_ISO_ALPHA2_NOT_FOUND)


class TestWildcardRankSort(unittest.TestCase):
    """
    wildcard_rank_sort関数のテストケース
    """

    def test_wildcard_with_year(self):
        """
        年付きのWildcard形式の場合、正しく(year, rank)を返すことを確認
        """
        result = wildcard_rank_sort({"ticket_class": "Wildcard 1 (2020)"})
        self.assertEqual(result, (2020, 1))

        result = wildcard_rank_sort({"ticket_class": "Wildcard 5 (2023)"})
        self.assertEqual(result, (2023, 5))

    def test_wildcard_without_year(self):
        """
        年なしのWildcard形式の場合、正しく(0, rank)を返すことを確認
        """
        result = wildcard_rank_sort({"ticket_class": "Wildcard 1"})
        self.assertEqual(result, (0, 1))

        result = wildcard_rank_sort({"ticket_class": "Wildcard 10"})
        self.assertEqual(result, (0, 10))

    def test_non_wildcard(self):
        """
        Wildcardでない場合、(inf, inf)を返すことを確認
        """
        result = wildcard_rank_sort({"ticket_class": "Champion"})
        self.assertEqual(result, (float("inf"), float("inf")))

        result = wildcard_rank_sort({"ticket_class": "Seed"})
        self.assertEqual(result, (float("inf"), float("inf")))

    def test_wildcard_sorting(self):
        """
        Wildcardのソートが正しく動作することを確認
        """
        data = [
            {"ticket_class": "Wildcard 3 (2020)"},
            {"ticket_class": "Wildcard 1 (2021)"},
            {"ticket_class": "Wildcard 2 (2020)"},
            {"ticket_class": "Champion"},
            {"ticket_class": "Wildcard 1 (2020)"},
        ]

        sorted_data = sorted(data, key=wildcard_rank_sort)

        self.assertEqual(sorted_data[0]["ticket_class"], "Wildcard 1 (2020)")
        self.assertEqual(sorted_data[1]["ticket_class"], "Wildcard 2 (2020)")
        self.assertEqual(sorted_data[2]["ticket_class"], "Wildcard 3 (2020)")
        self.assertEqual(sorted_data[3]["ticket_class"], "Wildcard 1 (2021)")
        self.assertEqual(sorted_data[4]["ticket_class"], "Champion")


if __name__ == "__main__":
    unittest.main()
