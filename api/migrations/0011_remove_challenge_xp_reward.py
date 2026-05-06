# Migration to remove xp_reward field from Challenge (now calculated as sum of test cases)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_testcase_xp_reward'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='challenge',
            name='xp_reward',
        ),
    ]
