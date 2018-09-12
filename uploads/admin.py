from __future__ import absolute_import

from django.contrib import admin
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect

from sorl.thumbnail.admin import AdminImageMixin
from uploads.models import Upload, Entity
from inline_actions.admin import InlineActionsMixin, InlineActionsModelAdminMixin


class EntityInlineAdmin(AdminImageMixin, InlineActionsMixin, admin.TabularInline):
    model = Entity
    fields = ["get_image", "type", "score"]
    readonly_fields = ["get_image", "type", "score"]
    extra = 0
    max_num = 0
    can_delete = False
    inline_actions = []

    def get_inline_actions(self, request, obj=None):
        actions = [
            "inline_create_crop"
        ]
        if obj.type == "face":
            actions.append('inline_create_identity')
        return actions

    def inline_create_crop(self, request, obj, parent_obj=None):
        obj.crop(force=True)
    inline_create_crop.short_description = "Crop"

    def inline_create_identity(self, request, obj, parent_obj=None):
        from identity.models import Identity
        i = Identity()
        i.save()
        i.identity.add(obj)
        return HttpResponseRedirect(i.get_admin_change_url())
    inline_create_identity.short_description = "Create Identity"

    def get_image(self, obj):
        if obj.has_image():
            return mark_safe('<img style="max-width: 150px" src="%s">' % obj.image.url)
        return "No crop yet"


class UploadAdmin(AdminImageMixin, InlineActionsModelAdminMixin, admin.ModelAdmin):
    actions = [
        "process_darknet",
        "process_dlib",
        "do_cropping",
        "delete_with_images"
    ]
    list_display = [
        "date_added",
        "get_number_of_entities",
        "render_inline_actions",
        "view_url",
    ]
    fields = [
        "image",
        "view_url",
        "darknet_processing_start",
        "darknet_processing_end",
        "dlib_processing_start",
        "dlib_processing_end",
        "render_inline_actions"
    ]
    readonly_fields = [
        "image",
        "view_url",
        "darknet_processing_start",
        "darknet_processing_end",
        "dlib_processing_start",
        "dlib_processing_end",
        "render_inline_actions"
    ]
    inlines = [EntityInlineAdmin, ]
    inline_actions = [
        "inline_create_crop",
        "inline_process_darknet",
        "inline_process_dlib"
    ]
    
    def view_url(self, obj):
        return mark_safe('<a target="_blank" href="%s"><img style="max-width: 150px" src="%s"><a>' % (
            obj.get_view_url(), obj.get_thumbnail().url 
        ))
    view_url.short_description = "View Image On Site"

    def get_number_of_entities(self, obj):
        return obj.number_of_entities
    get_number_of_entities.short_description = "Entities count"

    # actions
    def delete_with_images(self, request, queryset):
        for e in queryset:
            e.image.delete()
        queryset.delete()
    delete_with_images.short_description = "Delete along images"

    def process_darknet(self, request, queryset):
        from uploads.tasks import process_upload_with_darknet
        for upload in queryset.only("id"):
            process_upload_with_darknet.delay(upload.id)
    process_darknet.short_description = "Process with Darknet"

    def process_dlib(self, request, queryset):
        from uploads.tasks import process_upload_with_dlib
        for upload in queryset.only("id"):
            process_upload_with_dlib.delay(upload.id)
    process_dlib.short_description = "Process with dlib"

    def do_cropping(self, request, queryset):
        from uploads.tasks import crop_upload_entities
        for upload in queryset:
            crop_upload_entities.delay(upload.id)
    do_cropping.short_description = "Crop entities"

    # inline actions
    def inline_create_crop(self, request, obj, parent_obj=None):
        for entity in obj.entity_set.all():
            entity.crop()
    inline_create_crop.short_description = "Crop"

    def inline_process_darknet(self, request, obj, parent_obj=None):
        from uploads.tasks import process_upload_with_darknet
        process_upload_with_darknet.delay(obj.id, True)
    inline_process_darknet.short_description = "Process with Darknet"

    def inline_process_dlib(self, request, obj, parent_obj=None):
        from uploads.tasks import process_upload_with_dlib
        process_upload_with_dlib.delay(obj.id, True)
    inline_process_dlib.short_description = "Process with dlib"




class EntityAdmin(AdminImageMixin, admin.ModelAdmin):
    list_filter = ["type"]
    list_display = [
        "type",
        "get_image",
        "view_url",
    ]
    fields = [
        "type",
        "score",
        "get_admin_change_url",
        "get_image",
        "view_url",
    ]
    readonly_fields = [
        "get_image",
        "view_url",
        "get_admin_change_url"
    ]
    actions = [
        "crop",
        "delete_with_images"
    ]

    def get_admin_change_url(self, obj):
        return mark_safe('<a href="%s">Change Upload<a>' % (
            obj.upload.get_admin_change_url() 
        ))

    def view_url(self, obj):
        return mark_safe('<a target="_blank" href="%s"><img style="max-width: 150px" src="%s"><a>' % (
            obj.upload.get_view_url(), obj.upload.get_thumbnail().url 
        ))
    view_url.short_description = "View Image On Site"

    def get_image(self, obj):
        if obj.has_image():
            return mark_safe('<img style="max-width: 150px" src="%s">' % obj.image.url)

    # actions 
    def delete_with_images(self, request, queryset):
        for e in queryset:
            e.image.delete()
        queryset.delete()

    def crop(self, request, queryset):
        for entity in queryset:
            entity.crop()
    crop.short_description = "Crop entities"

admin.site.register(Upload, UploadAdmin)
admin.site.register(Entity, EntityAdmin)