from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from datetime import date, datetime, time
from .models import User, PickupRequest, WasteCategory
import re

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'address', 'role', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['username'].help_text = 'Required. Letters and special characters only (no digits allowed).'

    def clean_username(self):
        username = self.cleaned_data['username']
        
        # Remove all digits from the username
        username_no_digits = ''.join([c for c in username if not c.isdigit()])
        
        # Check if username still has characters after removing digits
        if not username_no_digits:
            raise ValidationError("Username must contain at least one non-digit character.")
            
        # Check for minimum length after digit removal
        if len(username_no_digits) < 2:
            raise ValidationError("Username must have at least 2 characters (excluding digits).")
            
        return username_no_digits

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.address = self.cleaned_data['address']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user

# Keep your other forms unchanged...
class PickupRequestForm(forms.ModelForm):
    # ... rest of your existing form code
    pass

class CollectorUpdateForm(forms.ModelForm):
    # ... rest of your existing form code  
    pass
