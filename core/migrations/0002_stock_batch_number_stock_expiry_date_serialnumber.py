# Generated by Django 5.2 on 2025-06-02 03:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='stock',
            name='batch_number',
            field=models.CharField(blank=True, help_text='Batch number for tracking', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='stock',
            name='expiry_date',
            field=models.DateField(blank=True, help_text='Expiry date of the batch', null=True),
        ),
        migrations.CreateModel(
            name='SerialNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serial_number', models.CharField(max_length=255, unique=True)),
                ('is_allocated', models.BooleanField(default=False, help_text='Indicates if the serial number is allocated to an order or stock out transaction.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='serial_numbers', to='core.product')),
                ('stock_in_transaction', models.ForeignKey(blank=True, help_text='Stock transaction that brought this serial number into inventory.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='serial_numbers_in', to='core.stock')),
                ('stock_out_transaction', models.ForeignKey(blank=True, help_text='Stock transaction that took this serial number out of inventory.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='serial_numbers_out', to='core.stock')),
            ],
            options={
                'verbose_name_plural': 'Serial Numbers',
                'ordering': ['serial_number'],
            },
        ),
    ]
