import subprocess
import platform
import tempfile
import os
import time
from typing import List, Optional

def list_printers() -> List[str]:
    """
    Detect and list available printers on the system.
    Returns a list of printer names.
    """
    try:
        system = platform.system()
        
        if system == "Windows":
            # Try PowerShell first (more reliable)
            try:
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Printer | Select-Object -ExpandProperty Name"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    printers = [
                        line.strip() 
                        for line in result.stdout.strip().split('\n') 
                        if line.strip()
                    ]
                    return printers
            except Exception:
                pass
            
            # Fallback to WMIC
            try:
                result = subprocess.run(
                    ["wmic", "printer", "get", "name"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    printers = [
                        line.strip() 
                        for line in result.stdout.split('\n') 
                        if line.strip() and 'Name' not in line
                    ]
                    return printers
            except Exception:
                pass
                
        elif system == "Linux":
            # Try lpstat -p (list printers)
            try:
                result = subprocess.run(
                    ["lpstat", "-p"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    printers = []
                    for line in result.stdout.split('\n'):
                        if line.startswith('printer '):
                            # Extract printer name: "printer PRINTER_NAME is idle..."
                            parts = line.split()
                            if len(parts) > 1:
                                printers.append(parts[1])
                    return printers
            except Exception:
                pass
            
            # Fallback to lpstat -a (list all available printers)
            try:
                result = subprocess.run(
                    ["lpstat", "-a"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    printers = []
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            # Format: "PRINTER_NAME accepting requests..."
                            parts = line.split()
                            if len(parts) > 0:
                                printers.append(parts[0])
                    return list(set(printers))  # Remove duplicates
            except Exception:
                pass
        
        return []
    except Exception as e:
        print(f"Error listing printers: {e}")
        return []


def print_receipt(printer_name: str, receipt_content: str) -> tuple[bool, Optional[str]]:
    """
    Print receipt content to the specified printer automatically.
    Saves file temporarily on server, prints without prompts, then deletes file.
    Returns (success: bool, error_message: Optional[str])
    """
    temp_file_path = None
    try:
        system = platform.system()
        print(f"[PRINT] Starting print job for printer: {printer_name} on {system}")
        
        if system == "Windows":
            # Create temporary file with receipt content (saved on server)
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
                temp_file.write(receipt_content)
                temp_file.flush()
                temp_file_path = temp_file.name
            
            # Ensure file is written and exists
            if not os.path.exists(temp_file_path):
                return (False, "Failed to create temporary file")
            
            # Wait a moment to ensure file is fully written
            time.sleep(0.1)
            
            try:
                # Method 1: Use Windows 'print' command (most reliable, no prompts)
                # Format: print /D:"printer_name" file_path
                try:
                    # Escape printer name for command line
                    escaped_printer = printer_name.replace('"', '""')
                    # Don't use CREATE_NO_WINDOW so print queue icon shows in taskbar
                    print(f"[PRINT] Attempting Windows print command: print /D:\"{escaped_printer}\" {temp_file_path}")
                    result = subprocess.run(
                        ['print', f'/D:"{escaped_printer}"', temp_file_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    print(f"[PRINT] Print command return code: {result.returncode}")
                    print(f"[PRINT] Print command stdout: {result.stdout}")
                    print(f"[PRINT] Print command stderr: {result.stderr}")
                    if result.returncode == 0:
                        # Wait a moment for print job to start before deleting file
                        time.sleep(0.5)
                        print("[PRINT] Print command succeeded")
                        return (True, None)
                    else:
                        print(f"[PRINT] Print command failed with code {result.returncode}, trying PowerShell")
                    # If print command fails, try PowerShell method
                except Exception as print_error:
                    print(f"[PRINT] Print command exception: {str(print_error)}")
                    pass
                
                # Method 2: Use PowerShell Out-Printer with silent flags (no prompts)
                try:
                    # Escape printer name and file path for PowerShell
                    escaped_printer = printer_name.replace("'", "''").replace('"', '`"')
                    escaped_path = temp_file_path.replace("'", "''").replace('"', '`"')
                    
                    # Use silent PowerShell flags to prevent any dialogs or prompts
                    # -NoProfile: Don't load profile (faster, avoids prompts)
                    # -NonInteractive: Prevents interactive prompts
                    # -WindowStyle Hidden: Hide window completely
                    # -Command: Execute command silently
                    command = f'$ErrorActionPreference = "Stop"; $content = Get-Content -Path "{escaped_path}" -Raw -Encoding UTF8; $content | Out-Printer -Name "{escaped_printer}"'
                    # Use NonInteractive but allow window to show print queue icon
                    print(f"[PRINT] Attempting PowerShell print command")
                    result = subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    print(f"[PRINT] PowerShell return code: {result.returncode}")
                    print(f"[PRINT] PowerShell stdout: {result.stdout}")
                    print(f"[PRINT] PowerShell stderr: {result.stderr}")
                    if result.returncode == 0:
                        # Wait a moment for print job to start before deleting file
                        time.sleep(0.5)
                        print("[PRINT] PowerShell print succeeded")
                        return (True, None)
                    else:
                        error_msg = result.stderr.strip() or result.stdout.strip()
                        print(f"[PRINT] PowerShell print failed: {error_msg}")
                        if "printer" in error_msg.lower() and "not found" in error_msg.lower():
                            return (False, f"Printer '{printer_name}' not found. Please check printer name.")
                        return (False, f"Print failed: {error_msg}")
                except subprocess.TimeoutExpired:
                    print("[PRINT] Print job timed out")
                    return (False, "Print job timed out")
                except Exception as ps_error:
                    print(f"[PRINT] PowerShell exception: {str(ps_error)}")
                    return (False, f"Print failed: {str(ps_error)}")
            finally:
                # Always clean up temp file after a short delay
                try:
                    if temp_file_path and os.path.exists(temp_file_path):
                        # Wait a bit longer to ensure print job has started
                        time.sleep(1)
                        os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    # Log but don't fail - file will be cleaned up eventually
                    print(f"Warning: Failed to delete temp file {temp_file_path}: {cleanup_error}")
                    
        elif system == "Linux":
            # Create temporary file with receipt content (saved on server)
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
                temp_file.write(receipt_content)
                temp_file.flush()
                temp_file_path = temp_file.name
            
            try:
                # Use lp command to print from file (no prompts)
                result = subprocess.run(
                    ["lp", "-d", printer_name, temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Wait a moment for print job to start before deleting file
                    time.sleep(0.5)
                    return (True, None)
                else:
                    return (False, f"Print failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                return (False, "Print job timed out")
            except Exception as e:
                return (False, f"Print failed: {str(e)}")
            finally:
                # Clean up temp file
                try:
                    if temp_file_path and os.path.exists(temp_file_path):
                        time.sleep(0.5)  # Wait a moment to ensure print job started
                        os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to delete temp file {temp_file_path}: {cleanup_error}")
        
        return (False, f"Unsupported operating system: {system}")
        
    except Exception as e:
        print(f"[PRINT] Exception occurred: {str(e)}")
        import traceback
        print(f"[PRINT] Traceback: {traceback.format_exc()}")
        # Clean up temp file if it exists
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except Exception:
            pass
        return (False, f"Error printing receipt: {str(e)}")

