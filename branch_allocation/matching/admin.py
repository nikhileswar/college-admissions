from django.contrib import admin
from .models import Branch, StudentProfile, Preference, MatchingResult, Allotment

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['college', 'branch', 'seats']
    list_filter = ['college']
    search_fields = ['college', 'branch']

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'air_rank', 'has_submitted']
    list_filter = ['has_submitted']
    search_fields = ['user__first_name', 'user__last_name', 'user__username']

@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display = ['student', 'rank', 'branch']
    list_filter = ['branch__college']

@admin.register(MatchingResult)
class MatchingResultAdmin(admin.ModelAdmin):
    list_display = ['run_at', 'is_active', 'total_matched', 'total_unmatched', 'total_unfilled']

@admin.register(Allotment)
class AllotmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'branch', 'preference_rank', 'is_matched']
    list_filter = ['is_matched', 'branch__college']
