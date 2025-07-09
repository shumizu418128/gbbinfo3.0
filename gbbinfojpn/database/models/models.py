from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .supabase_client import supabase_service


class ParticipantManager:
    """言語固有の出場者情報管理クラス。

    指定された言語での出場者情報取得を効率的に行うためのヘルパークラスです。
    国名も指定された言語で取得されます。
    """

    def __init__(self, language="ja"):
        self.language = language
        self.country_manager = CountryManager(language)

    def get_participants(self, year, category_name):
        """指定された年度とカテゴリの出場者一覧を取得します。

        Args:
            year (int): 大会年度
            category_name (str): カテゴリ名

        Returns:
            list: 出場者情報の辞書のリスト（メンバー情報も含む）
        """
        # カテゴリIDを取得
        category_data = supabase_service.get_data(
            table="categories", columns=["id"], filters={"name": category_name}
        )

        if not category_data:
            return []

        category_id = category_data[0]["id"]

        # Participantデータを取得
        participants_data = supabase_service.get_data(
            table="participants",
            columns=[
                "id",
                "name",
                "year",
                "category",
                "ticket_class",
                "country",
                "is_cancelled",
            ],
            filters={"year": year, "category": category_id},
        )

        # 関連する出場権情報を取得
        ticket_classes_data = supabase_service.get_data(
            table="ticket_classes", columns=["id", "name"]
        )
        ticket_classes_map = {tc["id"]: tc["name"] for tc in ticket_classes_data}

        # 全てのParticipantのIDを収集
        participant_ids = [p["id"] for p in participants_data]

        # ParticipantMemberデータを一括取得
        members_data = []
        if participant_ids:
            members_data = supabase_service.get_data(
                table="participant_members",
                columns=["participant", "name", "country"],
                filters={"participant__in": participant_ids},
            )

        # ParticipantIDごとにメンバーをグループ化
        members_by_participant = {}
        for member in members_data:
            participant_id = member["participant"]
            if participant_id not in members_by_participant:
                members_by_participant[participant_id] = []

            member_country_name = self.country_manager.get_country_name(
                member["country"]
            )
            members_by_participant[participant_id].append(
                {
                    "name": member["name"],
                    "country_iso": member["country"],
                    "country_name": member_country_name,
                }
            )

        participants = []
        for participant_data in participants_data:
            participant_id = participant_data["id"]
            country_iso = participant_data.get("country")
            country_name = self.country_manager.get_country_name(country_iso)

            # メンバー情報を取得（チームの場合）、ソロの場合は空リスト
            members = members_by_participant.get(participant_id, [])

            participants.append(
                {
                    "id": participant_id,
                    "name": participant_data.get("name"),
                    "year": participant_data.get("year"),
                    "category": category_name,
                    "ticket_class": ticket_classes_map.get(
                        participant_data.get("ticket_class"), "Unknown"
                    ),
                    "country_iso": country_iso,
                    "country_name": country_name,
                    "is_cancelled": participant_data.get("is_cancelled", False),
                    "members": members,  # チームメンバー情報（ソロの場合は空リスト）
                }
            )

        return participants

    def get_participants_by_country(self, year, country_iso):
        """指定された年度と国の出場者一覧を取得します。

        Args:
            year (int): 大会年度
            country_iso (int): ISO国コード

        Returns:
            list: 出場者情報の辞書のリスト（メンバー情報も含む）
        """
        # Participantデータを取得
        participants_data = supabase_service.get_data(
            table="participants",
            columns=[
                "id",
                "name",
                "year",
                "category",
                "ticket_class",
                "country",
                "is_cancelled",
            ],
            filters={"year": year, "country": country_iso},
        )

        # 関連するカテゴリ情報を取得
        categories_data = supabase_service.get_data(
            table="categories", columns=["id", "name"]
        )
        categories_map = {cat["id"]: cat["name"] for cat in categories_data}

        # 関連する出場権情報を取得
        ticket_classes_data = supabase_service.get_data(
            table="ticket_classes", columns=["id", "name"]
        )
        ticket_classes_map = {tc["id"]: tc["name"] for tc in ticket_classes_data}

        # 全てのParticipantのIDを収集
        participant_ids = [p["id"] for p in participants_data]

        # ParticipantMemberデータを一括取得
        members_data = []
        if participant_ids:
            members_data = supabase_service.get_data(
                table="participant_members",
                columns=["participant", "name", "country"],
                filters={"participant__in": participant_ids},
            )

        # ParticipantIDごとにメンバーをグループ化
        members_by_participant = {}
        for member in members_data:
            participant_id = member["participant"]
            if participant_id not in members_by_participant:
                members_by_participant[participant_id] = []

            member_country_name = self.country_manager.get_country_name(
                member["country"]
            )
            members_by_participant[participant_id].append(
                {
                    "name": member["name"],
                    "country_iso": member["country"],
                    "country_name": member_country_name,
                }
            )

        country_name = self.country_manager.get_country_name(country_iso)

        participants = []
        for participant_data in participants_data:
            participant_id = participant_data["id"]

            # メンバー情報を取得（チームの場合）、ソロの場合は空リスト
            members = members_by_participant.get(participant_id, [])

            participants.append(
                {
                    "id": participant_id,
                    "name": participant_data.get("name"),
                    "year": participant_data.get("year"),
                    "category": categories_map.get(
                        participant_data.get("category"), "Unknown"
                    ),
                    "ticket_class": ticket_classes_map.get(
                        participant_data.get("ticket_class"), "Unknown"
                    ),
                    "country_iso": country_iso,
                    "country_name": country_name,
                    "is_cancelled": participant_data.get("is_cancelled", False),
                    "members": members,  # チームメンバー情報（ソロの場合は空リスト）
                }
            )

        return participants


