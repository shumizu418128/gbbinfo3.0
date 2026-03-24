import copy
import os
import unittest
from unittest.mock import MagicMock, patch

# app.main import 時に sitemap 初期化で supabase が呼ばれるため、
# テスト用に最低限のモックを用意してから app を import します。
with patch("app.context_processors.supabase_service") as mock_ctx_supabase:

    def _mock_ctx_get_data(*args, **kwargs):
        table = kwargs.get("table")
        if table == "Year":
            return [{"year": 2025}]
        if table == "Participant":
            return [
                {
                    "id": 1,
                    "name": "Test",
                    "Category": {"is_team": False},
                }
            ]
        if table == "ParticipantMember":
            return [{"id": 2}]
        return []

    mock_ctx_supabase.get_data.side_effect = _mock_ctx_get_data
    from app.main import app


class WorldMapCacheTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        # テストでモックしている `Year` の値に固定して環境依存性を排除する
        self.year = 2025

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

    def tearDown(self):
        self.app_context.pop()

    def _build_world_map_country_df(self):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "iso_code": 392,
                    "latitude": 35.0,
                    "longitude": 139.0,
                    "names": {"ja": "日本", "en": "Japan"},
                    "iso_alpha2": "JP",
                }
            ]
        )

    def test_world_map_cache_skips_generation_for_same_participants_data(
        self,
    ):
        participants_data_a = [
            {
                "id": 1,
                "name": "alpha",
                "iso_code": 392,
                "ticket_class": "Solo",
                "Category": {"id": 1, "name": "Solo", "is_team": False},
                "ParticipantMember": [],
            }
        ]
        participants_data_hash_a = hash(str(participants_data_a))

        expected_template = f"{self.year}/world_map/ja_{participants_data_hash_a}.html"
        expected_map_save_path = os.path.join(
            "app",
            "templates",
            str(self.year),
            "world_map",
            f"ja_{participants_data_hash_a}.html",
        )

        dummy_map = MagicMock()
        dummy_root = MagicMock()
        dummy_header = MagicMock()
        dummy_root.header = dummy_header
        dummy_map.get_root.return_value = dummy_root

        tile_layer_instance = MagicMock()
        tile_layer_instance.add_to.return_value = dummy_map

        marker_instance = MagicMock()
        marker_instance.add_to.return_value = dummy_map

        country_df = self._build_world_map_country_df()

        with (
            patch("app.views.world_map.supabase_service") as mock_supabase,
            patch("app.views.world_map.os.path.exists") as mock_os_path_exists,
            patch("app.views.world_map.render_template") as mock_render_template,
            patch("app.views.world_map.folium.Map") as mock_folium_map,
            patch("app.views.world_map.folium.TileLayer") as mock_tile_layer,
            patch("app.views.world_map.folium.Element") as mock_folium_element,
            patch("app.views.world_map.folium.Popup") as mock_folium_popup,
            patch("app.views.world_map.folium.CustomIcon") as mock_folium_custom_icon,
            patch("app.views.world_map.folium.Marker") as mock_folium_marker,
        ):
            mock_os_path_exists.side_effect = [False, True]
            mock_render_template.return_value = "rendered"

            mock_folium_map.return_value = dummy_map
            mock_tile_layer.return_value = tile_layer_instance
            mock_folium_element.return_value = MagicMock()
            mock_folium_popup.return_value = MagicMock()
            mock_folium_custom_icon.return_value = MagicMock()
            mock_folium_marker.return_value = marker_instance

            def _get_data_side_effect(*args, **kwargs):
                table = kwargs.get("table")
                if table == "Participant":
                    # 2回とも同一 participants_data を返す
                    return copy.deepcopy(participants_data_a)
                if table == "Country":
                    return country_df
                return []

            mock_supabase.get_data.side_effect = _get_data_side_effect

            resp1 = self.client.get(f"/ja/{self.year}/world_map")
            resp2 = self.client.get(f"/ja/{self.year}/world_map")

            self.assertEqual(resp1.status_code, 200)
            self.assertEqual(resp2.status_code, 200)

            # 1回目: 生成（save が呼ばれる）
            self.assertEqual(mock_folium_map.call_count, 1)
            self.assertEqual(dummy_map.save.call_count, 1)

            # 2回目: os.path.exists で存在判定し生成スキップ（save/Map なし）
            self.assertEqual(mock_os_path_exists.call_count, 2)
            self.assertEqual(mock_render_template.call_count, 2)

            # テンプレート名は同じ participants_data_hash を使い続ける
            for call_args in mock_render_template.call_args_list:
                self.assertEqual(call_args.args[0], expected_template)

            os_exists_paths = [
                call.args[0] for call in mock_os_path_exists.call_args_list
            ]
            self.assertEqual(
                os_exists_paths,
                [expected_map_save_path, expected_map_save_path],
            )

    def test_world_map_cache_regenerates_for_different_participants_data(self):
        participants_data_a = [
            {
                "id": 1,
                "name": "alpha",
                "iso_code": 392,
                "ticket_class": "Solo",
                "Category": {"id": 1, "name": "Solo", "is_team": False},
                "ParticipantMember": [],
            }
        ]
        participants_data_b = [
            {
                "id": 2,
                "name": "beta",
                "iso_code": 392,
                "ticket_class": "Solo",
                "Category": {"id": 1, "name": "Solo", "is_team": False},
                "ParticipantMember": [],
            }
        ]

        participants_data_hash_a = hash(str(participants_data_a))
        participants_data_hash_b = hash(str(participants_data_b))

        expected_template_a = (
            f"{self.year}/world_map/ja_{participants_data_hash_a}.html"
        )
        expected_template_b = (
            f"{self.year}/world_map/ja_{participants_data_hash_b}.html"
        )

        expected_map_save_path_a = os.path.join(
            "app",
            "templates",
            str(self.year),
            "world_map",
            f"ja_{participants_data_hash_a}.html",
        )
        expected_map_save_path_b = os.path.join(
            "app",
            "templates",
            str(self.year),
            "world_map",
            f"ja_{participants_data_hash_b}.html",
        )

        dummy_map = MagicMock()
        dummy_root = MagicMock()
        dummy_header = MagicMock()
        dummy_root.header = dummy_header
        dummy_map.get_root.return_value = dummy_root

        tile_layer_instance = MagicMock()
        tile_layer_instance.add_to.return_value = dummy_map

        marker_instance = MagicMock()
        marker_instance.add_to.return_value = dummy_map

        country_df = self._build_world_map_country_df()

        participants_by_request = [participants_data_a, participants_data_b]
        participant_call_count = {"n": 0}

        with (
            patch("app.views.world_map.supabase_service") as mock_supabase,
            patch("app.views.world_map.os.path.exists") as mock_os_path_exists,
            patch("app.views.world_map.render_template") as mock_render_template,
            patch("app.views.world_map.folium.Map") as mock_folium_map,
            patch("app.views.world_map.folium.TileLayer") as mock_tile_layer,
            patch("app.views.world_map.folium.Element") as mock_folium_element,
            patch("app.views.world_map.folium.Popup") as mock_folium_popup,
            patch("app.views.world_map.folium.CustomIcon") as mock_folium_custom_icon,
            patch("app.views.world_map.folium.Marker") as mock_folium_marker,
        ):
            # 2回とも存在しない前提（毎回生成）
            mock_os_path_exists.return_value = False
            mock_render_template.return_value = "rendered"

            mock_folium_map.return_value = dummy_map
            mock_tile_layer.return_value = tile_layer_instance
            mock_folium_element.return_value = MagicMock()
            mock_folium_popup.return_value = MagicMock()
            mock_folium_custom_icon.return_value = MagicMock()
            mock_folium_marker.return_value = marker_instance

            def _get_data_side_effect(*args, **kwargs):
                table = kwargs.get("table")
                if table == "Participant":
                    n = participant_call_count["n"]
                    participant_call_count["n"] += 1
                    return copy.deepcopy(participants_by_request[n])
                if table == "Country":
                    return country_df
                return []

            mock_supabase.get_data.side_effect = _get_data_side_effect

            resp1 = self.client.get(f"/ja/{self.year}/world_map")
            resp2 = self.client.get(f"/ja/{self.year}/world_map")

            self.assertEqual(resp1.status_code, 200)
            self.assertEqual(resp2.status_code, 200)

            # participants_data が変わるので、毎回 Map 生成が行われる
            self.assertEqual(mock_folium_map.call_count, 2)
            self.assertEqual(dummy_map.save.call_count, 2)
            self.assertEqual(mock_render_template.call_count, 2)

            # os.path.exists は各 participants_data_hash のファイル名で呼ばれる
            self.assertEqual(
                [call.args[0] for call in mock_os_path_exists.call_args_list],
                [expected_map_save_path_a, expected_map_save_path_b],
            )

            rendered_templates = [
                call_args.args[0] for call_args in mock_render_template.call_args_list
            ]
            self.assertEqual(
                rendered_templates, [expected_template_a, expected_template_b]
            )
