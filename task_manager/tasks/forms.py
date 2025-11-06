from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Task, EmailTemplate
import datetime

# ✅ Custom User Creation Form
class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[(key, value) for key, value in CustomUser.ROLE_CHOICES if key.lower() != 'admin']
    )

    class Meta:
        model = CustomUser
        fields = ("username", "email", "role", "password1", "password2")


# ✅ Task Form with Email Template + Recipient Dropdown & (Me) option
class TaskForm(forms.ModelForm):
    sender = forms.ModelChoiceField(
        queryset=CustomUser.objects.all(),
        required=False,  # optional for editing tasks
        empty_label="-- Select Sender --",
        help_text="Who is sending the email?"
    )

    recipients = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 5}),
        help_text="Select one or more users to assign the task. (Me) will be available for admin/hod/supervisor."
    )

    email_template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.none(),
        required=False,
        empty_label="-- Select an Email Template --",
        help_text="Choose a premade email message for notifications."
    )

    due_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        required=False
    )

    class Meta:
        model = Task
        fields = ["title", "description", "due_date", "completed", "sender", "recipients", "email_template"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # pass request.user when initializing form
        super(TaskForm, self).__init__(*args, **kwargs)

        # Populate email templates dynamically
        self.fields['email_template'].queryset = EmailTemplate.objects.all()

        # Populate recipients dropdown
        qs = CustomUser.objects.all()
        if user and user.role in ["admin", "hod", "supervisor"]:
            # Add (Me) label for current user
            choices = [(u.pk, f"{u.username}{' (Me)' if u == user else ''}") for u in qs]
        else:
            choices = [(u.pk, u.username) for u in qs]

        self.fields['recipients'].queryset = qs
        self.fields['recipients'].choices = choices

        # Set initial due_date for existing tasks
        if self.instance and self.instance.pk and self.instance.due_date:
            self.fields['due_date'].initial = self.instance.due_date.strftime("%Y-%m-%d")

    def clean_due_date(self):
        due_date = self.cleaned_data.get("due_date")
        # Only block past dates for new tasks
        if due_date and not self.instance.pk and due_date < datetime.date.today():
            raise forms.ValidationError("Due date cannot be in the past for new tasks.")
        # Existing tasks can have any date (past or future)
        return due_date
