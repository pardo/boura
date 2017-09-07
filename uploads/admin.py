from django.contrib import admin
from django.utils.safestring import mark_safe

from sorl.thumbnail.admin import AdminImageMixin
from uploads.models import Upload, Entity


class EntityInlineAdmin(AdminImageMixin, admin.TabularInline):
    model = Entity
    fields = ["get_image", "type", "score"]
    readonly_fields = ["get_image", "type", "score"]
    extra = 0
    max_num = 0

    def get_image(self, obj):
        if obj.has_image():
            return mark_safe('<img src="%s">' % obj.image.url)
        return "No crop yet"

class UploadAdmin(AdminImageMixin, admin.ModelAdmin):
    actions = ["process_darknet"]
    readonly_fields = [
        "image",
        "get_image",
        "darknet_processing_start",
        "darknet_processing_end",
        "dlib_processing_start",
        "dlib_processing_end",
    ]
    inlines = [EntityInlineAdmin, ]

    def get_image(self, obj):
        return mark_safe('<img src="%s">' % obj.get_thumbnail().url)
    get_image.short_description = "Image"

    def process_darknet(self, request, queryset):
        from uploads.tasks import process_upload_with_darknet
        for upload in queryset.only("id"):
            process_upload_with_darknet.delay(upload.id)
    process_darknet.short_description = "Process with Darknet"

    def process_dlib(self, request, queryset):
        from uploads.tasks import process_upload_with_dlib
        for upload in queryset.only("id"):
            process_upload_with_dlib.delay(upload.id)
    process_darknet.short_description = "Process with dlib"


class EntityAdmin(AdminImageMixin, admin.ModelAdmin):
    pass

admin.site.register(Upload, UploadAdmin)
admin.site.register(Entity, EntityAdmin)