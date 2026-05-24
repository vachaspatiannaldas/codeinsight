import uuid

from django.db import models


class Review(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    repository_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    pr_number = models.IntegerField(
        blank=True,
        null=True
    )

    diff_content = models.TextField()

    ai_response = models.JSONField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.repository_name} - PR {self.pr_number}"