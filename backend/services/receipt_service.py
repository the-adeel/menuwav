from decimal import Decimal
from datetime import datetime
from models.order import Order
from models.restaurant import Restaurant

# ESC/POS commands for thermal printers
ESC = '\x1B'
GS = '\x1D'

# Common ESC/POS commands
INIT_PRINTER = ESC + '@'
CENTER_ALIGN = ESC + 'a' + '\x01'
LEFT_ALIGN = ESC + 'a' + '\x00'
BOLD_ON = ESC + 'E' + '\x01'
BOLD_OFF = ESC + 'E' + '\x00'
CUT_PAPER = GS + 'V' + 'B' + '\x00'
LINE_FEED = '\n'
DOUBLE_HEIGHT = ESC + 'd' + '\x01'
NORMAL_HEIGHT = ESC + 'd' + '\x00'

# Receipt width for 80mm thermal printer (approximately 48 characters)
RECEIPT_WIDTH = 48


def center_text(text: str, width: int = RECEIPT_WIDTH) -> str:
    """Center text within the receipt width."""
    text = text.strip()
    if len(text) >= width:
        return text[:width]
    padding = (width - len(text)) // 2
    return ' ' * padding + text


def format_line(left: str, right: str, width: int = RECEIPT_WIDTH) -> str:
    """Format a line with left and right aligned text."""
    left = str(left)[:width-10]
    right = str(right)[:10]
    padding = width - len(left) - len(right)
    if padding < 1:
        padding = 1
    return left + ' ' * padding + right


def format_price(price) -> str:
    """Format price to 2 decimal places."""
    if isinstance(price, Decimal):
        return f"${float(price):.2f}"
    try:
        return f"${float(price):.2f}"
    except:
        return "$0.00"


