from django.db import models
from django.contrib.auth.models import User


class Branch(models.Model):
    """A college + branch combination with a seat capacity."""
    college = models.CharField(max_length=200)
    branch = models.CharField(max_length=200)
    seats = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['college', 'branch']
        unique_together = ['college', 'branch']

    def __str__(self):
        return f"{self.college} — {self.branch}"

    def label(self):
        return f"{self.college} — {self.branch}"


class StudentProfile(models.Model):
    """Extended profile for student users."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    air_rank = models.PositiveIntegerField(null=True, blank=True, help_text="All India Rank")
    has_submitted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (AIR {self.air_rank})"

    def display_name(self):
        full = self.user.get_full_name()
        if full:
            return f"{full} (AIR {self.air_rank})" if self.air_rank else full
        return self.user.username


class Preference(models.Model):
    """
    Ordered preference list: one row per student-branch pair.
    rank=1 means most preferred.
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='preferences')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='preferences')
    rank = models.PositiveIntegerField()

    class Meta:
        ordering = ['student', 'rank']
        unique_together = [['student', 'branch'], ['student', 'rank']]

    def __str__(self):
        return f"{self.student} → #{self.rank} {self.branch}"


class MatchingResult(models.Model):
    """
    Stores the result of a stable matching run.
    One active result at a time (admin can rerun to replace).
    """
    run_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    total_matched = models.PositiveIntegerField(default=0)
    total_unmatched = models.PositiveIntegerField(default=0)
    total_unfilled = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-run_at']

    def __str__(self):
        return f"Matching run {self.run_at.strftime('%Y-%m-%d %H:%M')} — {self.total_matched} matched"


class Allotment(models.Model):
    """One allotment per student in a matching result."""
    result = models.ForeignKey(MatchingResult, on_delete=models.CASCADE, related_name='allotments')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='allotments')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='allotments', null=True, blank=True)
    preference_rank = models.PositiveIntegerField(null=True, blank=True)
    is_matched = models.BooleanField(default=False)

    class Meta:
        unique_together = ['result', 'student']

    def __str__(self):
        if self.is_matched:
            return f"{self.student} → {self.branch} (pref #{self.preference_rank})"
        return f"{self.student} → UNMATCHED"
