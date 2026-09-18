"""
Convert all vehicle master data to UPPERCASE.
Run once after switching to UPPERCASE policy.
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Convert vehicle master data (brand/model/type/color/fuel) to UPPERCASE'

    def handle(self, *args, **options):
        from apps.vehicles.models import (
            Brand, VehicleModel, VehicleType, Color, FuelType
        )

        self.stdout.write('Converting vehicle master data to UPPERCASE...\n')

        with transaction.atomic():

            # Brands
            for b in Brand.objects.all():
                upper = b.name.strip().upper()
                if b.name != upper:
                    existing = Brand.objects.filter(
                        name=upper
                    ).exclude(pk=b.pk).first()
                    if existing:
                        # Merge — move all models + vehicles to existing
                        for m in b.models.all():
                            m.brand = existing
                            m.save()
                        for v in b.vehicles.all():
                            v.brand = existing
                            v.save()
                        b.delete()
                        self.stdout.write(f'  Merged brand {b.name} → {upper}')
                    else:
                        b.name = upper
                        b.save()
                        self.stdout.write(f'  {b.name}')

            # Models
            for m in VehicleModel.objects.all():
                upper = m.name.strip().upper()
                if m.name != upper:
                    existing = VehicleModel.objects.filter(
                        brand=m.brand, name=upper
                    ).exclude(pk=m.pk).first()
                    if existing:
                        for v in m.vehicles.all():
                            v.model = existing
                            v.save()
                        m.delete()
                        self.stdout.write(
                            f'  Merged model {m.name} → {upper}'
                        )
                    else:
                        m.name = upper
                        m.save()
                        self.stdout.write(f'  {m.name}')

            # Vehicle Types
            for t in VehicleType.objects.all():
                upper = t.name.strip().upper()
                if t.name != upper:
                    existing = VehicleType.objects.filter(
                        name=upper
                    ).exclude(pk=t.pk).first()
                    if existing:
                        for v in t.vehicles.all():
                            v.vehicle_type = existing
                            v.save()
                        t.delete()
                        self.stdout.write(f'  Merged type {t.name} → {upper}')
                    else:
                        t.name = upper
                        t.save()
                        self.stdout.write(f'  {t.name}')

            # Colors
            for c in Color.objects.all():
                upper = c.name.strip().upper()
                if c.name != upper:
                    existing = Color.objects.filter(
                        name=upper
                    ).exclude(pk=c.pk).first()
                    if existing:
                        for v in c.vehicles.all():
                            v.color = existing
                            v.save()
                        c.delete()
                        self.stdout.write(f'  Merged color {c.name} → {upper}')
                    else:
                        c.name = upper
                        c.save()
                        self.stdout.write(f'  {c.name}')

            # Fuel Types
            for f in FuelType.objects.all():
                upper = f.name.strip().upper()
                if f.name != upper:
                    existing = FuelType.objects.filter(
                        name=upper
                    ).exclude(pk=f.pk).first()
                    if existing:
                        for v in f.vehicles.all():
                            v.fuel_type = existing
                            v.save()
                        f.delete()
                        self.stdout.write(f'  Merged fuel {f.name} → {upper}')
                    else:
                        f.name = upper
                        f.save()
                        self.stdout.write(f'  {f.name}')

            # Vehicle registrations
            from apps.vehicles.models import Vehicle
            for v in Vehicle.objects.all():
                upper = v.registration_number.strip().upper()
                if v.registration_number != upper:
                    v.registration_number = upper
                    v.save()

        self.stdout.write(
            self.style.SUCCESS('\n✓ All master data converted to UPPERCASE.\n')
        )