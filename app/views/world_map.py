import os
from collections import defaultdict

import folium
from flask import abort, render_template, session

from app.config.config import FLAG_CODE, FOLIUM_CUSTOM_CSS, MULTI_COUNTRY_TEAM_ISO_CODE
from app.models.supabase_client import supabase_service


# MARK: 世界地図
def world_map_view(year: int):
    """
    世界地図ビュー関数。

    指定された年の出場者データをもとに、国ごとの参加者情報を地図上に可視化する。

    Args:
        year (int): 対象となる年。

    Returns:
        flask.Response: 世界地図ページのHTMLを返す。既にマップが作成されている場合はキャッシュを利用する。

    Notes:
        - セッションから言語情報を取得し、言語ごとにマップをキャッシュする。
        - 出場者データはSupabaseから取得し、国ごとに集計する。
        - チームで複数国籍の場合は、各国ごとにデータを分配する。
        - Foliumを用いて地図を生成し、テンプレートとして保存・表示する。
    """
    language = session["language"]

    # マップがすでに作成されている場合はそれを表示
    map_save_path = os.path.join(
        "app", "templates", str(year), "world_map", f"{language}.html"
    )
    if os.path.exists(map_save_path):
        return render_template(f"{year}/world_map/{language}.html")

    try:
        participants_data = supabase_service.get_data(
            table="Participant",
            columns=["id", "name", "iso_code"],
            order_by="category",
            join_tables={
                "Category": ["id", "name", "is_team"],
                "ParticipantMember": ["Country(iso_code)"],
            },
            filters={"year": year, "is_cancelled": False},
            raise_error=True,
        )
    except Exception:
        abort(500)

    participants_per_country = defaultdict(list)

    for participant in participants_data:
        if participant["iso_code"] == 0:
            continue
        # 全員の名前を大文字に変換
        participant["name"] = participant["name"].upper()

        # カテゴリ名を取り出す
        participant["category"] = participant["Category"]["name"]

        # チームかどうかを判断
        is_team = participant["Category"]["is_team"]
        if is_team is True:
            participant["mode"] = "team"
        elif is_team is False:
            participant["mode"] = "single"

        participant.pop("Category")

        # 複数国籍のチームの場合、該当国ごとにデータを追加
        if participant["iso_code"] == MULTI_COUNTRY_TEAM_ISO_CODE:
            iso_code_list = set()

            for member in participant["ParticipantMember"]:
                iso_code = member["Country"]["iso_code"]
                iso_code_list.add(iso_code)

            for iso_code in iso_code_list:
                participants_per_country[iso_code].append(participant)
        else:
            participants_per_country[participant["iso_code"]].append(participant)

    # mapを作成
    map_center = [20, 0]
    beatboxer_map = folium.Map(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: US National Park Service",
        location=map_center,
        zoom_start=2,
        zoom_control=True,
        control_scale=True,
        min_zoom=1,
        max_zoom=8,
        max_bounds=True,
        options={
            "zoomSnap": 0.1,  # ズームのステップを0.1に設定
            "zoomDelta": 0.1,  # ズームの増減を0.1に設定
        },
    )

    beatboxer_map.get_root().header.add_child(folium.Element(FOLIUM_CUSTOM_CSS))

    try:
        country_coordinates_data = supabase_service.get_data(
            table="Country",
            columns=["iso_code", "latitude", "longitude", "names", "iso_alpha2"],
            pandas=True,
            raise_error=True,
        )
    except Exception:
        abort(500)

    # iso_code をキーに O(1) 参照できる辞書へ変換
    country_rows = {
        int(row["iso_code"]): (
            row["latitude"],
            row["longitude"],
            row["names"],
            row["iso_alpha2"],
        )
        for _, row in country_coordinates_data.iterrows()
    }

    for iso_code, participants in participants_per_country.items():
        # 国の緯度経度・名称・国コードを辞書から取得（存在しない場合はスキップ）
        if iso_code not in country_rows:
            continue
        latitude, longitude, country_names_dict, iso_alpha2 = country_rows[iso_code]
        location = (latitude, longitude)

        # 国名を取得
        country_name = country_names_dict[language]

        # ポップアップの内容を作成 (長い場合はスクロール可能にする)
        popup_content = "<div style=\"font-family: 'Noto sans JP'; font-size: 14px;\">"
        if len(participants) > 7:
            popup_content = "<div style=\"font-family: 'Noto sans JP'; font-size: 14px; max-height: 200px; overflow-y: scroll;\">"

        flag_code = FLAG_CODE.format(iso_alpha2=iso_alpha2)

        country_header = f'<h3 style="margin: 0; color: #ff6417; font-weight: bold;">{flag_code}{country_name}</h3>'
        team_info = f'<h4 style="margin: 0; color: #ff6417; font-weight: bold;">{len(participants)} team(s)</h4>'
        popup_content += country_header + team_info

        for participant in participants:
            popup_content += f"""
            <p style="margin: 5px 0;">
                <a href="/others/participant_detail?id={participant["id"]}&mode={participant["mode"]}" target="_top">{participant["name"]}</a> ({participant["category"]})
            </p>
            """
        popup_content += "</div>"

        # 作ったポップアップをfoliumのPopupオブジェクトに入れる
        popup = folium.Popup(popup_content, max_width=1000)

        # アイコンを設定
        flag_icon_path = os.path.join(
            "app",
            "static",
            "images",
            "flags",
            f"{country_names_dict['en']}.webp",
        )
        flag_icon = folium.CustomIcon(
            icon_image=flag_icon_path,
            icon_size=(48, 48),  # アイコンのサイズ（幅、高さ）
            icon_anchor=(24, 48),  # アイコンのアンカー位置
        )

        # マーカーを設定
        folium.Marker(
            location=location,
            popup=popup,
            icon=flag_icon,
        ).add_to(beatboxer_map)

    beatboxer_map.save(map_save_path)
    return render_template(f"{year}/world_map/{language}.html")
