import os
from collections import defaultdict

import folium
from flask import render_template, session

from app.models.supabase_client import supabase_service


def world_map_view(year: int):
    """指定された年のワールドマップを生成し、テンプレートをレンダリングするビュー関数。

    この関数は、指定された年の参加者データをSupabaseから取得し、国ごとに分類して
    Foliumを用いてインタラクティブなワールドマップを作成します。
    既にマップが生成されている場合は、保存済みのHTMLテンプレートを返します。
    そうでない場合は、参加者情報をもとに国ごとのマーカーとポップアップを作成し、
    マップを保存した後にテンプレートをレンダリングします。

    Args:
        year (int): マップを生成する対象の年。

    Returns:
        flask.Response: レンダリングされたHTMLテンプレートのレスポンス。

    Raises:
        KeyError: セッションに"language"が存在しない場合。
        IndexError: 国情報や座標が見つからない場合。
        その他、Supabaseやファイル操作に関する例外が発生する可能性があります。

    Note:
        - 参加者が複数国籍の場合（iso_code=9999）、各国ごとにマーカーが作成されます。
        - 参加者名は大文字に変換されます。
        - ポップアップが長い場合はスクロール可能なデザインになります。
        - 国旗アイコンは`app/static/images/flags/{国名（英語）}.webp`を参照します。
    """
    language = session["language"]

    # マップがすでに作成されている場合はそれを表示
    map_save_path = os.path.join(
        "app", "templates", str(year), "world_map", f"{language}.html"
    )
    if os.path.exists(map_save_path):
        return render_template(f"{year}/world_map/{language}.html")

    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "iso_code"],
        order_by="category",
        join_tables={
            "Category": ["id", "name"],
            "ParticipantMember": ["Country(iso_code)"],
        },
        filters={"year": year, "is_cancelled": False},
    )

    participants_per_country = defaultdict(list)

    for participant in participants_data:
        if participant["iso_code"] == 0:
            continue
        # 全員の名前を大文字に変換
        participant["name"] = participant["name"].upper()

        # カテゴリ名を取り出す
        participant["category"] = participant["Category"]["name"]
        participant.pop("Category")

        # チームかどうかを判断
        participant["is_team"] = len(participant["ParticipantMember"]) > 0

        # 複数国籍のチームの場合、該当国ごとにデータを追加
        if participant["iso_code"] == 9999:
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

    country_coordinates_data = supabase_service.get_data(
        table="Country",
        columns=["iso_code", "latitude", "longitude", "names"],
        pandas=True,
    )

    for iso_code, participants in participants_per_country.items():
        # 国の緯度経度を取得
        latitude = country_coordinates_data.loc[
            country_coordinates_data["iso_code"] == iso_code, "latitude"
        ].values[0]
        longitude = country_coordinates_data.loc[
            country_coordinates_data["iso_code"] == iso_code, "longitude"
        ].values[0]
        location = (latitude, longitude)

        # 国名を取得
        country_names_dict = country_coordinates_data.loc[
            country_coordinates_data["iso_code"] == iso_code, "names"
        ].values[0]
        country_name = country_names_dict[language]

        # ポップアップの内容を作成
        popup_content = "<div style=\"font-family: 'Noto sans JP'; font-size: 14px;\">"
        country_header = f'<h3 style="margin: 0; color: #ff6417;">{country_name}</h3>'
        team_info = (
            f'<h4 style="margin: 0; color: #ff6417;">{len(participants)} team(s)</h4>'
        )
        popup_content += country_header + team_info

        for participant in participants:
            popup_content += f"""
            <p style="margin: 5px 0;">
                <a href="/others/participant_detail?id={participant["id"]}&mode={participant["is_team"]}" target="_top">{participant["name"]}</a> ({participant["category"]})
            </p>
            """
        popup_content += "</div>"

        # ポップアップが長い場合はスクロール可能にする
        if len(participants) > 7:
            popup_content = f"<div style=\"font-family: 'Noto sans JP'; font-size: 14px; max-height: 300px; overflow-y: scroll;\">{popup_content}</div>"

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
