from django.core.management.base import BaseCommand
from django.utils.text import slugify

from store.models import Brand, Category, Product

CATEGORIES = [
    ("Smartphones", "📱"),
    ("Laptops", "💻"),
    ("Televisions", "📺"),
    ("Headphones", "🎧"),
    ("Gaming", "🎮"),
    ("Smart home", "🏠"),
]

# (category, brand, name, price, old_price, stock, specs)
PRODUCTS = [
    ("Smartphones", "Samsung", "Samsung Galaxy S24 128GB", 2399, 2699, 12,
     "Display: 6.2\" AMOLED 120Hz\nStorage: 128 GB\nRAM: 8 GB\nBattery: 4000 mAh"),
    ("Smartphones", "Apple", "Apple iPhone 15 128GB", 2899, None, 8,
     "Display: 6.1\" Super Retina XDR\nStorage: 128 GB\nChip: A16 Bionic\nPort: USB-C"),
    ("Smartphones", "Xiaomi", "Xiaomi Redmi Note 13 256GB", 749, 849, 25,
     "Display: 6.67\" AMOLED 120Hz\nStorage: 256 GB\nRAM: 8 GB\nBattery: 5000 mAh"),
    ("Laptops", "Lenovo", "Lenovo IdeaPad 3 15\" Ryzen 5", 1599, 1799, 10,
     "Display: 15.6\" Full HD\nCPU: AMD Ryzen 5\nRAM: 16 GB\nStorage: 512 GB SSD"),
    ("Laptops", "ASUS", "ASUS Vivobook 15 Core i5", 1749, None, 7,
     "Display: 15.6\" Full HD\nCPU: Intel Core i5\nRAM: 16 GB\nStorage: 512 GB SSD"),
    ("Laptops", "Apple", "Apple MacBook Air 13\" M2", 3499, 3799, 5,
     "Display: 13.6\" Liquid Retina\nChip: Apple M2\nRAM: 8 GB\nStorage: 256 GB SSD"),
    ("Televisions", "Samsung", "Samsung 55\" Crystal UHD 4K", 1599, 1899, 6,
     "Screen: 55\"\nResolution: 3840 x 2160\nSmart TV: Tizen\nHDR: HDR10+"),
    ("Televisions", "LG", "LG 50\" UHD 4K Smart TV", 1399, None, 9,
     "Screen: 50\"\nResolution: 3840 x 2160\nSmart TV: webOS\nHDR: HDR10"),
    ("Headphones", "Sony", "Sony WH-1000XM5", 1099, 1299, 14,
     "Type: Over-ear, wireless\nNoise cancelling: Yes\nBattery: up to 30 hours\nBluetooth: 5.2"),
    ("Headphones", "JBL", "JBL Tune 520BT", 119, None, 40,
     "Type: On-ear, wireless\nBattery: up to 57 hours\nBluetooth: 5.3"),
    ("Headphones", "Apple", "Apple AirPods Pro (2nd gen)", 799, 899, 0,
     "Type: In-ear, wireless\nNoise cancelling: Yes\nCase: USB-C charging"),
    ("Gaming", "Sony", "Sony PlayStation 5 Slim", 1899, None, 4,
     "Storage: 1 TB SSD\nOutput: up to 4K 120Hz\nDrive: Disc"),
    ("Gaming", "Logitech", "Logitech G102 Gaming Mouse", 59, 75, 30,
     "Sensor: 8000 DPI\nButtons: 6\nLighting: RGB"),
    ("Smart home", "Xiaomi", "Xiaomi Robot Vacuum E10", 649, 749, 11,
     "Suction: 4000 Pa\nBattery: 2600 mAh\nControl: Mi Home app"),
    ("Smart home", "Xiaomi", "Xiaomi Smart Band 8", 149, None, 35,
     "Display: 1.62\" AMOLED\nBattery: up to 16 days\nWater resistance: 5 ATM"),
]


class Command(BaseCommand):
    help = "Fill the shop with demo categories, brands and products (prices are placeholders)."

    def handle(self, *args, **options):
        categories = {}
        for name, icon in CATEGORIES:
            categories[name], _ = Category.objects.get_or_create(
                slug=slugify(name), defaults={"name": name, "icon": icon}
            )

        created = 0
        for cat, brand_name, name, price, old_price, stock, specs in PRODUCTS:
            brand, _ = Brand.objects.get_or_create(
                slug=slugify(brand_name), defaults={"name": brand_name}
            )
            _, was_created = Product.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    "category": categories[cat],
                    "brand": brand,
                    "name": name,
                    "price": price,
                    "old_price": old_price,
                    "stock": stock,
                    "specs": specs,
                    "description": f"{name}. Demo product added by seed_demo; edit it in the admin panel.",
                },
            )
            created += was_created

        self.stdout.write(self.style.SUCCESS(f"Done. {created} new products added."))
