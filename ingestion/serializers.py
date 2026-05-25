from rest_framework import serializers

from .models import ActivityRow, AuditEvent, SourceBatch, Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = "__all__"


class SourceBatchSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)

    class Meta:
        model = SourceBatch
        fields = "__all__"


class ActivityRowSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    source_name = serializers.CharField(source="source_batch.name", read_only=True)
    source_type = serializers.CharField(source="source_batch.source_type", read_only=True)

    class Meta:
        model = ActivityRow
        fields = "__all__"


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = "__all__"
