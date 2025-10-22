from django.db import models


class UploadedJSON(models.Model):
    # id field is automatically created by Django as primary key
    id = models.AutoField(primary_key=True)
    userId = models.IntegerField(help_text="ID of the user")
    timestamp = models.DateTimeField()
    hr = models.IntegerField(help_text="3-digit heart rate value")

    def __str__(self):
        return f"User {self.userId} at {self.timestamp}"

    class Meta:
        ordering = ["-timestamp"]
