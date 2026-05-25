from django.contrib import admin

from .models import ActivityRow, AuditEvent, SourceBatch, Tenant


admin.site.register(Tenant)
admin.site.register(SourceBatch)
admin.site.register(ActivityRow)
admin.site.register(AuditEvent)

# Register your models here.
