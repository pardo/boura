from django import forms

from uploads.models import Upload


class UploadForm(forms.ModelForm):
    class Meta:
        model = Upload
        fields = ["image"]
