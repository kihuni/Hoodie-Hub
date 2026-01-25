from django.core.management.base import BaseCommand
from hoodieHub.models import Hoodie

class Command(BaseCommand):
    help = 'Create sample hoodie data'

    def handle(self, *args, **kwargs):
        hoodies = [
            {
                'name': 'Classic Black Hoodie',
                'description': 'Premium quality black hoodie with soft fleece lining. Perfect for casual wear.',
                'price': 2500,
                'available_sizes': 'S,M,L,XL',
                'stock_quantity': 50
            },
            {
                'name': 'Urban Grey Hoodie',
                'description': 'Stylish grey hoodie with modern fit. Great for everyday comfort.',
                'price': 2800,
                'available_sizes': 'S,M,L,XL',
                'stock_quantity': 40
            },
            {
                'name': 'Navy Blue Hoodie',
                'description': 'Deep navy blue hoodie with premium cotton blend.',
                'price': 3000,
                'available_sizes': 'M,L,XL',
                'stock_quantity': 30
            },
        ]
        
        for hoodie_data in hoodies:
            hoodie, created = Hoodie.objects.get_or_create(
                name=hoodie_data['name'],
                defaults=hoodie_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created: {hoodie.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Already exists: {hoodie.name}'))