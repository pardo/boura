import json

from django.http.response import HttpResponse
from django.shortcuts import render

from django.views.decorators.csrf import csrf_exempt

from uploads.forms import UploadForm
from uploads.models import Upload
from uploads.tasks import process_upload_with_dlib, process_upload_with_darknet


@csrf_exempt
def upload_image(request):
    if request.method == "POST":
        form = UploadForm(files=request.FILES)
        if form.is_valid():
            upload = form.save()
            if request.POST.get("dlib"):
                process_upload_with_dlib.delay(upload.id)
            if request.POST.get("darknet"):
                process_upload_with_darknet.delay(upload.id)
    return HttpResponse(json.dumps({
        "id": upload.id
    }), content_type="application/json", status=200)


def upload_view(request):
    try:
        if "upload" in request.GET:
            upload = Upload.objects.get(id=request.GET.get("upload"))
        else:
            upload = Upload.objects.latest("id")
    except:
        return HttpResponse(status=404)

    entities = []
    for e in upload.entity_set.all():
        data = {
            "type": e.type,
            "score": e.score,
            "top": e.top,
            "right": e.right,
            "bottom": e.bottom,
            "left": e.left,
        }

        if e.type == "face":
            data["landmark_68"] = e.meta["landmark_68"]

        entities.append(data)

    return render(request, "base.html", {
        'upload': upload,
        'entities': json.dumps(entities)
    })