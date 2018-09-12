from django_rq import job


@job
def process_upload_with_dlib(upload_id, force=False):
    from uploads.models import Upload
    upload = Upload.objects.get(id=upload_id)
    upload.process_dlib(force=force)

@job
def process_upload_with_darknet(upload_id, force=False):
    from uploads.models import Upload
    upload = Upload.objects.get(id=upload_id)
    upload.process_darknet(force=force)

@job
def crop_upload_entities(upload_id, force=False):
    from uploads.models import Upload
    upload = Upload.objects.get(id=upload_id)
    for entity in upload.entity_set.all():
        entity.crop(force=force)