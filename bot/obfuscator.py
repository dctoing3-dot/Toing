"""
Ironbrew 2 Obfuscator - COMPLETE FIXED VERSION
Handles Ironbrew 2's complex multi-step obfuscation process
"""

import asyncio
import os
import uuid
import io
import shutil
import glob

# Paths
IRONBREW_PATH = os.getenv('IRONBREW_PATH', '/opt/ironbrew-2')
IRONBREW_PUBLISH = os.path.join(IRONBREW_PATH, 'publish')
IRONBREW_CLI_DLL = os.path.join(IRONBREW_PUBLISH, 'IronBrew2 CLI.dll')
TEMP_DIR = '/app/temp'

print(f"[Obfuscator] IRONBREW_PATH: {IRONBREW_PATH}")
print(f"[Obfuscator] PUBLISH DIR: {IRONBREW_PUBLISH}")
print(f"[Obfuscator] CLI DLL exists: {os.path.exists(IRONBREW_CLI_DLL)}")


def check_dependencies():
    """Check all required tools"""
    import subprocess
    
    deps = {}
    
    # Check luac
    try:
        result = subprocess.run(['luac', '-v'], capture_output=True, text=True)
        deps['luac'] = 'OK' if result.returncode == 0 else 'ERROR'
    except:
        deps['luac'] = 'NOT FOUND'
    
    # Check luajit
    try:
        result = subprocess.run(['luajit', '-v'], capture_output=True, text=True)
        deps['luajit'] = 'OK' if result.returncode == 0 else 'ERROR'
    except:
        deps['luajit'] = 'NOT FOUND'
    
    # Check lua
    try:
        result = subprocess.run(['lua', '-v'], capture_output=True, text=True)
        deps['lua'] = 'OK' if result.returncode == 0 else 'ERROR'
    except:
        deps['lua'] = 'NOT FOUND'
    
    # Check LuaSrcDiet files
    minifier_path = os.path.join(IRONBREW_PATH, 'Lua', 'Minifier')
    required_files = ['luasrcdiet.lua', 'llex.lua', 'lparser.lua', 'optlex.lua', 'optparser.lua']
    
    for f in required_files:
        fpath = os.path.join(minifier_path, f)
        deps[f] = 'OK' if os.path.exists(fpath) else 'MISSING'
    
    print(f"[Obfuscator] Dependencies: {deps}")
    return deps


# Run dependency check on startup
check_dependencies()


