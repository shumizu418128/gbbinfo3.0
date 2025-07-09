from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


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

    @property
    def has_coordinates(self):
        """座標データを持っているかどうかを判定します。"""
        return self.latitude is not None and self.longitude is not None


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

    Note:
        - name、year、categoryの組み合わせで一意制約が設定されています
        - キャンセル時は自動的にcancelled_atが設定されます
        - メンバー情報は members 関連マネージャーでアクセス可能です
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

    def save(self, *args, **kwargs):
        """参加者情報を保存します。

        キャンセルフラグの変更に応じてcancelled_atフィールドを自動設定します。
        これはデータ整合性を保つためのモデル層の責務です。
        """
        if self.is_cancelled and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        elif not self.is_cancelled:
            self.cancelled_at = None
        super().save(*args, **kwargs)


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
