from django.db import migrations


def assign_default_role(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Role = apps.get_model('roles', 'Role')
    customer = Role.objects.get(code='customer')
    User.objects.filter(role__isnull=True).update(role=customer)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_role'),
    ]

    operations = [
        migrations.RunPython(assign_default_role, migrations.RunPython.noop),
    ]
