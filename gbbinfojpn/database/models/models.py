from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .supabase_client import supabase_service


class Country(models.Model):
    """国情報テーブル"""

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
        """指定された言語の国名を取得"""
        return self.names.get(language, self.names.get("en", ""))


class Year(models.Model):
    """年度管理テーブル"""

    STATUS_CHOICES = [
        ("upcoming", "開催予定"),
        ("completed", "終了"),
    ]

    year = models.IntegerField(primary_key=True, validators=[MinValueValidator(2013)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="upcoming")

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
    """カテゴリテーブル"""
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
    """出場権クラステーブル"""

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
    """参加者テーブル"""

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
        if self.is_cancelled and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        elif not self.is_cancelled:
            self.cancelled_at = None
        super().save(*args, **kwargs)

    @property
    def members_list(self):
        """メンバーリストを取得"""
        return self.members.all().order_by("display_order")

    @property
    def members_names(self):
        """メンバー名をカンマ区切りで取得"""
        return ", ".join([member.name for member in self.members_list])


class ParticipantMember(models.Model):
    """参加者メンバーテーブル（チーム戦用）"""

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


class Competition(models.Model):
    """大会テーブル"""

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
    """トーナメント結果テーブル"""

    competition = models.ForeignKey(
        Competition, related_name="tournament_results", on_delete=models.CASCADE
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
            models.Index(fields=["competition"]),
            models.Index(fields=["round"]),
            models.Index(fields=["winner"]),
            models.Index(fields=["loser"]),
        ]
        verbose_name = "トーナメント結果"
        verbose_name_plural = "トーナメント結果一覧"

    def __str__(self):
        return f"{self.round}: {self.winner.name} vs {self.loser.name}"


class RankingResult(models.Model):
    """ランキング結果テーブル"""

    competition = models.ForeignKey(
        Competition, related_name="ranking_results", on_delete=models.CASCADE
    )
    round = models.CharField(max_length=50, help_text="ラウンド名")
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    rank = models.IntegerField(validators=[MinValueValidator(1)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ranking_results"
        unique_together = ["competition", "round", "participant"]
        indexes = [
            models.Index(fields=["competition"]),
            models.Index(fields=["round"]),
            models.Index(fields=["participant"]),
            models.Index(fields=["rank"]),
        ]
        verbose_name = "ランキング"
        verbose_name_plural = "ランキング一覧"

    def __str__(self):
        return f"{self.round}: {self.rank}位 {self.participant.name}"


class TestData(models.Model):
    """
    Supabaseのtestテーブル用モデル
    id, created_at, valueフィールドを持つ
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
    def get_test_data(cls, **filters):
        """Supabaseのtestテーブルから直接データを取得"""
        return supabase_service.get_table_data("test", **filters)