class CountryManager:
    """言語固有の国情報管理クラス。

    指定された言語での国情報取得を効率的に行うためのヘルパークラスです。
    """

    def __init__(self, language="ja"):
        self.language = language

    def get_country_name(self, iso_code):
        """指定されたISO国コードの国名を取得します。

        Args:
            iso_code (int): ISO国コード

        Returns:
            str: 指定された言語での国名
        """
        data = supabase_service.get_data(
            table="countries",
            columns=["names"],
            filters={"iso_code": iso_code},
        )

        if not data:
            return f"Country {iso_code}"

        names = data[0].get("names", {})

        # 指定された言語の名前を取得
        if self.language in names:
            return names[self.language]

        # 指定された言語がない場合は英語を試行
        if "en" in names:
            return names["en"]

        # 英語もない場合はISO国コードを返す
        return f"Country {iso_code}"

    def get_all_countries(self):
        """指定された言語での全ての国の一覧を取得します。

        Returns:
            list: {'iso_code': int, 'name': str}の辞書のリスト
        """
        data = supabase_service.get_data(
            table="countries", columns=["iso_code", "names"]
        )

        countries = []
        for country_data in data:
            iso_code = country_data.get("iso_code")
            names = country_data.get("names", {})

            # 指定された言語の名前を取得
            if self.language in names:
                name = names[self.language]
            elif "en" in names:
                name = names["en"]
            else:
                name = f"Country {iso_code}"

            countries.append({"iso_code": iso_code, "name": name})

        return sorted(countries, key=lambda x: x["name"])

    def get_countries_with_coordinates(self):
        """座標データを持つ国の情報を指定された言語で取得します（地図作成用）。

        Returns:
            list: {'iso_code': int, 'name': str, 'latitude': float, 'longitude': float}の辞書のリスト
        """
        data = supabase_service.get_data(
            table="countries",
            columns=["iso_code", "names", "latitude", "longitude"],
            filters={"latitude__isnull": False, "longitude__isnull": False},
        )

        countries = []
        for country_data in data:
            iso_code = country_data.get("iso_code")
            names = country_data.get("names", {})
            latitude = country_data.get("latitude")
            longitude = country_data.get("longitude")

            # 指定された言語の名前を取得
            if self.language in names:
                name = names[self.language]
            elif "en" in names:
                name = names["en"]
            else:
                name = f"Country {iso_code}"

            countries.append(
                {
                    "iso_code": iso_code,
                    "name": name,
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                }
            )

        return countries

    def get_country_choices(self):
        """プルダウンリスト用の国選択肢を取得します。

        Returns:
            list: (iso_code, country_name)のタプルのリスト
        """
        countries = self.get_all_countries()
        return [(country["iso_code"], country["name"]) for country in countries]


