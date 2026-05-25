import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import ActivityRow, AuditEvent, SourceBatch, Tenant
from .serializers import ActivityRowSerializer, AuditEventSerializer, SourceBatchSerializer, TenantSerializer


UNIT_CONVERSIONS = {
    "L": ("liter", Decimal("1")),
    "LTR": ("liter", Decimal("1")),
    "GAL": ("liter", Decimal("3.78541")),
    "KWH": ("kWh", Decimal("1")),
    "MWH": ("kWh", Decimal("1000")),
    "MI": ("km", Decimal("1.60934")),
    "MILE": ("km", Decimal("1.60934")),
    "KM": ("km", Decimal("1")),
    "NIGHT": ("room-night", Decimal("1")),
}

EMISSION_FACTORS = {
    "diesel": Decimal("2.68"),
    "gasoline": Decimal("2.31"),
    "electricity": Decimal("0.386"),
    "flight": Decimal("0.158"),
    "hotel": Decimal("14.00"),
    "ground": Decimal("0.171"),
    "procurement": Decimal("0.42"),
}


def parse_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return None


def parse_date(value):
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def normalize_unit(quantity, unit):
    if quantity is None:
        return None, unit or ""
    normalized_unit, multiplier = UNIT_CONVERSIONS.get((unit or "").upper(), (unit or "", Decimal("1")))
    return quantity * multiplier, normalized_unit


def classify_suspicion(normalized_quantity, category, period_start=None, period_end=None):
    reasons = []
    if normalized_quantity is None:
        return ["Quantity missing or unreadable"]
    if normalized_quantity <= 0:
        reasons.append("Non-positive activity quantity")
    if category == "electricity" and normalized_quantity > 250000:
        reasons.append("Electricity use is unusually high for one billing period")
    if category == "diesel" and normalized_quantity > 40000:
        reasons.append("Fuel draw exceeds expected site monthly range")
    if period_start and period_end and (period_end - period_start).days > 45:
        reasons.append("Billing period does not align cleanly to a month")
    return reasons


def compute_co2e(category, normalized_quantity):
    if normalized_quantity is None:
        return None, None
    factor = EMISSION_FACTORS.get(category, EMISSION_FACTORS["procurement"])
    return factor, normalized_quantity * factor


def make_row(batch, payload):
    source = batch.source_type
    errors = []
    if source == SourceBatch.SourceType.SAP:
        category = (payload.get("MaterialGroup") or payload.get("Warengruppe") or "procurement").lower()
        category = "diesel" if "diesel" in category or "fuel" in category or "kraftstoff" in category else "procurement"
        qty = parse_decimal(payload.get("Quantity") or payload.get("Menge"))
        unit = payload.get("Unit") or payload.get("MEINS") or ""
        activity_date = parse_date(payload.get("PostingDate") or payload.get("Buchungsdatum"))
        facility = payload.get("Plant") or payload.get("Werk") or payload.get("CostCenter") or ""
        scope = ActivityRow.Scope.SCOPE_1 if category == "diesel" else ActivityRow.Scope.SCOPE_3
        external_id = payload.get("DocumentItem") or f"{payload.get('Document', 'SAP')}-{payload.get('Item', '')}"
        spend = parse_decimal(payload.get("NetValue") or payload.get("Nettowert"))
        currency = payload.get("Currency") or payload.get("WAERS") or ""
    elif source == SourceBatch.SourceType.UTILITY:
        category = "electricity"
        qty = parse_decimal(payload.get("usage_kwh") or payload.get("Usage") or payload.get("Consumption"))
        unit = payload.get("unit") or payload.get("Unit") or "kWh"
        activity_date = None
        facility = payload.get("meter_id") or payload.get("Meter") or payload.get("Account") or ""
        scope = ActivityRow.Scope.SCOPE_2
        external_id = payload.get("bill_id") or payload.get("Statement") or facility
        spend = parse_decimal(payload.get("amount") or payload.get("BillAmount"))
        currency = payload.get("currency") or "USD"
    else:
        category = (payload.get("category") or payload.get("ExpenseType") or "flight").lower()
        category = "ground" if "taxi" in category or "car" in category or "ground" in category else category
        qty = parse_decimal(payload.get("distance") or payload.get("Distance") or payload.get("nights") or payload.get("Nights"))
        unit = payload.get("unit") or ("night" if category == "hotel" else "km")
        activity_date = parse_date(payload.get("travel_date") or payload.get("TransactionDate"))
        facility = payload.get("cost_center") or payload.get("Department") or ""
        scope = ActivityRow.Scope.SCOPE_3
        external_id = payload.get("expense_id") or payload.get("ReportEntryID") or payload.get("trip_id")
        spend = parse_decimal(payload.get("amount") or payload.get("ApprovedAmount"))
        currency = payload.get("currency") or "USD"

    normalized_quantity, normalized_unit = normalize_unit(qty, unit)
    period_start = parse_date(payload.get("period_start") or payload.get("StartDate"))
    period_end = parse_date(payload.get("period_end") or payload.get("EndDate"))
    if not external_id:
        errors.append("Missing source row identifier")
        external_id = f"missing-{timezone.now().timestamp()}"
    if not parse_date(activity_date) and not activity_date and source != SourceBatch.SourceType.UTILITY:
        errors.append("Activity date could not be parsed")
    suspicious = classify_suspicion(normalized_quantity, category, period_start, period_end)
    factor, co2e = compute_co2e(category, normalized_quantity)
    return ActivityRow(
        tenant=batch.tenant,
        source_batch=batch,
        external_id=str(external_id),
        activity_date=activity_date,
        period_start=period_start,
        period_end=period_end,
        facility_or_cost_center=facility,
        category=category,
        scope=scope,
        raw_quantity=qty,
        raw_unit=unit,
        normalized_quantity=normalized_quantity,
        normalized_unit=normalized_unit,
        emission_factor=factor,
        co2e_kg=co2e,
        currency=currency,
        spend_amount=spend,
        raw_payload=payload,
        validation_errors=errors,
        suspicious_reasons=suspicious,
    )


