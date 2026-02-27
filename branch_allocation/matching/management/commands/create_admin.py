from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create the default admin superuser (admin / admin123)'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                password='admin123',
                email='admin@collegmatch.local',
                first_name='Admin',
            )
            self.stdout.write(self.style.SUCCESS(
                '✅ Superuser created: admin / admin123'
            ))
        else:
            # Update password in case it changed
            user = User.objects.get(username='admin')
            user.set_password('admin123')
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(
                '✅ Admin user already exists — password reset to admin123'
            ))