class Country(models.Model):
    """国情報を管理するモデルクラス。

    このクラスは、GBB大会に参加する各国の基本情報を格納します。
    各国のISOコード、地理座標、多言語名称を管理します。

    Attributes:
        iso_code (int): ISO国コード。主キーとして設定されます。
        latitude (Decimal, optional): 緯度。最大8桁、小数点以下6桁。
        longitude (Decimal, optional): 経度。最大9桁、小数点以下6桁。
        names (JSONField): 多言語名称を格納するJSONフィールド。
            {'en': 'Japan', 'ja': '日本', ...} の形式で保存されます。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Example:
        >>> country = Country.objects.create(
        ...     iso_code=392,
        ...     latitude=35.6762,
        ...     longitude=139.6503,
        ...     names={'en': 'Japan', 'ja': '日本', 'ko': '일본'}
        ... )
        >>> country.get_name('ja')
        '日本'

    Note:
        - iso_codeフィールドは主キーとして設定されています
        - namesフィールドはJSONFieldを使用して多言語対応を実現しています
    """

    iso_code = models.IntegerField(primary_key=True, help_text="ISO国コード")
    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="緯度（地図表示用）",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="経度（地図表示用）",
    )
    names = JSONField(help_text="多言語名称 {en: 'Japan', ja: '日本', ...}")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "countries"
        indexes = [
            models.Index(fields=["iso_code"]),
        ]
        verbose_name = "国"
        verbose_name_plural = "国一覧"

    def __str__(self):
        return self.names.get("en", f"Country {self.iso_code}")

    @classmethod
    def for_language(cls, language="ja"):
        """指定された言語での国情報管理インスタンスを取得します。

        Args:
            language (str): 言語コード（'ja', 'en', 'ko' など）

        Returns:
            CountryManager: 指定された言語での国情報管理インスタンス

        Example:
            >>> # 日本語での国情報管理
            >>> ja_countries = Country.for_language('ja')
            >>> ja_countries.get_country_name(392)  # '日本'
            >>>
            >>> # 英語での国情報管理
            >>> en_countries = Country.for_language('en')
            >>> en_countries.get_country_name(392)  # 'Japan'
        """
        return CountryManager(language)

    def get_name(self, language="ja"):
        """指定された言語の国名を取得します。

        Args:
            language (str): 取得したい言語コード。デフォルトは'ja'。

        Returns:
            str: 指定された言語の国名。該当する言語がない場合は英語名を返します。
                英語名もない場合はISO国コードを返します。

        Example:
            >>> country = Country.objects.get(iso_code=392)
            >>> country.get_name('ja')
            '日本'
            >>> country.get_name('en')
            'Japan'
        """
        # Supabaseから国名データを取得
        data = supabase_service.get_data(
            table="countries",
            columns=["names"],
            filters={"iso_code": self.iso_code},
        )

        if not data:
            return f"Country {self.iso_code}"

        names = data[0].get("names", {}) if data else {}

        # 指定された言語の名前を取得
        if language in names:
            return names[language]

        # 指定された言語がない場合は英語を試行
        if "en" in names:
            return names["en"]

        # 英語もない場合はISO国コードを返す
        return f"Country {self.iso_code}"

    @property
    def coordinates(self):
        """緯度経度をタプルで取得します（地図作成用）。

        Returns:
            tuple: (latitude, longitude) または None（座標データがない場合）
        """
        # Supabaseから座標データを取得
        data = supabase_service.get_data(
            table="countries",
            columns=["latitude", "longitude"],
            filters={"iso_code": self.iso_code},
        )

        if not data:
            return None

        country_data = data[0]
        latitude = country_data.get("latitude")
        longitude = country_data.get("longitude")

        if latitude is not None and longitude is not None:
            return (float(latitude), float(longitude))
        return None

    def get_all_names(self):
        """利用可能な全ての言語の国名を取得します。

        Returns:
            dict: 言語コードをキー、国名を値とする辞書
        """
        # Supabaseから国名データを取得
        data = supabase_service.get_data(
            table="countries",
            columns=["names"],
            filters={"iso_code": self.iso_code},
        )

        if not data:
            return {}

        names = data[0].get("names", {})
        return names.copy() if names else {}

    @classmethod
    def get_all_countries_with_coordinates(cls):
        """座標データを持つ全ての国の情報を取得します（地図作成用）。

        Returns:
            list: 国の情報を含む辞書のリスト
                [{'iso_code': 392, 'names': {...}, 'latitude': 35.6762, 'longitude': 139.6503}, ...]
        """
        return supabase_service.get_data(
            table="countries",
            columns=["iso_code", "names", "latitude", "longitude"],
            filters={"latitude__isnull": False, "longitude__isnull": False},
        )

    @classmethod
    def get_country_choices(cls, language="ja"):
        """指定された言語での国名選択肢を取得します（プルダウンリスト用）。

        Args:
            language (str): 取得したい言語コード。デフォルトは'ja'。

        Returns:
            list: (iso_code, country_name)のタプルのリスト
        """
        data = supabase_service.get_data(
            table="countries", columns=["iso_code", "names"]
        )

        choices = []
        for country_data in data:
            iso_code = country_data.get("iso_code")
            names = country_data.get("names", {})

            # 指定された言語の名前を取得、なければ英語、それもなければISO国コード
            if language in names:
                name = names[language]
            elif "en" in names:
                name = names["en"]
            else:
                name = f"Country {iso_code}"

            choices.append((iso_code, name))

        return sorted(choices, key=lambda x: x[1])  # 国名でソート


