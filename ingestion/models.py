from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class SourceBatch(models.Model):
    class SourceType(models.TextChoices):
        SAP = "sap", "SAP procurement/fuel"
        UTILITY = "utility", "Utility electricity"
        TRAVEL = "travel", "Corporate travel"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="source_batches")
    source_type = models.CharField(max_length=24, choices=SourceType.choices)
    name = models.CharField(max_length=160)
    ingestion_method = models.CharField(max_length=80)
    original_filename = models.CharField(max_length=255, blank=True)
    source_system = models.CharField(max_length=120)
    imported_by = models.CharField(max_length=120, default="analyst@breatheesg.com")
    imported_at = models.DateTimeField(auto_now_add=True)
    row_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    suspicious_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tenant} / {self.name}"


class ActivityRow(models.Model):
    class Status(models.TextChoices):
        NEEDS_REVIEW = "needs_review", "Needs review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        LOCKED = "locked", "Locked for audit"

    class Scope(models.TextChoices):
        SCOPE_1 = "scope_1", "Scope 1"
        SCOPE_2 = "scope_2", "Scope 2"
        SCOPE_3 = "scope_3", "Scope 3"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="activity_rows")
    source_batch = models.ForeignKey(SourceBatch, on_delete=models.CASCADE, related_name="activity_rows")
    external_id = models.CharField(max_length=120)
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    facility_or_cost_center = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=80)
    scope = models.CharField(max_length=12, choices=Scope.choices)
    raw_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    raw_unit = models.CharField(max_length=32, blank=True)
    normalized_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    normalized_unit = models.CharField(max_length=32, blank=True)
    emission_factor = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    co2e_kg = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    currency = models.CharField(max_length=8, blank=True)
    spend_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    raw_payload = models.JSONField(default=dict)
    validation_errors = models.JSONField(default=list)
    suspicious_reasons = models.JSONField(default=list)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEEDS_REVIEW)
    edited = models.BooleanField(default=False)
    approved_by = models.CharField(max_length=120, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("source_batch", "external_id")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.external_id} {self.category}"


class AuditEvent(models.Model):
    row = models.ForeignKey(ActivityRow, on_delete=models.CASCADE, related_name="audit_events")
    action = models.CharField(max_length=80)
    actor = models.CharField(max_length=120)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

# Create your models here.
