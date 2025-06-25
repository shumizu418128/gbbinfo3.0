from django.db import models

class DatabaseEntry(models.Model):
    """データベース管理用のサンプルモデル"""
    title = models.CharField(max_length=200, verbose_name='タイトル')
    description = models.TextField(blank=True, verbose_name='説明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    is_active = models.BooleanField(default=True, verbose_name='有効')

    class Meta:
        verbose_name = 'データベースエントリ'
        verbose_name_plural = 'データベースエントリ'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