class Year(models.Model):
    """GBB大会の年度を管理するモデルクラス。

    このクラスは、GBB大会の開催年度とその状態を管理します。
    各年度の開催状況（開催予定/終了）を追跡できます。

    Attributes:
        year (int): 大会開催年。主キーとして設定され、2013年以降の値のみ有効です。
        starts_at (DateTimeField): 開始日時 未定・中止の場合はnull
        ends_at (DateTimeField): 終了日時 未定・中止の場合はnull
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Example:
        >>> year = Year.objects.create(year=2024, starts_at='2024-01-01', ends_at='2024-01-02')
        >>> year
        GBB 2024
        >>> year.starts_at
        '2024-01-01'
        >>> year.ends_at
        '2024-01-02'

    Note:
        - yearフィールドは主キーとして設定されており、2013年以降の値のみ有効です
        - 年度は降順でソートされます（最新年度が上位に表示）
        - starts_atとends_atがnullの場合は開催前として扱う
        - ただし、yearを比較して過去の場合は中止として扱う
    """

    year = models.IntegerField(primary_key=True, validators=[MinValueValidator(2013)])
    starts_at = models.DateTimeField(
        null=True, blank=True, help_text="開始日時 未定・中止の場合はnull"
    )
    ends_at = models.DateTimeField(
        null=True, blank=True, help_text="終了日時 未定・中止の場合はnull"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "years"
        ordering = ["-year"]
        verbose_name = "年度"
        verbose_name_plural = "年度一覧"

    def __str__(self):
        return f"GBB {self.year}"


class Category(models.Model):
    """GBB大会のカテゴリを管理するモデルクラス。

    このクラスは、GBB大会の各種カテゴリ（Solo、Tag Team等）を管理します。
    各カテゴリの表示順序も制御できます。

    Attributes:
        name (str): カテゴリ名。事前定義された選択肢から選択します。
        display_order (int): 表示順序。0が最上位で、数値が大きいほど下位に表示されます。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Constants:
        CATEGORY_CHOICES: 利用可能なカテゴリの選択肢
            - 'Solo': ソロ部門
            - 'Tag Team': タッグチーム部門
            - 'Loopstation': ループステーション部門
            - 'Producer': プロデューサー部門
            - 'Crew': クルー部門
            - 'Tag Team Loopstation': タッグチームループステーション部門
            - 'U18': 18歳以下部門

    Example:
        >>> category = Category.objects.create(
        ...     name='Solo',
        ...     display_order=1
        ... )
        >>> category
        Solo

    Note:
        - nameフィールドには一意制約が設定されています
        - カテゴリはdisplay_order、nameの順でソートされます
    """

    CATEGORY_CHOICES = [
        ("Solo", "Solo"),
        ("Tag Team", "Tag Team"),
        ("Loopstation", "Loopstation"),
        ("Producer", "Producer"),
        ("Crew", "Crew"),
        ("Tag Team Loopstation", "Tag Team Loopstation"),
        ("U18", "U18"),
    ]

    name = models.CharField(max_length=50, unique=True, choices=CATEGORY_CHOICES)
    display_order = models.IntegerField(default=0, help_text="表示順序 0が最上位")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        ordering = ["display_order", "name"]
        verbose_name = "カテゴリ"
        verbose_name_plural = "カテゴリ一覧"

    def __str__(self):
        return self.name


class TicketClass(models.Model):
    """出場権クラスを管理するモデルクラス。

    このクラスは、GBB大会への出場権の種類と優先度を管理します。
    Seed出場権やWildcard出場権などの区別が可能です。

    Attributes:
        name (str): 出場権クラス名。一意の値として設定されます。
        priority (int): 優先度。0が最上位で、数値が大きいほど優先度が低くなります。
        is_wildcard (bool): Wildcard出場権かどうかのフラグ。
        is_gbb_seed (bool): GBB成績による出場権かどうかのフラグ。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Example:
        >>> seed = TicketClass.objects.create(
        ...     name='GBB Seed',
        ...     priority=0,
        ...     is_wildcard=False,
        ...     is_gbb_seed=True
        ... )
        >>> wildcard = TicketClass.objects.create(
        ...     name='Wildcard',
        ...     priority=10,
        ...     is_wildcard=True,
        ...     is_gbb_seed=False
        ... )

    Note:
        - nameフィールドには一意制約が設定されています
        - 出場権は優先度の降順、名前の昇順でソートされます
    """

    name = models.CharField(max_length=100, unique=True)
    priority = models.IntegerField(
        default=0, help_text="優先度 0が最上位 seedは0, wildcardは順位"
    )
    is_wildcard = models.BooleanField(default=False, help_text="Wildcard出場権")
    is_gbb_seed = models.BooleanField(default=False, help_text="GBB成績による出場権")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ticket_classes"
        ordering = ["-priority", "name"]
        verbose_name = "出場権"
        verbose_name_plural = "出場権一覧"

    def __str__(self):
        return self.name


class Participant(models.Model):
    """GBB大会の参加者を管理するモデルクラス。

    このクラスは、GBB大会に参加する個人またはチームの情報を管理します。
    参加者の基本情報、出場カテゴリ、出場権、所属国、キャンセル状況などを追跡できます。

    Attributes:
        name (str): 参加者名またはグループ名。
        year (ForeignKey): 参加年度。Yearモデルとの外部キー関係。
        category (ForeignKey): 参加カテゴリ。Categoryモデルとの外部キー関係。
        ticket_class (ForeignKey): 出場権クラス。TicketClassモデルとの外部キー関係。
        country (ForeignKey): 所属国。Countryモデルとの外部キー関係。
        is_cancelled (bool): キャンセルしたかどうかのフラグ。
        cancelled_at (DateTimeField, optional): キャンセル日時。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Properties:
        members_list: メンバーリストを表示順序で取得します。
        members_names: メンバー名をカンマ区切りで取得します。

    Example:
        >>> participant = Participant.objects.create(
        ...     name='Beatbox Crew',
        ...     year=year_2024,
        ...     category=solo_category,
        ...     ticket_class=seed_ticket,
        ...     country=japan
        ... )
        >>> participant.members_names
        'Member1, Member2, Member3'

    Note:
        - name、year、categoryの組み合わせで一意制約が設定されています
        - キャンセル時は自動的にcancelled_atが設定されます
        - 複数のインデックスが設定されており、検索パフォーマンスが最適化されています
    """

    name = models.CharField(max_length=100, help_text="参加者名（グループ名）")
    year = models.ForeignKey(Year, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    ticket_class = models.ForeignKey(TicketClass, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    is_cancelled = models.BooleanField(
        default=False, help_text="キャンセルしたかどうか"
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "participants"
        unique_together = ["name", "year", "category"]
        indexes = [
            models.Index(fields=["year"]),
            models.Index(fields=["category"]),
            models.Index(fields=["country"]),
            models.Index(fields=["name"]),
            models.Index(fields=["is_cancelled"]),
            models.Index(fields=["year", "category"]),
            models.Index(fields=["year", "country"]),
        ]
        verbose_name = "出場者"
        verbose_name_plural = "全出場者一覧"

    def __str__(self):
        return f"{self.name} ({self.year} {self.category})"

    @classmethod
    def for_language(cls, language="ja"):
        """指定された言語での出場者情報管理インスタンスを取得します。

        Args:
            language (str): 言語コード（'ja', 'en', 'ko' など）

        Returns:
            ParticipantManager: 指定された言語での出場者情報管理インスタンス

        Example:
            >>> # 日本語での出場者情報管理
            >>> ja_participants = Participant.for_language('ja')
            >>> participants_2024 = ja_participants.get_participants_by_year(2024)
            >>> # 出場者の国名が日本語で取得される
            >>>
            >>> # 英語での出場者情報管理
            >>> en_participants = Participant.for_language('en')
            >>> participants_solo = en_participants.get_participants_by_year_and_category(2024, 'Solo')
        """
        return ParticipantManager(language)

    def save(self, *args, **kwargs):
        """参加者情報を保存します。

        キャンセルフラグが変更された場合、自動的にcancelled_atフィールドを更新します。

        Args:
            *args: 位置引数
            **kwargs: キーワード引数
        """
        if self.is_cancelled and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        elif not self.is_cancelled:
            self.cancelled_at = None
        super().save(*args, **kwargs)

    @property
    def members_list(self):
        """メンバーリストを名前順で取得します。

        Returns:
            QuerySet: 名前順でソートされたメンバーのQuerySet。
        """
        return self.members.all().order_by("name")

    @property
    def members_names(self):
        """メンバー名をカンマ区切りで取得します。

        Returns:
            str: メンバー名をカンマ区切りで連結した文字列。
        """
        return ", ".join([member.name for member in self.members_list])


class ParticipantMember(models.Model):
    """参加者のメンバー情報を管理するモデルクラス（チーム戦用）。

    このクラスは、チーム戦で参加する場合の個別メンバー情報を管理します。
    各メンバーの名前と国籍を設定できます。

    Attributes:
        participant (ForeignKey): 所属する参加者。Participantモデルとの外部キー関係。
        name (str): メンバー名。
        country (ForeignKey): 所属国。Countryモデルとの外部キー関係。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Example:
        >>> member = ParticipantMember.objects.create(
        ...     participant=team_participant,
        ...     name='Member1',
        ...     country=japan
        ... )
        >>> member
        Member1 (Beatbox Crew)

    Note:
        - participantとnameの組み合わせで一意制約が設定されています
        - メンバーは名前でソートされます
    """

    participant = models.ForeignKey(
        Participant, related_name="members", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100, help_text="メンバー名")
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "participant_members"
        unique_together = ["participant", "name"]
        indexes = [
            models.Index(fields=["participant"]),
            models.Index(fields=["name"]),
            models.Index(fields=["country"]),
        ]
        ordering = ["name"]
        verbose_name = "チームメンバー"
        verbose_name_plural = "チームメンバー一覧"

    def __str__(self):
        return f"{self.name} ({self.participant.name})"


class TournamentResult(models.Model):
    """トーナメント形式の試合結果を管理するモデルクラス。

    このクラスは、トーナメント形式の競技における各試合の結果を記録します。
    勝者と敗者、ラウンド情報を管理できます。

    Attributes:
        year (ForeignKey): 大会年度。Yearモデルとの外部キー関係。
        category (ForeignKey): 競技カテゴリ。Categoryモデルとの外部キー関係。
        round (str): ラウンド名（例：'Final', 'Semi-Final', 'Quarter-Final'）。
        winner (ForeignKey): 勝者。Participantモデルとの外部キー関係。
        loser (ForeignKey): 敗者。Participantモデルとの外部キー関係。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Constants:
        ROUND_CHOICES: ラウンドの選択肢
            - 'Final': 決勝
            - 'Semi-Final': 準決勝
            - 'Small-Final': 3位決定戦
            - 'Quarter-Final': 準々決勝
            - 'Round 16': ベスト16

    Example:
        >>> result = TournamentResult.objects.create(
        ...     year=year_2024,
        ...     category=solo_category,
        ...     round='Final',
        ...     winner=participant1,
        ...     loser=participant2
        ... )
        >>> result
        Final: Beatboxer1 vs Beatboxer2

    Note:
        - year、category、round、winnerの組み合わせで一意制約が設定されています
        - 複数のインデックスが設定されており、検索パフォーマンスが最適化されています
    """

    ROUND_CHOICES = [
        ("Final", "決勝"),
        ("Semi-Final", "準決勝"),
        ("Small-Final", "3位決定戦"),
        ("Quarter-Final", "準々決勝"),
        ("Round 16", "ベスト16"),
    ]

    year = models.ForeignKey(Year, on_delete=models.CASCADE, help_text="大会年度")
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, help_text="競技カテゴリ"
    )
    round = models.CharField(
        max_length=30, choices=ROUND_CHOICES, help_text="ラウンド名"
    )
    winner = models.ForeignKey(
        Participant, related_name="wins", on_delete=models.CASCADE
    )
    loser = models.ForeignKey(
        Participant, related_name="losses", on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tournament_results"
        unique_together = ["year", "category", "round", "winner"]
        indexes = [
            models.Index(fields=["year"]),
            models.Index(fields=["category"]),
            models.Index(fields=["year", "category"]),
            models.Index(fields=["round"]),
            models.Index(fields=["winner"]),
            models.Index(fields=["loser"]),
        ]
        verbose_name = "トーナメント結果"
        verbose_name_plural = "トーナメント結果一覧"

    def __str__(self):
        return f"{self.year} {self.category} {self.get_round_display()}: {self.winner.name} vs {self.loser.name}"


class RankingResult(models.Model):
    """ランキング形式の競技結果を管理するモデルクラス。

    このクラスは、ランキング形式の競技における各参加者の順位を記録します。
    ラウンドごとの順位を管理できます。

    Attributes:
        year (ForeignKey): 大会年度。Yearモデルとの外部キー関係。
        category (ForeignKey): 競技カテゴリ。Categoryモデルとの外部キー関係。
        round (str): ラウンド名（例：'Day 1', 'Day 2', 'Total'）。
        participant (ForeignKey): 参加者。Participantモデルとの外部キー関係。
        rank (int): 順位。1以上の値。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Constants:
        ROUND_CHOICES: ラウンドの選択肢
            - 'Day 1': 1日目
            - 'Day 2': 2日目
            - 'Total': 総合結果

    Example:
        >>> result = RankingResult.objects.create(
        ...     year=year_2024,
        ...     category=producer_category,
        ...     round='Total',
        ...     participant=producer1,
        ...     rank=1
        ... )
        >>> result
        2024 Producer Total: 1位 Producer1

    Note:
        - year、category、round、participantの組み合わせで一意制約が設定されています
        - rankフィールドは1以上の値のみ有効です
    """

    ROUND_CHOICES = [
        ("Day 1", "1日目"),
        ("Day 2", "2日目"),
        ("Total", "総合結果"),
    ]

    year = models.ForeignKey(Year, on_delete=models.CASCADE, help_text="大会年度")
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, help_text="競技カテゴリ"
    )
    round = models.CharField(
        max_length=30, choices=ROUND_CHOICES, help_text="ラウンド名"
    )
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    rank = models.IntegerField(validators=[MinValueValidator(1)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ranking_results"
        unique_together = ["year", "category", "round", "participant"]
        indexes = [
            models.Index(fields=["year"]),
            models.Index(fields=["category"]),
            models.Index(fields=["year", "category"]),
            models.Index(fields=["round"]),
            models.Index(fields=["participant"]),
            models.Index(fields=["rank"]),
        ]
        verbose_name = "ランキング"
        verbose_name_plural = "ランキング一覧"

    def __str__(self):
        return f"{self.year} {self.category} {self.get_round_display()}: {self.rank}位 {self.participant.name}"


class TestData(models.Model):
    """Supabaseのtestテーブル用モデルクラス。

    このクラスは、Supabaseのtestテーブルとの連携を目的としたモデルです。
    Djangoのマイグレーション管理対象外として設定されており、
    Supabaseから直接データを取得・操作できます。

    Attributes:
        value (TextField): テキストデータ。
        created_at (DateTimeField): レコード作成日時。自動設定されます。

    Example:
        >>> test_data = TestData.get_test_data()
        >>> for data in test_data:
        ...     print(f"ID: {data['id']}, Value: {data['value']}")

    Note:
        - managed=Falseが設定されており、Djangoのマイグレーション管理対象外です
        - Supabaseとの連携にはsupabase_serviceを使用します
    """

    value = models.TextField(verbose_name="テキスト")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        verbose_name = "テストデータ"
        verbose_name_plural = "テストデータ"
        ordering = ["-created_at"]
        managed = False  # Djangoのマイグレーション管理対象外

    def __str__(self):
        return f"TestData {self.id}: {self.value[:50]}"

    @classmethod
    def get_all_data(cls):
        """Supabaseのtestテーブルから直接データを取得します。

        Returns:
            list: Supabaseから取得したデータのリスト。

        Example:
            >>> # 全データを取得
            >>> all_data = TestData.get_test_data()
            >>> # 特定の条件でフィルタリング
            >>> filtered_data = TestData.get_test_data(value__contains='test')
        """
        return supabase_service.get_data("test")
