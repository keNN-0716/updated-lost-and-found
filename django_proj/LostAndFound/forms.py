from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, LostItem, FoundItem, ClaimRequest


# Upload limits for item images
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']


def validate_image(image):
    """Shared server-side validation for item image uploads."""
    if image.size > MAX_IMAGE_SIZE:
        raise forms.ValidationError('Image must be 5 MB or smaller.')
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise forms.ValidationError('Only JPEG, PNG, GIF, or WebP images are allowed.')
    return image


class CustomLoginForm(forms.Form):
    id_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your ID number'})
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'})
    )


class CustomSignupForm(UserCreationForm):
    # Add an email field and make it required
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address'
        })
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Add email to the form, remove id_number
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_email(self):
        # Ensure the email is unique
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email


class LostItemForm(forms.ModelForm):
    class Meta:
        model = LostItem
        fields = ['name', 'description', 'date_lost', 'location_lost', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'date_lost': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'location_lost': forms.TextInput(attrs={'class': 'form-input'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            validate_image(image)
        return image


class FoundItemForm(forms.ModelForm):
    class Meta:
        model = FoundItem
        fields = ['name', 'description', 'date_found', 'location_found', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'date_found': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'location_found': forms.TextInput(attrs={'class': 'form-input'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            validate_image(image)
        return image
    
class ClaimRequestForm(forms.ModelForm):
    class Meta:
        model = ClaimRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'class': 'form-textarea', 
                'rows': 4, 
                'placeholder': 'Please provide proof of ownership, a detailed description, or distinguishing marks...'
            }),
        }