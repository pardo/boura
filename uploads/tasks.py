from django_rq import job


@job
def process_upload_with_dlib(upload_id):
    from uploads.models import Upload
    upload = Upload.objects.get(id=upload_id)
    upload.process_dlib()

@job
def process_upload_with_darknet(upload_id):
    from uploads.models import Upload
    upload = Upload.objects.get(id=upload_id)
    upload.process_darknet()