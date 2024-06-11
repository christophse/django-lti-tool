from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from jwcrypto import jwk


class KeyForm(forms.ModelForm):
    priv_key = forms.CharField(
        label="Private key",
        help_text=_(
            "Private key in <strong>PKCS#8 format</strong>. A new key "
            "will be generated if field is empty."
        ),
        required=False,
        widget=forms.widgets.Textarea(attrs={"cols": 67}),
    )

    pub_key = forms.CharField(
        label="Public key",
        help_text=_(
            "<strong>Read only.</strong> Will be generated after "
            "supplying a private key."
        ),
        required=False,
        widget=forms.widgets.Textarea(attrs={"cols": 67, "disabled": True}),
    )

    class Meta:
        fields = "__all__"
        exclude = ["_jwk"]

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance", None)
        if instance:
            kwargs["initial"] = {
                "priv_key": instance.pem(private=True),
                "pub_key": instance.pem(private=False),
            }
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data["priv_key"]:
            try:
                jwk.JWK().from_pem(bytes(cleaned_data["priv_key"], "ascii"))
            except ValueError:
                raise ValidationError(
                    {
                        "priv_key": _(
                            "Not a valid key. Please provide a key in " "PKCS#8 format."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.instance.jwk = self.cleaned_data["priv_key"]
        return super().save(*args, **kwargs)
