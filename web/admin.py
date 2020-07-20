from django.contrib import admin

from .models import FailedGameUpload


@admin.register(FailedGameUpload)
class FailedGameUploadAdmin(admin.ModelAdmin):
    pass
