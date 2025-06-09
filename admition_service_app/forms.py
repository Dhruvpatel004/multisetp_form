from django import forms
from .models import AdmissionApplication , College, Department

#  Step 1: Personal Information Form

class PersonalInfoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        show_otp = kwargs.pop('show_otp', False)
        otp_verified = kwargs.pop('otp_verified', False)
        super().__init__(*args, **kwargs)

        if otp_verified:
            # If OTP is already verified, do not show OTP field
            print("OTP already verified, not showing OTP field")
            if 'otp' in self.fields:
                self.fields.pop('otp')
        elif show_otp:
            # Show OTP field if OTP was sent but not verified yet
            self.fields['otp'] = forms.CharField(
                label="OTP",
                max_length=6,
                required=True,
                widget=forms.TextInput(attrs={'placeholder': 'Enter OTP'})
            )
        else:
            # Hide OTP field if OTP not sent yet
            if 'otp' in self.fields:
                self.fields.pop('otp')

    class Meta:
        model = AdmissionApplication
        fields = ['first_name', 'last_name', 'email', 'mobile']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
            'mobile': forms.TextInput(attrs={'placeholder': 'Phone Number'}),
        }

    class Meta:
        model = AdmissionApplication
        fields = ['first_name', 'last_name', 'email', 'mobile']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
            'mobile': forms.TextInput(attrs={'placeholder': 'Phone Number'}),
        }

#  Step 2: College Selection Form
class CollegeSelectionForm(forms.ModelForm):
    class Meta:
        model = AdmissionApplication
        fields = ['college']
        widgets = {
            'college': forms.Select(attrs={'class': 'form-control'}),
        }

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields['college'].queryset = College.objects.all()

# Step 3: Select Interested Departments Form
class InterestedDepartmentsForm(forms.ModelForm):
    interested_departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.none(),  # initially empty, will filter dynamically
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = AdmissionApplication
        fields = ['interested_departments']

    def __init__(self, *args, **kwargs):
        college = kwargs.pop('college', None)
        super().__init__(*args, **kwargs)
        if college:
            self.fields['interested_departments'].queryset = Department.objects.filter(college=college)
        else:
            self.fields['interested_departments'].queryset = Department.objects.none()

# Step 4: Additional Information Form
# Step 4a: Engineering Entrance Exam Scores Form
class EngineeringScoresForm(forms.ModelForm):
    class Meta:
        model = AdmissionApplication
        fields = ['jee_main_score', 'math_score', 'physics_score', 'chemistry_score']


# Step 4b: Pharmacy Entrance Exam Scores Form
class PharmacyScoresForm(forms.ModelForm):
    class Meta:
        model = AdmissionApplication
        fields = ['neet_score', 'biology_score', 'physics_score', 'chemistry_score']

# Step 5: Summary Form
class ConfirmationForm(forms.Form):
    pass