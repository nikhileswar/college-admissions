from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import StudentProfile, Branch


class StudentSignupForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'First name', 'autocomplete': 'given-name'})
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Last name (optional)', 'autocomplete': 'family-name'})
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Choose a username', 'autocomplete': 'username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Create a password', 'autocomplete': 'new-password'})
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repeat password', 'autocomplete': 'new-password'})
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data.get('last_name', ''),
        )
        profile = StudentProfile.objects.create(
            user=user,
            has_submitted=False,
        )
        # Auto-populate preferences with all branches in default order
        from .models import Preference, Branch
        for i, branch in enumerate(Branch.objects.all(), start=1):
            Preference.objects.create(student=profile, branch=branch, rank=i)
        return user, profile


class StudentLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Your username', 'autocomplete': 'username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Your password', 'autocomplete': 'current-password'})
    )


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['college', 'branch', 'seats']
        widgets = {
            'college': forms.TextInput(attrs={'placeholder': 'e.g. IIT Bombay'}),
            'branch': forms.TextInput(attrs={'placeholder': 'e.g. Computer Science & Engg'}),
            'seats': forms.NumberInput(attrs={'min': 1, 'max': 500}),
        }

    def clean(self):
        cleaned = super().clean()
        college = cleaned.get('college', '').strip()
        branch = cleaned.get('branch', '').strip()
        qs = Branch.objects.filter(college__iexact=college, branch__iexact=branch)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'"{college} — {branch}" already exists.')
        return cleaned


class AdminStudentForm(forms.Form):
    """Admin adding a student manually."""
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'First name'}))
    last_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': 'Last name'}))
    air_rank = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'placeholder': 'AIR rank'}))
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(initial='jee2025', widget=forms.TextInput(attrs={'placeholder': 'jee2025'}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already taken.')
        return username

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data.get('last_name', ''),
        )
        profile = StudentProfile.objects.create(
            user=user,
            air_rank=data['air_rank'],
        )
        from .models import Preference, Branch
        for i, branch in enumerate(Branch.objects.all(), start=1):
            Preference.objects.create(student=profile, branch=branch, rank=i)
        return user, profile


class AdminStudentRankForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.select_related('user').order_by('user__first_name', 'user__last_name', 'user__username'),
        empty_label='Select a student',
    )
    air_rank = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'placeholder': 'AIR rank'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].label_from_instance = lambda p: p.user.get_full_name() or p.user.username
