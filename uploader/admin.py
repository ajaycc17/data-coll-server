from django.contrib import admin
from .models import HealthData, EmotionData

# Register your models here.
admin.site.register(HealthData)
admin.site.register(EmotionData)
