from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .supabase_client import supabase_service


class Country(models.Model):
    """国情報を管理するモデルクラス。

    このクラスは、GBB大会に参加する各国の基本情報を格納します。
    各国のISOコード、地理座標、多言語名称を管理します。

    Attributes:
        iso_code (int): ISO国コード。一意の値として設定されます。
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
        - iso_codeフィールドには一意制約が設定されています
        - namesフィールドはJSONFieldを使用して多言語対応を実現しています
    """

    iso_code = models.IntegerField(unique=True, help_text="ISO国コード")
    latitude = models.DecimalField(
        max_digits=8, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
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

    def get_name(self, language="ja"):
        """指定された言語の国名を取得します。

        Args:
            language (str): 取得したい言語コード。デフォルトは'ja'。

        Returns:
            str: 指定された言語の国名。該当する言語がない場合は英語名を返します。
                英語名もない場合は空文字列を返します。

        Example:
            >>> country = Country.objects.get(iso_code=392)
            >>> country.get_name('ja')
            '日本'
            >>> country.get_name('en')
            'Japan'
        """
        return self.names.get(language, self.names.get("en", ""))


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
        """メンバーリストを表示順序で取得します。

        Returns:
            QuerySet: 表示順序でソートされたメンバーのQuerySet。
        """
        return self.members.all().order_by("display_order")

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
    各メンバーの名前と表示順序を設定できます。

    Attributes:
        participant (ForeignKey): 所属する参加者。Participantモデルとの外部キー関係。
        name (str): メンバー名。
        display_order (int): 表示順序。デフォルトは1。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Example:
        >>> member = ParticipantMember.objects.create(
        ...     participant=team_participant,
        ...     name='Member1',
        ...     display_order=1
        ... )
        >>> member
        Member1 (Beatbox Crew)

    Note:
        - participantとnameの組み合わせで一意制約が設定されています
        - メンバーはdisplay_orderでソートされます
    """

    participant = models.ForeignKey(
        Participant, related_name="members", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100, help_text="メンバー名")
    display_order = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "participant_members"
        unique_together = ["participant", "name"]
        indexes = [
            models.Index(fields=["participant"]),
            models.Index(fields=["name"]),
        ]
        ordering = ["display_order"]
        verbose_name = "チームメンバー"
        verbose_name_plural = "チームメンバー一覧"

    def __str__(self):
        return f"{self.name} ({self.participant.name})"


class CompetitionRule(models.Model):
    """GBB大会の競技形式を管理するモデルクラス。

    このクラスは、各年度・カテゴリにおける競技形式（トーナメント/ランキング）を管理します。

    Attributes:
        year (ForeignKey): 大会年度。Yearモデルとの外部キー関係。
        category (ForeignKey): 競技カテゴリ。Categoryモデルとの外部キー関係。
        format (str): 競技形式。'tournament'（トーナメント）または'ranking'（ランキング）。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Constants:
        FORMAT_CHOICES: 競技形式の選択肢
            - 'tournament': トーナメント形式
            - 'ranking': ランキング形式

    Example:
        >>> competition = Competition.objects.create(
        ...     year=year_2024,
        ...     category=solo_category,
        ...     format='tournament'
        ... )
        >>> competition
        2024 Solo (トーナメント)

    Note:
        - yearとcategoryの組み合わせで一意制約が設定されています
    """

    FORMAT_CHOICES = [
        ("tournament", "トーナメント"),
        ("ranking", "ランキング"),
    ]

    year = models.ForeignKey(Year, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "competitions"
        unique_together = ["year", "category"]
        indexes = [
            models.Index(fields=["year"]),
            models.Index(fields=["category"]),
        ]
        verbose_name = "形式"
        verbose_name_plural = "形式一覧"

    def __str__(self):
        return f"{self.year} {self.category} ({self.get_format_display()})"


class TournamentResult(models.Model):
    """トーナメント形式の試合結果を管理するモデルクラス。

    このクラスは、トーナメント形式の競技における各試合の結果を記録します。
    勝者と敗者、ラウンド情報を管理できます。

    Attributes:
        competition (ForeignKey): 所属する競技。Competitionモデルとの外部キー関係。
        round (str): ラウンド名（例：'Final', 'Semi-Final', 'Quarter-Final'）。
        winner (ForeignKey): 勝者。Participantモデルとの外部キー関係。
        loser (ForeignKey): 敗者。Participantモデルとの外部キー関係。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Example:
        >>> result = TournamentResult.objects.create(
        ...     competition_rule=solo_competition_rule,
        ...     round='Final',
        ...     winner=participant1,
        ...     loser=participant2
        ... )
        >>> result
        Final: Beatboxer1 vs Beatboxer2

    Note:
        - 複数のインデックスが設定されており、検索パフォーマンスが最適化されています
    """

    competition_rule = models.ForeignKey(
        CompetitionRule, related_name="tournament_results", on_delete=models.CASCADE
    )
    round = models.CharField(max_length=50, help_text="ラウンド名")
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
        indexes = [
            models.Index(fields=["competition_rule"]),
            models.Index(fields=["round"]),
            models.Index(fields=["winner"]),
            models.Index(fields=["loser"]),
        ]
        verbose_name = "トーナメント結果"
        verbose_name_plural = "トーナメント結果一覧"

    def __str__(self):
        return f"{self.round}: {self.winner.name} vs {self.loser.name}"


class RankingResult(models.Model):
    """ランキング形式の競技結果を管理するモデルクラス。

    このクラスは、ランキング形式の競技における各参加者の順位を記録します。
    ラウンドごとの順位を管理できます。

    Attributes:
        competition_rule (ForeignKey): 所属する競技。CompetitionRuleモデルとの外部キー関係。
        round (str): ラウンド名（例：'Final', 'Semi-Final'）。
        participant (ForeignKey): 参加者。Participantモデルとの外部キー関係。
        rank (int): 順位。1以上の値。
        created_at (DateTimeField): レコード作成日時。自動設定されます。
        updated_at (DateTimeField): レコード更新日時。自動更新されます。

    Example:
        >>> result = RankingResult.objects.create(
        ...     competition_rule=producer_competition_rule,
        ...     round='Final',
        ...     participant=producer1,
        ...     rank=1
        ... )
        >>> result
        Final: 1位 Producer1

    Note:
        - competition、round、participantの組み合わせで一意制約が設定されています
        - rankフィールドは1以上の値のみ有効です
    """

    competition_rule = models.ForeignKey(
        CompetitionRule, related_name="ranking_results", on_delete=models.CASCADE
    )
    round = models.CharField(max_length=50, help_text="ラウンド名")
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    rank = models.IntegerField(validators=[MinValueValidator(1)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ranking_results"
        unique_together = ["competition_rule", "round", "participant"]
        indexes = [
            models.Index(fields=["competition_rule"]),
            models.Index(fields=["round"]),
            models.Index(fields=["participant"]),
            models.Index(fields=["rank"]),
        ]
        verbose_name = "ランキング"
        verbose_name_plural = "ランキング一覧"

    def __str__(self):
        return f"{self.round}: {self.rank}位 {self.participant.name}"


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
    def get_all_data(cls, **filters):
        """Supabaseのtestテーブルから直接データを取得します。

        Args:
            **filters: フィルタリング条件。Supabaseのクエリパラメータとして使用されます。

        Returns:
            list: Supabaseから取得したデータのリスト。

        Example:
            >>> # 全データを取得
            >>> all_data = TestData.get_test_data()
            >>> # 特定の条件でフィルタリング
            >>> filtered_data = TestData.get_test_data(value__contains='test')
        """
        return supabase_service.get_all_data("test", **filters)
