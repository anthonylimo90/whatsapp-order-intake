"""Database seeding with demo data."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import Customer, Product


# Expanded customer data (15+ customers across regions)
CUSTOMERS = [
    # Masai Mara Safari Lodges
    {"name": "Sarah Kimani", "organization": "Saruni Mara", "phone": "+254700000001", "tier": "premium", "region": "Masai Mara"},
    {"name": "Peter Omondi", "organization": "Governors Camp", "phone": "+254700000002", "tier": "vip", "region": "Masai Mara"},
    {"name": "James Mwangi", "organization": "Angama Mara", "phone": "+254700000003", "tier": "vip", "region": "Masai Mara"},
    {"name": "Grace Wanjiku", "organization": "Kilima Safari Lodge", "phone": "+254700000004", "tier": "premium", "region": "Masai Mara"},
    {"name": "David Kipchoge", "organization": "Mara Serena Safari", "phone": "+254700000005", "tier": "standard", "region": "Masai Mara"},

    # Coast Region Hotels
    {"name": "Amina Hassan", "organization": "Diani Reef Beach", "phone": "+254700000010", "tier": "premium", "region": "Coast"},
    {"name": "Mohamed Ali", "organization": "Leopard Beach Resort", "phone": "+254700000011", "tier": "standard", "region": "Coast"},
    {"name": "Fatma Omar", "organization": "Baobab Beach Resort", "phone": "+254700000012", "tier": "premium", "region": "Coast"},
    {"name": "Hassan Juma", "organization": "Voyager Beach Resort", "phone": "+254700000013", "tier": "standard", "region": "Coast"},

    # Nairobi Hotels
    {"name": "Elizabeth Njeri", "organization": "Sarova Stanley", "phone": "+254700000020", "tier": "vip", "region": "Nairobi"},
    {"name": "John Kamau", "organization": "Norfolk Hotel", "phone": "+254700000021", "tier": "premium", "region": "Nairobi"},
    {"name": "Catherine Mueni", "organization": "Tribe Hotel", "phone": "+254700000022", "tier": "standard", "region": "Nairobi"},

    # Lake Region Lodges
    {"name": "Wilson Otieno", "organization": "Lake Naivasha Resort", "phone": "+254700000030", "tier": "standard", "region": "Lake Region"},
    {"name": "Mercy Akinyi", "organization": "Enashipai Resort", "phone": "+254700000031", "tier": "premium", "region": "Lake Region"},

    # Mount Kenya Region
    {"name": "Francis Ndungu", "organization": "Fairmont Mount Kenya", "phone": "+254700000040", "tier": "vip", "region": "Mount Kenya"},
    {"name": "Rose Muthoni", "organization": "Serena Mountain Lodge", "phone": "+254700000041", "tier": "premium", "region": "Mount Kenya"},
]

# Expanded product catalog (50+ products across categories)
PRODUCTS = [
    # Grains & Staples
    {"name": "Basmati Rice 25kg", "category": "Grains & Staples", "unit": "bag", "price": 2500.0},
    {"name": "Pishori Rice 25kg", "category": "Grains & Staples", "unit": "bag", "price": 2200.0},
    {"name": "White Rice 25kg", "category": "Grains & Staples", "unit": "bag", "price": 1800.0},
    {"name": "Wheat Flour 25kg", "category": "Grains & Staples", "unit": "bag", "price": 1500.0},
    {"name": "Maize Flour 25kg", "category": "Grains & Staples", "unit": "bag", "price": 1200.0},
    {"name": "Sugar 50kg", "category": "Grains & Staples", "unit": "bag", "price": 3500.0},
    {"name": "Sugar 25kg", "category": "Grains & Staples", "unit": "bag", "price": 1800.0},
    {"name": "Salt 25kg", "category": "Grains & Staples", "unit": "bag", "price": 600.0},

    # Cooking Oils & Fats
    {"name": "Vegetable Oil 20L", "category": "Cooking Oils", "unit": "jerrycan", "price": 3200.0},
    {"name": "Vegetable Oil 10L", "category": "Cooking Oils", "unit": "jerrycan", "price": 1700.0},
    {"name": "Vegetable Oil 5L", "category": "Cooking Oils", "unit": "bottle", "price": 900.0},
    {"name": "Olive Oil 5L", "category": "Cooking Oils", "unit": "bottle", "price": 2500.0},
    {"name": "Butter 500g", "category": "Cooking Oils", "unit": "pack", "price": 450.0},
    {"name": "Margarine 500g", "category": "Cooking Oils", "unit": "tub", "price": 280.0},

    # Dairy Products
    {"name": "Fresh Milk 20L", "category": "Dairy", "unit": "jerrycan", "price": 1200.0},
    {"name": "Fresh Milk 5L", "category": "Dairy", "unit": "bottle", "price": 350.0},
    {"name": "UHT Milk (Crate of 12)", "category": "Dairy", "unit": "crate", "price": 1500.0},
    {"name": "Yoghurt 5L", "category": "Dairy", "unit": "container", "price": 800.0},
    {"name": "Cheese Block 2kg", "category": "Dairy", "unit": "block", "price": 1800.0},
    {"name": "Cream 1L", "category": "Dairy", "unit": "bottle", "price": 450.0},

    # Eggs & Poultry
    {"name": "Eggs (Tray of 30)", "category": "Eggs & Poultry", "unit": "tray", "price": 450.0},
    {"name": "Eggs (Crate of 360)", "category": "Eggs & Poultry", "unit": "crate", "price": 5200.0},
    {"name": "Chicken Whole 1.5kg", "category": "Eggs & Poultry", "unit": "piece", "price": 650.0},
    {"name": "Chicken Breast 1kg", "category": "Eggs & Poultry", "unit": "kg", "price": 550.0},

    # Bread & Bakery
    {"name": "White Bread Loaf", "category": "Bakery", "unit": "loaf", "price": 60.0},
    {"name": "Brown Bread Loaf", "category": "Bakery", "unit": "loaf", "price": 65.0},
    {"name": "Bread Rolls (Pack of 12)", "category": "Bakery", "unit": "pack", "price": 180.0},
    {"name": "Croissants (Pack of 6)", "category": "Bakery", "unit": "pack", "price": 350.0},

    # Beverages
    {"name": "Tusker Beer (Crate of 24)", "category": "Beverages", "unit": "crate", "price": 2400.0},
    {"name": "White Cap Beer (Crate of 24)", "category": "Beverages", "unit": "crate", "price": 2300.0},
    {"name": "Soda Assorted (Crate of 24)", "category": "Beverages", "unit": "crate", "price": 1200.0},
    {"name": "Mineral Water 500ml (Pack of 24)", "category": "Beverages", "unit": "pack", "price": 600.0},
    {"name": "Mineral Water 1.5L (Pack of 6)", "category": "Beverages", "unit": "pack", "price": 450.0},
    {"name": "Orange Juice 1L", "category": "Beverages", "unit": "bottle", "price": 180.0},
    {"name": "Coffee Beans 1kg", "category": "Beverages", "unit": "kg", "price": 1200.0},
    {"name": "Tea Bags (Box of 100)", "category": "Beverages", "unit": "box", "price": 350.0},

    # Fresh Vegetables
    {"name": "Tomatoes 5kg", "category": "Vegetables", "unit": "kg", "price": 400.0},
    {"name": "Onions 5kg", "category": "Vegetables", "unit": "kg", "price": 350.0},
    {"name": "Potatoes 10kg", "category": "Vegetables", "unit": "kg", "price": 500.0},
    {"name": "Carrots 5kg", "category": "Vegetables", "unit": "kg", "price": 300.0},
    {"name": "Cabbage", "category": "Vegetables", "unit": "head", "price": 80.0},
    {"name": "Lettuce", "category": "Vegetables", "unit": "head", "price": 100.0},
    {"name": "Mixed Salad Greens 1kg", "category": "Vegetables", "unit": "kg", "price": 450.0},
    {"name": "Green Peppers 1kg", "category": "Vegetables", "unit": "kg", "price": 200.0},

    # Cleaning Supplies
    {"name": "Toilet Paper (Pack of 48)", "category": "Cleaning", "unit": "pack", "price": 1800.0},
    {"name": "Toilet Paper (Pack of 12)", "category": "Cleaning", "unit": "pack", "price": 500.0},
    {"name": "Multi-Surface Cleaner 5L", "category": "Cleaning", "unit": "bottle", "price": 450.0},
    {"name": "Dish Soap 5L", "category": "Cleaning", "unit": "bottle", "price": 380.0},
    {"name": "Laundry Detergent 5kg", "category": "Cleaning", "unit": "bag", "price": 850.0},
    {"name": "Bar Soap (Box of 12)", "category": "Cleaning", "unit": "box", "price": 420.0},
    {"name": "Hand Sanitizer 5L", "category": "Cleaning", "unit": "bottle", "price": 1200.0},
    {"name": "Bleach 5L", "category": "Cleaning", "unit": "bottle", "price": 350.0},
    {"name": "Floor Cleaner 5L", "category": "Cleaning", "unit": "bottle", "price": 400.0},

    # Paper Products
    {"name": "Paper Napkins (Pack of 500)", "category": "Paper Products", "unit": "pack", "price": 650.0},
    {"name": "Paper Towels (Pack of 6)", "category": "Paper Products", "unit": "pack", "price": 450.0},
    {"name": "Tissue Paper (Box of 100)", "category": "Paper Products", "unit": "box", "price": 180.0},
]


async def seed_database(session: AsyncSession):
    """Seed the database with demo data."""
    # Check if already seeded
    result = await session.execute(select(Customer).limit(1))
    if result.scalar_one_or_none():
        print("Database already seeded, skipping...")
        return

    print("Seeding database with demo data...")

    # Add customers
    for customer_data in CUSTOMERS:
        customer = Customer(**customer_data)
        session.add(customer)

    # Add products
    for product_data in PRODUCTS:
        product = Product(**product_data)
        session.add(product)

    await session.commit()
    print(f"Seeded {len(CUSTOMERS)} customers and {len(PRODUCTS)} products")


async def reset_and_seed(session: AsyncSession):
    """Reset and reseed the database."""
    from .models import Order, OrderItem, Message, Conversation

    # Delete in order due to foreign keys
    await session.execute(OrderItem.__table__.delete())
    await session.execute(Order.__table__.delete())
    await session.execute(Message.__table__.delete())
    await session.execute(Conversation.__table__.delete())
    await session.execute(Customer.__table__.delete())
    await session.execute(Product.__table__.delete())
    await session.commit()

    # Reseed
    for customer_data in CUSTOMERS:
        customer = Customer(**customer_data)
        session.add(customer)

    for product_data in PRODUCTS:
        product = Product(**product_data)
        session.add(product)

    await session.commit()
    print(f"Reset and seeded {len(CUSTOMERS)} customers and {len(PRODUCTS)} products")
