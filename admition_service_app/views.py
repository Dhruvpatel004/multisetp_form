from django.shortcuts import render
from django.views.generic import TemplateView
from formtools.wizard.views import SessionWizardView
from .models import AdmissionApplication
from .forms import (
    PersonalInfoForm,
    CollegeSelectionForm,
    InterestedDepartmentsForm,
    EngineeringScoresForm,
    PharmacyScoresForm,
    ConfirmationForm,
)

class HomePageView(TemplateView):
    template_name = 'admission_service_app/index.html'


FORMS = [
    ("0", PersonalInfoForm),
    ("1", CollegeSelectionForm),
    ("2", InterestedDepartmentsForm),
    ("3", None),  # dynamic based on college
    ("4", ConfirmationForm),  # summary page (no form fields)
]

TEMPLATES = {
    "0": "admission_service_app/step1_personal_info.html",
    "1": "admission_service_app/step2_college_selection.html",
    "2": "admission_service_app/step3_interested_departments.html",
    "3": "admission_service_app/step4_scores.html",
    "4": "admission_service_app/step5_summary.html",
}


class AdmissionWizard(SessionWizardView):
    form_list = dict(FORMS)

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == "2":
            step1_data = self.get_cleaned_data_for_step("1")
            if step1_data:
                kwargs['college'] = step1_data.get("college")
        return kwargs

    def get_form(self, step=None, data=None, files=None):
        step = step or self.steps.current

        if step == "3":
            step1_data = self.get_cleaned_data_for_step("1")
            college = step1_data.get("college") if step1_data else None
            form_class = PharmacyScoresForm if college and "pharma" in college.name.lower() else EngineeringScoresForm
            return form_class(data=data, files=files)

        elif step == "4":
            return ConfirmationForm(data=data)

        return super().get_form(step, data=data, files=files)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        if self.steps.current == "4":  # Step 5 (summary)
            form_data = self.get_all_cleaned_data()
            context.update({
                'form_data': form_data,
                'college': form_data.get('college'),
                'interested_departments': form_data.get('interested_departments', []),
            })

        return context

    def done(self, form_list, **kwargs):
        form_data = self.get_all_cleaned_data()

        application = AdmissionApplication.objects.create(
            first_name=form_data.get('first_name'),
            last_name=form_data.get('last_name'),
            email=form_data.get('email'),
            mobile=form_data.get('mobile'),
            college=form_data.get('college'),
            jee_main_score=form_data.get('jee_main_score'),
            math_score=form_data.get('math_score'),
            neet_score=form_data.get('neet_score'),
            biology_score=form_data.get('biology_score'),
            physics_score=form_data.get('physics_score'),
            chemistry_score=form_data.get('chemistry_score'),
        )

        # Set many-to-many relationship
        departments = form_data.get('interested_departments', [])
        application.interested_departments.set(departments)
        application.save()

        return render(self.request, 'admission_service_app/done.html', {'application': application})
