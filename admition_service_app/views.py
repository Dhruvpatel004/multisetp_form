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
from twilio.rest import Client

from django.conf import settings
import random
from django.utils.timezone import now, timedelta


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


def clear_otp_session(self):
    for key in ["otp_verified", "otp_sent", "otp_mobile", "otp_code", "otp_expiry"]:
        self.request.session.pop(key, None)


class AdmissionWizard(SessionWizardView):
    form_list = dict(FORMS)

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == "0":
            kwargs['show_otp'] = self.request.session.get('otp_sent', False)
            kwargs['otp_verified'] = self.request.session.get('otp_verified', False)
        if step == "2":
            step1_data = self.get_cleaned_data_for_step("1")
            if step1_data:
                kwargs['college'] = step1_data.get("college")
        return kwargs

    def post(self, *args, **kwargs):
        request = self.request
        step = self.steps.current

        if step == "0":
            form = self.get_form(data=request.POST)

            mobile = form.data.get("mobile", "").strip()
            session_mobile = request.session.get("otp_mobile", "").strip()

            if request.session.get("otp_verified") and mobile != session_mobile:
                request.session["otp_verified"] = False
                request.session["otp_sent"] = False
                request.session.pop("otp_code", None)
                request.session.pop("otp_expiry", None)
                request.session.pop("otp_mobile", None)
                form.add_error("mobile", "Mobile number changed. Please reverify with a new OTP.")
                return self.render(form)

            if request.session.get("otp_verified") and form.is_valid():
                return super().post(*args, **kwargs)

            if "send_otp" in request.POST:
                if form.is_valid():
                    mobile = form.cleaned_data.get("mobile")
                    if mobile:
                        mobile = mobile.strip()
                        if not mobile.startswith("+"):
                            form.add_error('mobile', "Mobile number must start with '+' followed by country code.")
                            return self.render(form)

                    # Generate and send OTP manually
                    otp = str(random.randint(100000, 999999))

                    try:
                        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                        message = client.messages.create(
                            body=f"Your verification code is: {otp}",
                            from_=settings.TWILIO_PHONE_NUMBER,
                            to=mobile
                        )

                        request.session["otp_sent"] = True
                        request.session["otp_mobile"] = mobile
                        request.session["otp_code"] = otp
                        request.session["otp_expiry"] = (now() + timedelta(minutes=5)).isoformat()

                        return self.render(form)
                    except Exception as e:
                        form.add_error('mobile', f"OTP sending failed")
                        print(f"Error sending OTP: {e}")
                        return self.render(form)

            elif "verify_and_continue" in request.POST:
                if form.is_valid():
                    mobile = form.cleaned_data.get("mobile")
                    otp = form.cleaned_data.get("otp")

                    session_otp = request.session.get("otp_code")
                    session_mobile = request.session.get("otp_mobile")
                    expiry = request.session.get("otp_expiry")

                    if not session_mobile or mobile != session_mobile:
                        form.add_error("mobile", "Mobile number does not match the one used for OTP.")
                        return self.render(form)

                    if now().isoformat() > expiry:
                        form.add_error("otp", "OTP has expired. Please request a new one.")
                        request.session.pop("otp_sent", None)
                        request.session.pop("otp_code", None)
                        return self.render(form)

                    if otp != session_otp:
                        form.add_error("otp", "Invalid OTP.")
                        return self.render(form)

                    request.session["otp_verified"] = True
                    request.session["otp_sent"] = True
                    return super().post(*args, **kwargs)

            return self.render(form)

        return super().post(*args, **kwargs)

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

    def get_next_step(self, step=None):
        if step == "0" and not self.request.session.get('otp_verified'):
            return None  # Don't allow moving forward if OTP not verified
        return super().get_next_step(step)

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        if self.steps.current == "0":
            context['show_otp'] = self.request.session.get('otp_sent', False)
            context['otp_verified'] = self.request.session.get('otp_verified', False)
        if self.steps.current == "4":  # Summary step
            form_data = self.get_all_cleaned_data()
            context.update({
                'form_data': form_data,
                'college': form_data.get('college'),
                'interested_departments': form_data.get('interested_departments', []),
            })
        return context

    def done(self, form_list, **kwargs):
        # Clear OTP session info after form submission completes
        self.request.session.pop("otp_sent", None)
        self.request.session.pop("otp_verified", None)
        self.request.session.pop("otp_mobile", None)

        form_data = self.get_all_cleaned_data()
        form_data = self.get_all_cleaned_data()

        form_data.update({
                'college': form_data.get('college'),
                'interested_departments': form_data.get('interested_departments', []),
            })


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
            is_mobile_verified=True,
        )

        departments = form_data.get('interested_departments', [])
        application.interested_departments.set(departments)
        application.save()

        return render(self.request, 'admission_service_app/done.html', {'application': application})
