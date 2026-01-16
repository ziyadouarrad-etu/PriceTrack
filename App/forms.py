from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class UserRegisterForm(UserCreationForm):
    # We explicitly add the email field and make it required
    email = forms.EmailField(required=True, help_text="Required. Inform a valid email address.")

    class Meta:
        model = User
        # This defines the order of fields in the HTML form
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        """Ensure the email is unique in our database."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email