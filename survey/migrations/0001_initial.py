# Generated by Django 3.1 on 2020-09-15 13:02

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('authApp', '0002_auto_20200914_1301'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option', models.CharField(max_length=20)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'Answers',
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=150)),
                ('question_type', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'Questions',
            },
        ),
        migrations.CreateModel(
            name='Questionnaire',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(max_length=150)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('active_till', models.DateField(default=datetime.datetime.now)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'Questionnaires',
            },
        ),
        migrations.CreateModel(
            name='Started_Questionnaire',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ccc_number', models.CharField(max_length=15)),
                ('firstname', models.CharField(max_length=30)),
                ('questionnaire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.questionnaire')),
                ('started_by', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'Started_Questionnaire',
            },
        ),
        migrations.CreateModel(
            name='Response',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('open_text', models.CharField(blank=True, max_length=150, null=True)),
                ('answer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.answer')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.question')),
                ('session', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='survey.started_questionnaire')),
            ],
            options={
                'db_table': 'Responses',
            },
        ),
        migrations.AddField(
            model_name='question',
            name='questionnaire',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.questionnaire'),
        ),
        migrations.CreateModel(
            name='Patient_Consent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ccc_number', models.CharField(max_length=15)),
                ('questionnaire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.questionnaire')),
            ],
            options={
                'db_table': 'PatientConsent',
            },
        ),
        migrations.CreateModel(
            name='Facility_Questionnaire',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='authApp.facility')),
                ('questionnaire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.questionnaire')),
            ],
            options={
                'db_table': 'Facility_Questionnaire',
            },
        ),
        migrations.CreateModel(
            name='End_Questionnaire',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ccc_number', models.CharField(max_length=15)),
                ('firstname', models.CharField(max_length=30)),
                ('questionnaire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.questionnaire')),
            ],
            options={
                'db_table': 'End_Questionnaire',
            },
        ),
        migrations.AddField(
            model_name='answer',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.question'),
        ),
    ]