async def obfuscate_lua(lua_content: str, filename: str) -> tuple:
    """
    Obfuscate Lua content using Ironbrew 2
    
    Ironbrew 2 process:
    1. luac - compile & verify syntax
    2. luajit + luasrcdiet - strip comments
    3. Encrypt strings
    4. luac - compile encrypted
    5. Obfuscate bytecode
    6. Generate VM
    7. luajit + luasrcdiet - minify
    8. Output to out.lua
    
    Returns:
        tuple: (result_io, success, error_message)
    """
    
    unique_id = str(uuid.uuid4())[:8]
    
    # Store original sizes for comparison
    input_size = len(lua_content)
    
    try:
        # ============================================
        # Create input file in IRONBREW publish directory
        # (karena path relative ke ../Lua/Minifier)
        # ============================================
        input_filename = f"{unique_id}_input.lua"
        input_path = os.path.join(IRONBREW_PUBLISH, input_filename)
        
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(lua_content)
        
        print(f"[Obfuscator] Created input: {input_path}")
        print(f"[Obfuscator] Input size: {input_size} bytes")
        
        # ============================================
        # Run Ironbrew 2 CLI
        # ============================================
        cmd = f'dotnet "{IRONBREW_CLI_DLL}" "{input_path}"'
        print(f"[Obfuscator] Running: {cmd}")
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=IRONBREW_PUBLISH  # PENTING: Jalankan dari publish dir
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=300.0  # 5 menit
            )
        except asyncio.TimeoutError:
            process.kill()
            cleanup_files(unique_id)
            return (None, False, "⏱️ Timeout: Proses terlalu lama (>5 menit)")
        
        stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
        stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
        
        print(f"[Obfuscator] Exit code: {process.returncode}")
        print(f"[Obfuscator] STDOUT:\n{stdout_text[:1000]}")
        if stderr_text:
            print(f"[Obfuscator] STDERR:\n{stderr_text[:500]}")
        
        # ============================================
        # Find output file (out.lua)
        # ============================================
        result_content = None
        output_found = None
        
        # Possible output locations
        possible_outputs = [
            os.path.join(IRONBREW_PUBLISH, 'out.lua'),
            os.path.join(IRONBREW_PATH, 'out.lua'),
            os.path.join(IRONBREW_PUBLISH, f'{unique_id}_out.lua'),
        ]
        
        # List all .lua files in publish dir
        print(f"[Obfuscator] Files in publish dir:")
        for f in os.listdir(IRONBREW_PUBLISH):
            if f.endswith('.lua'):
                fpath = os.path.join(IRONBREW_PUBLISH, f)
                fsize = os.path.getsize(fpath)
                print(f"  - {f} ({fsize} bytes)")
                
                # Add to possible outputs if it's not our input
                if f != input_filename:
                    possible_outputs.append(fpath)
        
        # Check each possible output
        for output_path in possible_outputs:
            if os.path.exists(output_path):
                try:
                    # Ironbrew uses latin-1 encoding
                    with open(output_path, 'r', encoding='latin-1', errors='ignore') as f:
                        content = f.read()
                    
                    # Verify it's different from input
                    if content and len(content) > 100 and content != lua_content:
                        # Check for IronBrew watermark
                        if "IronBrew" in content:
                            result_content = content
                            output_found = output_path
                            print(f"[Obfuscator] ✅ Found valid output: {output_path}")
                            print(f"[Obfuscator] ✅ Has IronBrew watermark!")
                            break
                        elif len(content) > input_size:
                            # Obfuscated code is usually larger
                            result_content = content
                            output_found = output_path
                            print(f"[Obfuscator] ✅ Found output (larger): {output_path}")
                            break
                except Exception as e:
                    print(f"[Obfuscator] Error reading {output_path}: {e}")
        
        # ============================================
        # Cleanup temporary files
        # ============================================
        cleanup_files(unique_id)
        
        # ============================================
        # Return result
        # ============================================
        if result_content:
            result_size = len(result_content)
            ratio = result_size / input_size if input_size > 0 else 0
            
            print(f"[Obfuscator] ✅ Success!")
            print(f"[Obfuscator] Size: {input_size} → {result_size} bytes ({ratio:.2f}x)")
            
            result_io = io.BytesIO(result_content.encode('latin-1'))
            return (result_io, True, None)
        
        # ============================================
        # Build error message
        # ============================================
        error_parts = []
        
        if process.returncode != 0:
            error_parts.append(f"Exit code: {process.returncode}")
        
        # Parse common errors
        combined_output = stdout_text + stderr_text
        
        if "Invalid input file" in combined_output:
            error_parts.append("❌ File tidak valid")
        elif "not found" in combined_output.lower():
            error_parts.append("❌ Dependency tidak ditemukan (luac/luajit)")
        elif "error" in combined_output.lower():
            # Extract error line
            for line in combined_output.split('\n'):
                if 'error' in line.lower():
                    error_parts.append(line.strip())
                    break
        
        if stderr_text:
            error_parts.append(f"Error: {stderr_text[:300]}")
        
        if not error_parts:
            error_parts.append("Tidak ada output. Kemungkinan syntax error di Lua file.")
            error_parts.append(f"Output: {stdout_text[:300]}")
        
        return (None, False, "\n".join(error_parts))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        cleanup_files(unique_id)
        return (None, False, f"Exception: {str(e)}")


def cleanup_files(unique_id: str):
    """Clean up temporary files created by Ironbrew"""
    
    files_to_clean = [
        # Input file
        os.path.join(IRONBREW_PUBLISH, f'{unique_id}_input.lua'),
        # Ironbrew temp files
        os.path.join(IRONBREW_PUBLISH, 't0.lua'),
        os.path.join(IRONBREW_PUBLISH, 't1.lua'),
        os.path.join(IRONBREW_PUBLISH, 't2.lua'),
        os.path.join(IRONBREW_PUBLISH, 't3.lua'),
        os.path.join(IRONBREW_PUBLISH, 'luac.out'),
        os.path.join(IRONBREW_PUBLISH, 'out.lua'),
    ]
    
    for fpath in files_to_clean:
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
        except:
            pass