class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer


class SourceBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SourceBatch.objects.select_related("tenant").all()
    serializer_class = SourceBatchSerializer


class ActivityRowViewSet(viewsets.ModelViewSet):
    queryset = ActivityRow.objects.select_related("tenant", "source_batch").all()
    serializer_class = ActivityRowSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        review = self.request.query_params.get("review")
        source_type = self.request.query_params.get("source_type")
        if review == "true":
            queryset = queryset.exclude(status=ActivityRow.Status.LOCKED)
        if source_type:
            queryset = queryset.filter(source_batch__source_type=source_type)
        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        row = self.get_object()
        row.status = ActivityRow.Status.APPROVED
        row.approved_by = request.data.get("actor", "analyst@breatheesg.com")
        row.approved_at = timezone.now()
        row.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        AuditEvent.objects.create(row=row, action="approved", actor=row.approved_by, details={"source": "review_dashboard"})
        return Response(self.get_serializer(row).data)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        row = self.get_object()
        if row.status != ActivityRow.Status.APPROVED:
            return Response({"detail": "Rows must be approved before audit lock."}, status=status.HTTP_400_BAD_REQUEST)
        row.status = ActivityRow.Status.LOCKED
        row.locked_at = timezone.now()
        row.save(update_fields=["status", "locked_at", "updated_at"])
        AuditEvent.objects.create(row=row, action="locked", actor=request.data.get("actor", "auditor@breatheesg.com"), details={})
        return Response(self.get_serializer(row).data)


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.select_related("row").all()
    serializer_class = AuditEventSerializer


@api_view(["GET"])
def summary(request):
    return Response(summary_payload())


def summary_payload():
    rows = ActivityRow.objects.all()
    by_source = rows.values("source_batch__source_type").annotate(count=Count("id"), co2e=Sum("co2e_kg"))
    return {
        "total_rows": rows.count(),
        "approved": rows.filter(status=ActivityRow.Status.APPROVED).count(),
        "locked": rows.filter(status=ActivityRow.Status.LOCKED).count(),
        "failed": rows.filter(~Q(validation_errors=[])).count(),
        "suspicious": rows.filter(~Q(suspicious_reasons=[])).count(),
        "co2e_kg": rows.aggregate(total=Sum("co2e_kg"))["total"] or 0,
        "by_source": list(by_source),
    }


