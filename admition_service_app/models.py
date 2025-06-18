from django.core.exceptions import ValidationError
from django.core.validators import (MaxValueValidator, MinValueValidator,
                                    RegexValidator)
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Abstract model to add created and updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class College(TimeStampedModel):
    """Model for colleges."""

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    address = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Colleges"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Department(TimeStampedModel):
    """Departments offered by a college."""

    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("college", "name")
        ordering = ["college", "name"]

    def __str__(self):
        return f"{self.name} ({self.college.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class AdmissionApplication(TimeStampedModel):
    """Admission Application model with step-wise fields."""

    phone_validator = RegexValidator(
        regex=r"^\+?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )

    # === Step 1: Personal Info & Contact ===
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)

    mobile = models.CharField(max_length=15, unique=True, validators=[phone_validator])
    is_mobile_verified = models.BooleanField(default=False)

    # === Step 2: Select College ===
    college = models.ForeignKey(
        College, on_delete=models.PROTECT, related_name="applications"
    )

    # === Step 3: Select Interested Departments (many to many) ===
    interested_departments = models.ManyToManyField(Department, blank=True)

    # === Step 4: Entrance Exam Scores (conditional) ===
    # Engineering department related
    jee_main_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)],
    )
    math_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Medical department related
    neet_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(720)],
    )
    biology_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Shared subjects for both streams
    physics_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    chemistry_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # === Step 5: Status ===
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.college.name}"

    # def clean(self):
    #     cleaned_data = super().clean()
    #     college = cleaned_data.get("college")
    #     departments = cleaned_data.get("interested_departments")

    #     if college and departments:
    #         for dept in departments:
    #             if dept.college != college:
    #                 raise ValidationError(f"Department '{dept.name}' does not belong to the selected college.")
