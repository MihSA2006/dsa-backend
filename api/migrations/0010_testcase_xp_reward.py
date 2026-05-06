# Generated migration to add xp_reward field to TestCase

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_remove_teaminvitation_team_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='testcase',
            name='xp_reward',
            field=models.IntegerField(default=0, verbose_name='Points XP du test case'),
        ),
    ]
