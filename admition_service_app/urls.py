from django.urls import path

from admition_service_app.views import AdmissionWizard, HomePageView

from .forms import (CollegeSelectionForm, ConfirmationForm,
                    EngineeringScoresForm, InterestedDepartmentsForm,
                    PersonalInfoForm, PharmacyScoresForm)

urlpatterns = [
    # Define your URL patterns here
    path("", HomePageView.as_view(), name="home"),
    path(
        "apply/",
        AdmissionWizard.as_view(
            [
                PersonalInfoForm,
                CollegeSelectionForm,
                InterestedDepartmentsForm,
                EngineeringScoresForm,
                ConfirmationForm,  # Assuming you have a ConfirmationForm for the final step
            ]
        ),
        name="admission_apply",
    ),
]
