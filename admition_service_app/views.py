"""
Admission Service Application Views
"""
import random

from django.conf import settings
from django.shortcuts import render
from django.utils.timezone import now, timedelta
from django.views.generic import TemplateView
from formtools.wizard.views import SessionWizardView
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from .forms import (CollegeSelectionForm, ConfirmationForm,
                    EngineeringScoresForm, InterestedDepartmentsForm,
                    PersonalInfoForm, PharmacyScoresForm)
from .models import AdmissionApplication


class HomePageView(TemplateView):
    """
    Home page view for the admission service application.
    Displays the main landing page with information about the admission process.
    """
    template_name = "admission_service_app/index.html"


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
    """
    Clear OTP-related session data after successful submission.
    This function is called to ensure that OTP data does not persist
    """
    for key in ["otp_verified", "otp_sent", "otp_mobile", "otp_code", "otp_expiry"]:
        self.request.session.pop(key, None)


class AdmissionWizard(SessionWizardView):
    """
    Admission application wizard view to handle multi-step form submission.
    Steps:
    - 0: Personal Info & Contact (with OTP)
    - 1: Select College
    - 2: Interested Departments
    - 3: Exam Scores (dynamic)
    - 4: Summary
    - 5: Final Submit
    """

    form_list = dict(FORMS)

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == "0":
            kwargs["show_otp"] = self.request.session.get("otp_sent", False)
            kwargs["otp_verified"] = self.request.session.get("otp_verified", False)
        if step == "2":
            step1_data = self.get_cleaned_data_for_step("1")
            if step1_data:
                kwargs["college"] = step1_data.get("college")
        return kwargs

    def get_form(self, step=None, data=None, files=None):
        step = step or self.steps.current
        if step == "3":
            step1_data = self.get_cleaned_data_for_step("1")
            college = step1_data.get("college") if step1_data else None
            form_class = (
                PharmacyScoresForm
                if college and "pharma" in college.name.lower()
                else EngineeringScoresForm
            )
            return form_class(data=data, files=files)
        return super().get_form(step, data=data, files=files)

    def get_next_step(self, step=None):
        if step == "0" and not self.request.session.get("otp_verified"):
            return None
        return super().get_next_step(step)

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        if self.steps.current == "0":
            context.update({
                "show_otp": self.request.session.get("otp_sent", False),
                "otp_verified": self.request.session.get("otp_verified", False)
            })
        if self.steps.current == "4":
            form_data = self.get_all_cleaned_data()
            context.update({
                "form_data": form_data,
                "college": form_data.get("college"),
                "interested_departments": form_data.get("interested_departments", [])
            })
        return context

    def done(self, form_list, **kwargs):
        self._reset_otp_session()
        form_data = self.get_all_cleaned_data()

        application = AdmissionApplication.objects.create(
            first_name=form_data.get("first_name"),
            last_name=form_data.get("last_name"),
            email=form_data.get("email"),
            mobile=form_data.get("mobile"),
            college=form_data.get("college"),
            jee_main_score=form_data.get("jee_main_score"),
            math_score=form_data.get("math_score"),
            neet_score=form_data.get("neet_score"),
            biology_score=form_data.get("biology_score"),
            physics_score=form_data.get("physics_score"),
            chemistry_score=form_data.get("chemistry_score"),
            is_mobile_verified=True,
        )

        departments = form_data.get("interested_departments", [])
        application.interested_departments.set(departments)
        application.save()

        return render(
            self.request,
            "admission_service_app/done.html",
            {"application": application},
        )

    def post(self, *args, **kwargs):
        """Handle POST for step 0 (OTP verification logic)"""
        request = self.request
        step = self.steps.current

        if step != "0":
            return super().post(*args, **kwargs)

        form = self.get_form(data=request.POST)
        mobile = form.data.get(f"{step}-mobile", "").strip()
        session_mobile = request.session.get("otp_mobile", "").strip()

        if request.session.get("otp_verified") and mobile != session_mobile:
            self._reset_otp_session()
            form.add_error("mobile", "Mobile number changed. Please reverify with a new OTP.")
        elif request.session.get("otp_verified") and form.is_valid():
            return super().post(*args, **kwargs)
        elif "send_otp" in request.POST and form.is_valid():
            return self._handle_send_otp(form)
        elif "verify_and_continue" in request.POST and form.is_valid():
            if self._verify_otp(form):
                request.session["otp_verified"] = True
                request.session["otp_sent"] = True
                return super().post(*args, **kwargs)

        return self.render(form)

    def _handle_send_otp(self, form):
        """Send OTP to the mobile if valid"""
        mobile = form.cleaned_data.get("mobile", "").strip()
        if not mobile.startswith("+"):
            form.add_error("mobile", "Mobile must start with '+' and country code.")
            return self.render(form)

        if self._send_otp_to_mobile(mobile):
            return self.render(form)

        form.add_error("mobile", "OTP sending failed.")
        return self.render(form)

    def _reset_otp_session(self):
        """Clear OTP session values"""
        for key in ("otp_verified", "otp_sent", "otp_code", "otp_expiry", "otp_mobile"):
            self.request.session.pop(key, None)

    def _send_otp_to_mobile(self, mobile):
        """Generate and send OTP via Twilio"""
        otp = str(random.randint(100000, 999999))
        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=f"Your verification code is: {otp}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=mobile,
            )
            self.request.session.update({
                "otp_sent": True,
                "otp_mobile": mobile,
                "otp_code": otp,
                "otp_expiry": (now() + timedelta(minutes=1)).isoformat()
            })
            return True
        except TwilioRestException as exc:
            print(f"Error sending OTP: {exc}")
            return False

    def _verify_otp(self, form):
        """Validate OTP input"""
        mobile = form.cleaned_data.get("mobile")
        otp = form.cleaned_data.get("otp")
        session_mobile = self.request.session.get("otp_mobile")
        session_otp = self.request.session.get("otp_code")
        expiry = self.request.session.get("otp_expiry")

        if not session_mobile or mobile != session_mobile:
            form.add_error("mobile", "Mobile number mismatch.")
            return False
        if now().isoformat() > expiry:
            form.add_error("otp", "OTP expired. Request a new one.")
            self.request.session.pop("otp_sent", None)
            self.request.session.pop("otp_code", None)
            return False
        if otp != session_otp:
            form.add_error("otp", "Invalid OTP.")
            return False
        return True