"""
Ironbrew 2 Obfuscator Module - COMPLETE FIX
Correctly handles Ironbrew 2's file-based output
"""

import asyncio
import os
import uuid
import io
import shutil
import hashlib

# Paths
IRONBREW_PATH = os.getenv('IRONBREW_PATH', '/opt/ironbrew-2')
IRONBREW_CLI_DLL = os.path.join(IRONBREW_PATH, 'publish', 'IronBrew2 CLI.dll')
TEMP_DIR = '/app/temp'

print(f"[Obfuscator] IRONBREW_PATH: {IRONBREW_PATH}")
print(f"[Obfuscator] CLI DLL: {IRONBREW_CLI_DLL}")
print(f"[Obfuscator] DLL Exists: {os.path.exists(IRONBREW_CLI_DLL)}")

# Check dependencies
def check_dependencies():
    """Check if all required tools are available"""
    deps = {
        'luac': os.system('which luac > /dev/null 2>&1') == 0,
        'luajit': os.system('which luajit > /dev/null 2>&1') == 0,
        'lua': os.system('which lua > /dev/null 2>&1') == 0,
    }
    print(f"[Obfuscator] Dependencies: {deps}")
    return deps

check_dependencies()


def get_hash(content: str) -> str:
    """Get MD5 hash"""
    return hashlib.md5(content.encode()).hexdigest()


async def obfuscate_lua(lua_content: str, filename: str) -> tuple:
    """
    Obfuscate Lua content using Ironbrew 2
    
    IMPORTANT: Ironbrew 2 outputs to 'out.lua' file, NOT stdout!
    
    Returns:
        tuple: (result_io, success, error_message)
    """
    
    unique_id = str(uuid.uuid4())[:8]
    work_dir = os.path.join(TEMP_DIR, unique_id)
    
    input_hash = get_hash(lua_content)
    input_size = len(lua_content)
    
    try:
        # Create work directory
        os.makedirs(work_dir, exist_ok=True)
        
        # Create input file
        input_filename = "input.lua"
        input_path = os.path.join(work_dir, input_filename)
        
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(lua_content)
        
        print(f"[Obfuscator] Work dir: {work_dir}")
        print(f"[Obfuscator] Input: {input_path}")
        print(f"[Obfuscator] Input size: {input_size} bytes")
        
        # ================================================
        # Run Ironbrew 2 CLI
        # Must run from IRONBREW_PATH for relative paths
        # (../Lua/Minifier/luasrcdiet.lua)
        # ================================================
        
        # Copy input to ironbrew directory (because it uses relative paths)
        ib_input_path = os.path.join(IRONBREW_PATH, 'publish', f'{unique_id}_input.lua')
        shutil.copy(input_path, ib_input_path)
        
        cmd = f'dotnet "{IRONBREW_CLI_DLL}" "{ib_input_path}"'
        print(f"[Obfuscator] Command: {cmd}")
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.join(IRONBREW_PATH, 'publish')  # Run from publish dir
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=300.0  # 5 minutes for complex scripts
            )
        except asyncio.TimeoutError:
            process.kill()
            return (None, False, "⏱️ Timeout: Process took too long (>5 minutes)")
        
        stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
        stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
        
        print(f"[Obfuscator] Exit code: {process.returncode}")
        print(f"[Obfuscator] STDOUT: {stdout_text[:500]}")
        print(f"[Obfuscator] STDERR: {stderr_text[:500]}")
        
        # ================================================
        # Find output file - Ironbrew writes to out.lua
        # ================================================
        result_content = None
        
        # Check possible output locations
        possible_outputs = [
            os.path.join(IRONBREW_PATH, 'publish', 'out.lua'),  # Primary output
            os.path.join(IRONBREW_PATH, 'out.lua'),
            os.path.join(work_dir, 'out.lua'),
            ib_input_path.replace('.lua', '_out.lua'),
        ]
        
        # Also check for any .lua files created in publish dir
        publish_dir = os.path.join(IRONBREW_PATH, 'publish')
        
        print(f"[Obfuscator] Files in publish dir:")
        for f in os.listdir(publish_dir):
            if f.endswith('.lua'):
                print(f"  - {f}")
        
        # Check each possible output
        for output_path in possible_outputs:
            if os.path.exists(output_path):
                print(f"[Obfuscator] Found: {output_path}")
                
                with open(output_path, 'r', encoding='latin-1', errors='ignore') as f:
                    content = f.read()
                
                # Check if it's different from input
                if len(content) > 100 and get_hash(content) != input_hash:
                    result_content = content
                    print(f"[Obfuscator] ✅ Output size: {len(content)} bytes")
                    
                    # Clean up output file
                    try:
                        os.remove(output_path)
                    except:
                        pass
                    break
        
        # Also look for out.lua anywhere in IRONBREW_PATH
        if not result_content:
            import glob
            for lua_file in glob.glob(os.path.join(IRONBREW_PATH, '**', 'out.lua'), recursive=True):
                print(f"[Obfuscator] Found via glob: {lua_file}")
                with open(lua_file, 'r', encoding='latin-1', errors='ignore') as f:
                    content = f.read()
                if len(content) > 100:
                    result_content = content
                    try:
                        os.remove(lua_file)
                    except:
                        pass
                    break
        
        # Cleanup input file from ironbrew dir
        try:
            os.remove(ib_input_path)
        except:
            pass
        
        # Also cleanup temp files ironbrew creates
        for temp_file in ['t0.lua', 't1.lua', 't2.lua', 't3.lua', 'luac.out']:
            try:
                os.remove(os.path.join(IRONBREW_PATH, 'publish', temp_file))
            except:
                pass
        
        # ================================================
        # Validate and return result
        # ================================================
        if result_content:
            result_size = len(result_content)
            
            # Ironbrew output should be MUCH larger (VM code)
            print(f"[Obfuscator] Size: {input_size} → {result_size} bytes")
            print(f"[Obfuscator] Ratio: {result_size/input_size:.2f}x")
            
            # Check for watermark (confirms it's Ironbrew output)
            if "IronBrew" in result_content:
                print(f"[Obfuscator] ✅ IronBrew watermark found!")
            
            result_io = io.BytesIO(result_content.encode('latin-1'))
            return (result_io, True, None)
        
        # ================================================
        # Failed - build error message
        # ================================================
        error_parts = []
        
        if process.returncode != 0:
            error_parts.append(f"Exit code: {process.returncode}")
        
        if stderr_text:
            error_parts.append(f"Error: {stderr_text[:500]}")
        
        if stdout_text:
            # Check for common errors
            if "not found" in stdout_text.lower():
                error_parts.append("Missing dependency (luac/luajit)")
            elif "Invalid" in stdout_text:
                error_parts.append("Invalid Lua syntax")
            else:
                error_parts.append(f"Output: {stdout_text[:300]}")
        
        if not error_parts:
            error_parts.append("No output file generated. Check Lua syntax.")
        
        return (None, False, "\n".join(error_parts))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (None, False, f"Exception: {str(e)}")
        
    finally:
        # Cleanup work directory
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except:
            pass