@api_view(["POST"])
def upload_csv(request):
    source_type = request.data.get("source_type")
    upload = request.FILES.get("file")
    if not source_type or not upload:
        return Response({"detail": "source_type and file are required."}, status=status.HTTP_400_BAD_REQUEST)
    tenant, _ = Tenant.objects.get_or_create(slug="acme-industrial", defaults={"name": "Acme Industrial"})
    batch = SourceBatch.objects.create(
        tenant=tenant,
        source_type=source_type,
        name=request.data.get("name") or upload.name,
        ingestion_method="csv_upload",
        original_filename=upload.name,
        source_system=request.data.get("source_system", source_type.upper()),
    )
    text = upload.read().decode("utf-8-sig")
    rows = [make_row(batch, row) for row in csv.DictReader(io.StringIO(text))]
    ActivityRow.objects.bulk_create(rows)
    batch.row_count = len(rows)
    batch.failed_count = sum(1 for row in rows if row.validation_errors)
    batch.suspicious_count = sum(1 for row in rows if row.suspicious_reasons)
    batch.save()
    return Response(SourceBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def seed_demo(request):
    ActivityRow.objects.all().delete()
    SourceBatch.objects.all().delete()
    tenant, _ = Tenant.objects.get_or_create(slug="acme-industrial", defaults={"name": "Acme Industrial"})
    fixtures = {
        SourceBatch.SourceType.SAP: [
            {"DocumentItem": "4900008811-10", "PostingDate": "2026-01-31", "Plant": "DE07", "MaterialGroup": "Diesel fuel", "Quantity": "18850", "Unit": "L", "NetValue": "26750", "Currency": "EUR"},
            {"DocumentItem": "4900008811-20", "Buchungsdatum": "31.01.2026", "Werk": "IN03", "Warengruppe": "Kraftstoff Diesel", "Menge": "42100", "MEINS": "LTR", "Nettowert": "39840", "WAERS": "INR"},
            {"DocumentItem": "4900009020-10", "PostingDate": "2026/02/03", "Plant": "US14", "MaterialGroup": "Purchased steel parts", "Quantity": "2400", "Unit": "KG", "NetValue": "188000", "Currency": "USD"},
        ],
        SourceBatch.SourceType.UTILITY: [
            {"bill_id": "GB-2026-001", "meter_id": "MTR-ATL-08", "period_start": "2026-01-12", "period_end": "2026-02-11", "usage_kwh": "84500", "unit": "kWh", "amount": "10150", "currency": "USD"},
            {"bill_id": "GB-2026-002", "meter_id": "MTR-HOU-02", "period_start": "2026-01-01", "period_end": "2026-02-28", "usage_kwh": "312000", "unit": "kWh", "amount": "37620", "currency": "USD"},
            {"bill_id": "GB-2026-003", "meter_id": "MTR-MUC-01", "period_start": "2026-02-01", "period_end": "2026-02-29", "usage_kwh": "", "unit": "kWh", "amount": "9940", "currency": "EUR"},
        ],
        SourceBatch.SourceType.TRAVEL: [
            {"expense_id": "CNQ-7721", "travel_date": "2026-02-04", "category": "flight", "origin": "SFO", "destination": "JFK", "distance": "4160", "unit": "km", "amount": "612", "currency": "USD", "cost_center": "SALES-US"},
            {"expense_id": "CNQ-7722", "TransactionDate": "02/06/2026", "ExpenseType": "Hotel", "nights": "3", "unit": "night", "ApprovedAmount": "735", "currency": "USD", "Department": "SALES-US"},
            {"expense_id": "CNQ-7723", "travel_date": "2026-02-07", "category": "taxi ground", "distance": "0", "unit": "mi", "amount": "54", "currency": "USD", "cost_center": "SALES-US"},
        ],
    }
    methods = {
        SourceBatch.SourceType.SAP: ("SAP OData export snapshot", "SAP S/4HANA PurchaseOrder OData"),
        SourceBatch.SourceType.UTILITY: ("Green Button portal CSV", "Utility customer portal"),
        SourceBatch.SourceType.TRAVEL: ("Concur expense report export", "SAP Concur Expense"),
    }
    for source_type, payloads in fixtures.items():
        method, system = methods[source_type]
        batch = SourceBatch.objects.create(
            tenant=tenant,
            source_type=source_type,
            name=f"{system} demo batch",
            ingestion_method=method,
            source_system=system,
            notes="Fabricated but shaped from public documentation and common enterprise exports.",
        )
        rows = [make_row(batch, payload) for payload in payloads]
        ActivityRow.objects.bulk_create(rows)
        batch.row_count = len(rows)
        batch.failed_count = sum(1 for row in rows if row.validation_errors)
        batch.suspicious_count = sum(1 for row in rows if row.suspicious_reasons)
        batch.save()
    return Response(summary_payload())

# Create your views here.
