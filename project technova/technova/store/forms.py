from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["full_name", "phone", "city", "address", "note"]
        labels = {
            "full_name": "Full name",
            "phone": "Phone number",
            "city": "City",
            "address": "Delivery address",
            "note": "Note for the courier (optional)",
        }
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}
