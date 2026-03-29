from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('api', '0001_initial'),
	]

	operations = [
		migrations.AddField(
			model_name='card',
			name='attack_speed',
			field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
		),
	]
