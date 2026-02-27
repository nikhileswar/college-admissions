from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('college', models.CharField(max_length=200)),
                ('branch', models.CharField(max_length=200)),
                ('seats', models.PositiveIntegerField(default=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['college', 'branch'],
                'unique_together': {('college', 'branch')},
            },
        ),
        migrations.CreateModel(
            name='MatchingResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('run_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('total_matched', models.PositiveIntegerField(default=0)),
                ('total_unmatched', models.PositiveIntegerField(default=0)),
                ('total_unfilled', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['-run_at'],
            },
        ),
        migrations.CreateModel(
            name='StudentProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('air_rank', models.PositiveIntegerField(blank=True, help_text='All India Rank', null=True)),
                ('has_submitted', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='auth.user')),
            ],
        ),
        migrations.CreateModel(
            name='Preference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rank', models.PositiveIntegerField()),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preferences', to='matching.studentprofile')),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preferences', to='matching.branch')),
            ],
            options={
                'ordering': ['student', 'rank'],
                'unique_together': {('student', 'branch'), ('student', 'rank')},
            },
        ),
        migrations.CreateModel(
            name='Allotment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('preference_rank', models.PositiveIntegerField(blank=True, null=True)),
                ('is_matched', models.BooleanField(default=False)),
                ('result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allotments', to='matching.matchingresult')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allotments', to='matching.studentprofile')),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='allotments', to='matching.branch')),
            ],
            options={
                'unique_together': {('result', 'student')},
            },
        ),
    ]
