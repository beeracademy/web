import base64
from io import BytesIO

from django import forms
from django.contrib.auth.password_validation import (
    get_default_password_validators,
    validate_password,
)
from PIL import Image

from games.models import User

validators_help_text = "<br>".join(
    [v.get_help_text() for v in get_default_password_validators()]
)


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "new_password",
            "new_image_data_url",
            "image_deleted",
        ]

    new_password = forms.CharField(
        widget=forms.PasswordInput, required=False, help_text=validators_help_text
    )
    new_image_data_url = forms.CharField(required=False)
    image_deleted = forms.BooleanField(required=False)

    def clean_new_image_data_url(self):
        data_url = self.cleaned_data["new_image_data_url"]
        if not data_url:
            self.cleaned_data["image_io"] = None
            return

        parts = data_url.split("base64,", maxsplit=1)
        if len(parts) != 2:
            raise forms.ValidationError("Invalid data url")

        try:
            data = base64.b64decode(parts[1])
        except:
            raise forms.ValidationError("Invalid base64 data")

        bytes_io = BytesIO(data)
        try:
            image = Image.open(bytes_io)
            image.verify()
        except:
            raise forms.ValidationError("Invalid image")

        bytes_io.seek(0)
        self.cleaned_data["image_io"] = bytes_io

    def clean_new_password(self):
        password = self.cleaned_data["new_password"]
        if password:
            validate_password(password, self.instance)

        return password
