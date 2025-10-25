from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class HealthData(models.Model):
    # id field is automatically created by Django as primary key
    id = models.AutoField(primary_key=True)
    userId = models.CharField(max_length=64, help_text="ID of the user")
    timestamp = models.DateTimeField()
    type = models.CharField(max_length=32, help_text="Step count or HR")
    value = models.IntegerField(help_text="3-digit heart rate value")

    def __str__(self):
        return f"User {self.userId} at {self.timestamp}"

    class Meta:
        ordering = ["-timestamp"]


class EmotionData(models.Model):
    # id field is automatically created by Django as primary key
    id = models.AutoField(primary_key=True)
    userId = models.CharField(max_length=64, help_text="ID of the user")
    timestamp = models.DateTimeField()
    valence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        help_text="Valence value (0-5 range)",
    )
    arousal = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        help_text="Arousal value (0-5 range)",
    )
    type = models.CharField(
        max_length=32,
        default="periodic",
        help_text="Type of emotion data (e.g., 'periodic', 'opportune')",
    )

    def __str__(self):
        return f"User {self.userId}'s emotion data at {self.timestamp}"

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Emotion Data"
        verbose_name_plural = "Emotion Data"
