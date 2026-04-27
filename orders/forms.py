from django import forms

from .models import Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'full_name',
            'email',
            'phone',
            'address',
            'district',
            'payment_method',
            'sms_opt_in',
            'notes',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-lg'}),
            'phone': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'district': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'payment_method': forms.RadioSelect(),
            'sms_opt_in': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        self.fields['phone'].required = False
        self.fields['notes'].required = False
        self.fields['phone'].help_text = "Optional. Add a phone number if you want SMS order updates."

    def clean_phone(self):
        phone = ''.join(ch for ch in (self.cleaned_data.get('phone') or '') if ch.isdigit())
        if not phone:
            return ''
        if len(phone) < 10:
            raise forms.ValidationError("Enter a valid phone number with at least 10 digits.")
        return phone
