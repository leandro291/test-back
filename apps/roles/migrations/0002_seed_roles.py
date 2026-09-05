from django.db import migrations

INITIAL_ROLES = [
    {
        'code': 'customer',
        'name': 'Customer',
        'description': 'End buyer who places orders in the shop.',
    },
    {
        'code': 'seller',
        'name': 'Seller',
        'description': 'Publishes and manages products in the catalog.',
    },
    {
        'code': 'admin',
        'name': 'Administrator',
        'description': 'Manages the platform and its users.',
    },
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model('roles', 'Role')
    for role in INITIAL_ROLES:
        Role.objects.get_or_create(
            code=role['code'],
            defaults={'name': role['name'], 'description': role['description']},
        )


def unseed_roles(apps, schema_editor):
    Role = apps.get_model('roles', 'Role')
    Role.objects.filter(code__in=[r['code'] for r in INITIAL_ROLES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
