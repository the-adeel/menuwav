import subprocess
import platform
import tempfile
import os
import time
import shutil
from typing import List, Optional, Tuple

def _check_command_available(command: str) -> bool:
    """Check if a command is available in the system PATH."""
    return shutil.which(command) is not None

def _get_test_printers(system: str) -> List[str]:
    """
    Get list of test/virtual printers available on the system.
    These are always included to allow testing without physical printers.
    """
    test_printers = []
    
    if system == "Windows":
        # Check for Microsoft Print to PDF
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Printer | Where-Object {$_.Name -like '*PDF*'} | Select-Object -ExpandProperty Name"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                pdf_printers = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                test_printers.extend(pdf_printers)
        except Exception:
            pass
        
        # Always add Microsoft Print to PDF if not already found
        if "Microsoft Print to PDF" not in test_printers:
            test_printers.append("Microsoft Print to PDF")
    
    elif system == "Linux":
        # Check for CUPS-PDF printer
        try:
            result = subprocess.run(
                ["lpstat", "-p", "CUPS-PDF"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                test_printers.append("CUPS-PDF")
        except Exception:
            pass
        
        # Also check for other common PDF printers
        try:
            result = subprocess.run(
                ["lpstat", "-a"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        printer_name = line.split()[0] if line.split() else ""
                        if printer_name and ("PDF" in printer_name.upper() or "pdf" in printer_name.lower()):
                            if printer_name not in test_printers:
                                test_printers.append(printer_name)
        except Exception:
            pass
        
        # Add generic PDF printer if no PDF printer found
        if not test_printers:
            test_printers.append("PDF Printer")
    
    return test_printers

def list_printers() -> List[str]:
    """
    Detect and list available printers on the system.
    Returns a list of printer names, always including test/virtual printers.
    """
    printers = []
    system = platform.system()
    
    print(f"[PRINTER_DETECT] Starting printer detection on {system}")
    print(f"[PRINTER_DETECT] Platform: {platform.platform()}")
    
    try:
        if system == "Windows":
            print("[PRINTER_DETECT] Detecting Windows printers...")
            
            # Try PowerShell first (more reliable)
            try:
                if _check_command_available("powershell"):
                    print("[PRINTER_DETECT] Trying PowerShell Get-Printer...")
                    result = subprocess.run(
                        ["powershell", "-Command", "Get-Printer | Select-Object -ExpandProperty Name"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    print(f"[PRINTER_DETECT] PowerShell return code: {result.returncode}")
                    if result.returncode == 0 and result.stdout.strip():
                        detected = [
                            line.strip() 
                            for line in result.stdout.strip().split('\n') 
                            if line.strip()
                        ]
                        printers.extend(detected)
                        print(f"[PRINTER_DETECT] Found {len(detected)} printers via PowerShell: {detected}")
                else:
                    print("[PRINTER_DETECT] PowerShell not available")
            except subprocess.TimeoutExpired:
                print("[PRINTER_DETECT] PowerShell command timed out")
            except Exception as e:
                print(f"[PRINTER_DETECT] PowerShell detection failed: {str(e)}")
            
            # Fallback to WMIC
            if not printers:
                try:
                    if _check_command_available("wmic"):
                        print("[PRINTER_DETECT] Trying WMIC...")
                        result = subprocess.run(
                            ["wmic", "printer", "get", "name"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        print(f"[PRINTER_DETECT] WMIC return code: {result.returncode}")
                        if result.returncode == 0:
                            detected = [
                                line.strip() 
                                for line in result.stdout.split('\n') 
                                if line.strip() and 'Name' not in line
                            ]
                            printers.extend(detected)
                            print(f"[PRINTER_DETECT] Found {len(detected)} printers via WMIC: {detected}")
                    else:
                        print("[PRINTER_DETECT] WMIC not available")
                except subprocess.TimeoutExpired:
                    print("[PRINTER_DETECT] WMIC command timed out")
                except Exception as e:
                    print(f"[PRINTER_DETECT] WMIC detection failed: {str(e)}")
                
        elif system == "Linux":
            print("[PRINTER_DETECT] Detecting Linux printers...")
            
            # Check if CUPS commands are available
            cups_available = _check_command_available("lpstat")
            lpinfo_available = _check_command_available("lpinfo")
            
            print(f"[PRINTER_DETECT] lpstat available: {cups_available}, lpinfo available: {lpinfo_available}")
            
            # Method 1: Try lpstat -p (list all printers)
            if cups_available:
                try:
                    print("[PRINTER_DETECT] Trying lpstat -p...")
                    result = subprocess.run(
                        ["lpstat", "-p"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    print(f"[PRINTER_DETECT] lpstat -p return code: {result.returncode}")
                    if result.returncode == 0:
                        detected = []
                        for line in result.stdout.split('\n'):
                            if line.startswith('printer '):
                                # Extract printer name: "printer PRINTER_NAME is idle..."
                                parts = line.split()
                                if len(parts) > 1:
                                    detected.append(parts[1])
                        if detected:
                            printers.extend(detected)
                            print(f"[PRINTER_DETECT] Found {len(detected)} printers via lpstat -p: {detected}")
                    else:
                        print(f"[PRINTER_DETECT] lpstat -p failed: {result.stderr}")
                except subprocess.TimeoutExpired:
                    print("[PRINTER_DETECT] lpstat -p command timed out")
                except Exception as e:
                    print(f"[PRINTER_DETECT] lpstat -p detection failed: {str(e)}")
            
            # Method 2: Try lpstat -a (list all accepting printers)
            if not printers and cups_available:
                try:
                    print("[PRINTER_DETECT] Trying lpstat -a...")
                    result = subprocess.run(
                        ["lpstat", "-a"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    print(f"[PRINTER_DETECT] lpstat -a return code: {result.returncode}")
                    if result.returncode == 0:
                        detected = []
                        for line in result.stdout.split('\n'):
                            if line.strip():
                                # Format: "PRINTER_NAME accepting requests..."
                                parts = line.split()
                                if len(parts) > 0:
                                    detected.append(parts[0])
                        if detected:
                            printers.extend(detected)
                            printers = list(set(printers))  # Remove duplicates
                            print(f"[PRINTER_DETECT] Found {len(detected)} printers via lpstat -a: {detected}")
                    else:
                        print(f"[PRINTER_DETECT] lpstat -a failed: {result.stderr}")
                except subprocess.TimeoutExpired:
                    print("[PRINTER_DETECT] lpstat -a command timed out")
                except Exception as e:
                    print(f"[PRINTER_DETECT] lpstat -a detection failed: {str(e)}")
            
            # Method 3: Try lpstat -d (get default printer)
            if cups_available:
                try:
                    print("[PRINTER_DETECT] Trying lpstat -d (default printer)...")
                    result = subprocess.run(
                        ["lpstat", "-d"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        # Format: "system default destination: PRINTER_NAME"
                        for line in result.stdout.split('\n'):
                            if 'default destination:' in line.lower():
                                parts = line.split('default destination:')
                                if len(parts) > 1:
                                    default_printer = parts[1].strip()
                                    if default_printer and default_printer not in printers:
                                        printers.append(default_printer)
                                        print(f"[PRINTER_DETECT] Found default printer: {default_printer}")
                except Exception as e:
                    print(f"[PRINTER_DETECT] lpstat -d detection failed: {str(e)}")
            
            # Method 4: Try lpinfo -v (list available printer devices)
            if lpinfo_available:
                try:
                    print("[PRINTER_DETECT] Trying lpinfo -v...")
                    result = subprocess.run(
                        ["lpinfo", "-v"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    print(f"[PRINTER_DETECT] lpinfo -v return code: {result.returncode}")
                    if result.returncode == 0:
                        # lpinfo -v shows devices, not printer names, but we can check if CUPS is working
                        if result.stdout.strip():
                            print("[PRINTER_DETECT] lpinfo -v shows CUPS is working, but no printer names available")
                except Exception as e:
                    print(f"[PRINTER_DETECT] lpinfo -v detection failed: {str(e)}")
            
            # Check CUPS service status
            try:
                print("[PRINTER_DETECT] Checking CUPS service status...")
                # Try systemctl if available
                if _check_command_available("systemctl"):
                    result = subprocess.run(
                        ["systemctl", "is-active", "cups"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        print("[PRINTER_DETECT] CUPS service is active")
                    else:
                        print("[PRINTER_DETECT] CUPS service is not active")
                # Try service command as fallback
                elif _check_command_available("service"):
                    result = subprocess.run(
                        ["service", "cups", "status"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    print(f"[PRINTER_DETECT] CUPS service status check: {result.returncode}")
            except Exception as e:
                print(f"[PRINTER_DETECT] CUPS service check failed: {str(e)}")
        
        # Always add test printers
        test_printers = _get_test_printers(system)
        print(f"[PRINTER_DETECT] Adding test printers: {test_printers}")
        for test_printer in test_printers:
            if test_printer not in printers:
                printers.append(test_printer)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_printers = []
        for printer in printers:
            if printer not in seen:
                seen.add(printer)
                unique_printers.append(printer)
        
        print(f"[PRINTER_DETECT] Final printer list ({len(unique_printers)} printers): {unique_printers}")
        return unique_printers
        
    except Exception as e:
        print(f"[PRINTER_DETECT] Error listing printers: {e}")
        import traceback
        print(f"[PRINTER_DETECT] Traceback: {traceback.format_exc()}")
        # Even on error, return test printers
        test_printers = _get_test_printers(system)
        print(f"[PRINTER_DETECT] Returning test printers only due to error: {test_printers}")
        return test_printers


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
                # Method 1: Use Windows 'print' command (skip if printer name has spaces - use PowerShell instead)
                # The Windows 'print' command has issues with printer names containing spaces
                # So we'll skip it and go straight to PowerShell for better reliability
                if ' ' not in printer_name:
                    try:
                        # For simple printer names without spaces, try the print command
                        print_cmd = ['print', f'/D:{printer_name}', temp_file_path]
                        print(f"[PRINT] Attempting Windows print command: {' '.join(print_cmd)}")
                        result = subprocess.run(
                            print_cmd,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        print(f"[PRINT] Print command return code: {result.returncode}")
                        print(f"[PRINT] Print command stdout: {result.stdout}")
                        print(f"[PRINT] Print command stderr: {result.stderr}")
                        
                        # Check for errors even if return code is 0 (Windows print can return 0 with error messages)
                        stdout_lower = result.stdout.lower() if result.stdout else ""
                        stderr_lower = result.stderr.lower() if result.stderr else ""
                        has_error = (
                            "invalid" in stdout_lower or 
                            "error" in stdout_lower or 
                            "invalid" in stderr_lower or 
                            "error" in stderr_lower or
                            result.returncode != 0
                        )
                        
                        if not has_error and result.returncode == 0:
                            # Wait a moment for print job to start before deleting file
                            time.sleep(0.5)
                            print("[PRINT] Print command succeeded")
                            return (True, None)
                        else:
                            error_msg = result.stdout.strip() or result.stderr.strip() or f"Print command failed with return code {result.returncode}"
                            print(f"[PRINT] Print command failed: {error_msg}, trying PowerShell")
                    except Exception as print_error:
                        print(f"[PRINT] Print command exception: {str(print_error)}, trying PowerShell")
                        pass
                else:
                    print(f"[PRINT] Printer name contains spaces, skipping Windows print command, using PowerShell instead")
                
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

