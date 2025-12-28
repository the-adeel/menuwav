from openpyxl import load_workbook
from openpyxl_image_loader import SheetImageLoader
from pathlib import Path
from typing import List, Optional, Tuple
from decimal import Decimal, InvalidOperation
import uuid
import time

from models.menu import Menu
from models.menu_item import MenuItem
from models.restaurant import Restaurant

# Base upload directory
UPLOAD_BASE_DIR = Path("uploads/images")

# Expected column headers
EXPECTED_HEADERS = [
    "Menu Name",
    "Item Name",
    "Item Description",
    "Item Price",
    "Item Image"
]


class MenuImportError:
    """Represents an error during menu import"""
    def __init__(self, row: int, item_name: str, error: str):
        self.row = row
        self.item_name = item_name
        self.error = error
    
    def to_dict(self):
        return {
            "row": self.row,
            "item_name": self.item_name,
            "error": self.error
        }


class ImportResult:
    """Result of import operation"""
    def __init__(self):
        self.imported_items = 0
        self.imported_addons = 0
        self.skipped_items = 0
        self.errors: List[MenuImportError] = []
    
    def to_dict(self):
        return {
            "success": len(self.errors) == 0,
            "imported_items": self.imported_items,
            "imported_addons": self.imported_addons,
            "skipped_items": self.skipped_items,
            "errors": [error.to_dict() for error in self.errors]
        }


def validate_headers(worksheet) -> Optional[str]:
    """Validate that the Excel file has the correct headers"""
    if worksheet.max_row < 1:
        return "Excel file is empty"
    
    headers = []
    for col in range(1, min(len(EXPECTED_HEADERS) + 1, worksheet.max_column + 1)):
        cell_value = worksheet.cell(row=1, column=col).value
        headers.append(str(cell_value).strip() if cell_value else "")
    
    # Check if we have at least the required columns
    if len(headers) < len(EXPECTED_HEADERS):
        return f"Expected at least {len(EXPECTED_HEADERS)} columns, found {len(headers)}"
    
    # Check header names (case-insensitive)
    for i, expected in enumerate(EXPECTED_HEADERS):
        if i < len(headers):
            if headers[i].lower() != expected.lower():
                return f"Column {i+1} should be '{expected}', found '{headers[i]}'"
    
    return None


def get_cell_value(worksheet, row: int, col: int) -> Optional[str]:
    """Get cell value as string, returning None if empty"""
    cell = worksheet.cell(row=row, column=col)
    if cell.value is None:
        return None
    return str(cell.value).strip() if str(cell.value).strip() else None


def extract_image_from_cell(image_loader: SheetImageLoader, cell_reference: str, restaurant_id: int, prefix: str = "menu_item") -> Optional[str]:
    """Extract image from Excel cell and save it to file system"""
    try:
        image = image_loader.get(cell_reference)
        if image is None:
            return None
        
        # Create restaurant-specific directory
        restaurant_dir = UPLOAD_BASE_DIR / f"restaurant_{restaurant_id}"
        restaurant_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        
        # Determine file extension from image format
        if hasattr(image, 'format'):
            ext_map = {'PNG': '.png', 'JPEG': '.jpg', 'GIF': '.gif', 'WEBP': '.webp'}
            ext = ext_map.get(image.format, '.png')
        else:
            ext = '.png'
        
        filename = f"{prefix}_{timestamp}_{unique_id}{ext}"
        file_path = restaurant_dir / filename
        
        # Save image
        image.save(file_path)
        
        # Return relative path for URL
        return f"/uploads/images/restaurant_{restaurant_id}/{filename}"
    except Exception as e:
        # If image extraction fails, return None (image is optional)
        return None


def parse_price(price_str: Optional[str]) -> Tuple[Optional[Decimal], Optional[str]]:
    """Parse price string to Decimal, returning error message if invalid"""
    if not price_str:
        return None, "Price is required"
    
    try:
        # Remove any currency symbols and whitespace
        cleaned = price_str.replace('$', '').replace(',', '').strip()
        price = Decimal(cleaned)
        if price < 0:
            return None, "Price cannot be negative"
        return price, None
    except (InvalidOperation, ValueError):
        return None, f"Invalid price format: {price_str}"




async def import_menu_from_excel(file_path: str, restaurant: Restaurant) -> ImportResult:
    """
    Import menu items from Excel file
    
    Args:
        file_path: Path to the Excel file
        restaurant: Restaurant object to import items for
    
    Returns:
        ImportResult with statistics and errors
    """
    result = ImportResult()
    
    try:
        # Load workbook
        workbook = load_workbook(file_path)
        worksheet = workbook.active
        
        # Validate headers
        header_error = validate_headers(worksheet)
        if header_error:
            result.errors.append(MenuImportError(1, "", f"Header validation failed: {header_error}"))
            return result
        
        # Initialize image loader
        image_loader = SheetImageLoader(worksheet)
        
        # Process rows (starting from row 2, as row 1 is headers)
        for row_num in range(2, worksheet.max_row + 1):
            try:
                # Get cell values
                menu_name = get_cell_value(worksheet, row_num, 1)  # Column A
                item_name = get_cell_value(worksheet, row_num, 2)  # Column B
                item_description = get_cell_value(worksheet, row_num, 3)  # Column C
                item_price_str = get_cell_value(worksheet, row_num, 4)  # Column D
                item_image_cell = worksheet.cell(row=row_num, column=5)  # Column E
                
                # Validate required fields
                if not menu_name:
                    result.errors.append(MenuImportError(
                        row_num,
                        item_name or "Unknown",
                        "Menu Name is required"
                    ))
                    continue
                
                if not item_name:
                    result.errors.append(MenuImportError(
                        row_num,
                        "Unknown",
                        "Item Name is required"
                    ))
                    continue
                
                # Check if menu exists
                menu = await Menu.get_or_none(name=menu_name, restaurant=restaurant)
                if not menu:
                    result.errors.append(MenuImportError(
                        row_num,
                        item_name,
                        f"Menu '{menu_name}' does not exist"
                    ))
                    continue
                
                # Check for duplicate item (skip if exists)
                existing_item = await MenuItem.get_or_none(name=item_name, menu=menu)
                if existing_item:
                    result.skipped_items += 1
                    continue
                
                # Parse price
                item_price, price_error = parse_price(item_price_str)
                if price_error:
                    result.errors.append(MenuImportError(
                        row_num,
                        item_name,
                        price_error
                    ))
                    continue
                
                # Extract item image if present (try to extract from cell E)
                item_image_url = None
                cell_ref = item_image_cell.coordinate
                item_image_url = extract_image_from_cell(
                    image_loader, cell_ref, restaurant.id, "menu_item"
                )
                
                # Create menu item
                await MenuItem.create(
                    menu=menu,
                    name=item_name,
                    description=item_description,
                    price=item_price,
                    image_url=item_image_url
                )
                result.imported_items += 1
            
            except Exception as e:
                result.errors.append(MenuImportError(
                    row_num,
                    item_name or "Unknown",
                    f"Unexpected error: {str(e)}"
                ))
                continue
        
        workbook.close()
        return result
    
    except Exception as e:
        result.errors.append(MenuImportError(0, "", f"Failed to process Excel file: {str(e)}"))
        return result