async def generate_receipt_content(order: Order) -> str:
    """
    Generate formatted receipt content for thermal printer (80mm ESC/POS).
    Returns formatted string ready for printing.
    """
    # Fetch related data
    restaurant = await order.restaurant
    order_items = await order.items.all().prefetch_related("menu_item", "addons", "meal_items")
    
    # Build receipt content
    receipt_lines = []
    
    # Initialize printer
    receipt_lines.append(INIT_PRINTER)
    
    # Header - Restaurant name (centered, bold, double height for POS)
    receipt_lines.append(CENTER_ALIGN)
    receipt_lines.append(BOLD_ON)
    receipt_lines.append(center_text(restaurant.name.upper()))
    receipt_lines.append(BOLD_OFF)
    receipt_lines.append(LINE_FEED)
    
    # Restaurant address and contact (centered, compact for POS)
    if restaurant.address:
        receipt_lines.append(center_text(restaurant.address))
        receipt_lines.append(LINE_FEED)
    if restaurant.phone:
        receipt_lines.append(center_text(restaurant.phone))
        receipt_lines.append(LINE_FEED)
    
    # Separator line
    receipt_lines.append(LEFT_ALIGN)
    receipt_lines.append('=' * RECEIPT_WIDTH)
    receipt_lines.append(LINE_FEED)
    
    # Order information (left aligned)
    receipt_lines.append(format_line("Order #:", order.order_number or f"#{order.id}"))
    receipt_lines.append(LINE_FEED)
    
    # Format date/time
    order_date = order.created_at
    if isinstance(order_date, str):
        try:
            order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
        except:
            # Fallback if parsing fails
            order_date = datetime.now()
    elif hasattr(order_date, 'strftime'):
        # Already a datetime object
        pass
    else:
        order_date = datetime.now()
    date_str = order_date.strftime("%Y-%m-%d %H:%M:%S")
    receipt_lines.append(format_line("Date:", date_str))
    receipt_lines.append(LINE_FEED)
    
    # Order type
    receipt_lines.append(format_line("Type:", order.order_type.value.title()))
    receipt_lines.append(LINE_FEED)
    
    # Table number (if applicable)
    if order.table_number:
        receipt_lines.append(format_line("Table:", f"#{order.table_number}"))
        receipt_lines.append(LINE_FEED)
    
    # Customer information (if available)
    if order.customer_name:
        receipt_lines.append(format_line("Customer:", order.customer_name))
        receipt_lines.append(LINE_FEED)
    if order.customer_phone:
        receipt_lines.append(format_line("Phone:", order.customer_phone))
        receipt_lines.append(LINE_FEED)
    
    # Separator
    receipt_lines.append('-' * RECEIPT_WIDTH)
    receipt_lines.append(LINE_FEED)
    
    # Order items (compact for POS)
    receipt_lines.append(BOLD_ON)
    receipt_lines.append("ITEMS")
    receipt_lines.append(BOLD_OFF)
    receipt_lines.append(LINE_FEED)
    receipt_lines.append('-' * RECEIPT_WIDTH)
    receipt_lines.append(LINE_FEED)
    
    subtotal = Decimal('0.00')
    
    for order_item in order_items:
        menu_item = await order_item.menu_item
        
        # Item name and quantity
        item_line = f"{order_item.quantity}x {menu_item.name}"
        if len(item_line) > RECEIPT_WIDTH - 12:
            item_line = item_line[:RECEIPT_WIDTH - 12] + "..."
        receipt_lines.append(item_line)
        receipt_lines.append(LINE_FEED)
        
        # Calculate item price
        item_price = Decimal(str(order_item.price_at_time)) * order_item.quantity
        
        # Addons
        addons = await order_item.addons.all().prefetch_related("addon")
        for addon_rel in addons:
            addon = await addon_rel.addon
            addon_price = Decimal(str(addon_rel.price_at_time)) * addon_rel.quantity
            item_price += addon_price
            
            addon_line = f"  + {addon_rel.quantity}x {addon.name}"
            if len(addon_line) > RECEIPT_WIDTH - 12:
                addon_line = addon_line[:RECEIPT_WIDTH - 12] + "..."
            receipt_lines.append(addon_line)
            receipt_lines.append(LINE_FEED)
            
            if addon_price > 0:
                receipt_lines.append(format_line("", format_price(addon_price)))
                receipt_lines.append(LINE_FEED)
        
        # Meal items
        meal_items = await order_item.meal_items.all().prefetch_related("meal_item")
        if meal_items:
            receipt_lines.append("  Meal Items:")
            receipt_lines.append(LINE_FEED)
            for meal_item_rel in meal_items:
                meal_item = await meal_item_rel.meal_item
                meal_price = Decimal(str(meal_item_rel.price_at_time)) * meal_item_rel.quantity
                item_price += meal_price
                
                meal_line = f"    - {meal_item_rel.quantity}x {meal_item.name}"
                if len(meal_line) > RECEIPT_WIDTH - 12:
                    meal_line = meal_line[:RECEIPT_WIDTH - 12] + "..."
                receipt_lines.append(meal_line)
                receipt_lines.append(LINE_FEED)
                
                if meal_price > 0:
                    receipt_lines.append(format_line("", format_price(meal_price)))
                    receipt_lines.append(LINE_FEED)
            
            # Meal charge
            if order_item.meal_charge and Decimal(str(order_item.meal_charge)) > 0:
                meal_charge = Decimal(str(order_item.meal_charge)) * order_item.quantity
                item_price += meal_charge
                receipt_lines.append(format_line("  Meal Charge:", format_price(meal_charge)))
                receipt_lines.append(LINE_FEED)
        
        # Item total
        receipt_lines.append(format_line("", format_price(item_price)))
        receipt_lines.append(LINE_FEED)
        
        subtotal += item_price
    
    # Separator
    receipt_lines.append('=' * RECEIPT_WIDTH)
    receipt_lines.append(LINE_FEED)
    
    # Totals (compact for POS)
    receipt_lines.append(format_line("Subtotal:", format_price(subtotal)))
    receipt_lines.append(LINE_FEED)
    
    # Payment information
    receipt_lines.append('=' * RECEIPT_WIDTH)
    receipt_lines.append(LINE_FEED)
    receipt_lines.append(BOLD_ON)
    receipt_lines.append(format_line("TOTAL:", format_price(order.total)))
    receipt_lines.append(BOLD_OFF)
    receipt_lines.append(LINE_FEED)
    receipt_lines.append('=' * RECEIPT_WIDTH)
    receipt_lines.append(LINE_FEED)
    
    # Payment method and status (compact)
    if order.payment_method:
        receipt_lines.append(format_line("Payment:", order.payment_method.value.title()))
        receipt_lines.append(LINE_FEED)
    receipt_lines.append(format_line("Status:", order.payment_status.value.title()))
    receipt_lines.append(LINE_FEED)
    
    # Footer (compact for POS)
    receipt_lines.append(LINE_FEED)
    receipt_lines.append(CENTER_ALIGN)
    receipt_lines.append("Thank you!")
    receipt_lines.append(LINE_FEED)
    receipt_lines.append(LINE_FEED)
    
    # Cut paper
    receipt_lines.append(CUT_PAPER)
    
    return ''.join(receipt_lines)

