"""
Ironbrew 2 Obfuscator - FIXED VERSION
"""

import asyncio
import os
import uuid
import io
import shutil

IRONBREW_PATH = os.getenv('IRONBREW_PATH', '/opt/ironbrew-2')
IRONBREW_PUBLISH = os.path.join(IRONBREW_PATH, 'publish')
IRONBREW_CLI_DLL = os.path.join(IRONBREW_PUBLISH, 'IronBrew2 CLI.dll')
TEMP_DIR = '/app/temp'

print(f"[Obfuscator] IRONBREW_PATH: {IRONBREW_PATH}")
print(f"[Obfuscator] CLI DLL exists: {os.path.exists(IRONBREW_CLI_DLL)}")


def check_deps():
    import subprocess
    deps = {}
    for cmd in ['luac', 'luajit', 'lua']:
        try:
            result = subprocess.run([cmd, '-v'], capture_output=True)
            deps[cmd] = 'OK' if result.returncode == 0 else 'FAIL'
        except:
            deps[cmd] = 'MISSING'
    
    minifier = os.path.join(IRONBREW_PATH, 'Lua', 'Minifier')
    for f in ['luasrcdiet.lua', 'llex.lua', 'lparser.lua', 'optlex.lua', 'optparser.lua']:
        deps[f] = 'OK' if os.path.exists(os.path.join(minifier, f)) else 'MISSING'
    
    print(f"[Obfuscator] Dependencies: {deps}")
    return deps

check_deps()


async def obfuscate_lua(lua_content: str, filename: str) -> tuple:
    """
    Obfuscate Lua using Ironbrew 2
    Output: out.lua in publish directory
    """
    
    unique_id = str(uuid.uuid4())[:8]
    input_size = len(lua_content)
    
    try:
        # Create input file
        input_filename = f"{unique_id}_input.lua"
        input_path = os.path.join(IRONBREW_PUBLISH, input_filename)
        
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(lua_content)
        
        print(f"[Obfuscator] Input: {input_path} ({input_size} bytes)")
        
        # Run Ironbrew 2
        cmd = f'dotnet "{IRONBREW_CLI_DLL}" "{input_path}"'
        print(f"[Obfuscator] Running: {cmd}")
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=IRONBREW_PUBLISH
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=300.0
            )
        except asyncio.TimeoutError:
            process.kill()
            cleanup(unique_id)
            return (None, False, "Timeout: >5 minutes")
        
        stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
        stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
        
        print(f"[Obfuscator] Exit: {process.returncode}")
        print(f"[Obfuscator] STDOUT: {stdout_text[:800]}")
        if stderr_text:
            print(f"[Obfuscator] STDERR: {stderr_text[:400]}")
        
        # Find output (out.lua)
        result_content = None
        output_path = os.path.join(IRONBREW_PUBLISH, 'out.lua')
        
        # List files
        print(f"[Obfuscator] Files in publish:")
        for f in os.listdir(IRONBREW_PUBLISH):
            if f.endswith('.lua'):
                fsize = os.path.getsize(os.path.join(IRONBREW_PUBLISH, f))
                print(f"  - {f} ({fsize} bytes)")
        
        # Check out.lua
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
            
            if content and len(content) > 100 and content != lua_content:
                result_content = content
                print(f"[Obfuscator] Found out.lua ({len(content)} bytes)")
        
        # Cleanup
        cleanup(unique_id)
        
        # Return result
        if result_content:
            print(f"[Obfuscator] Success: {input_size} -> {len(result_content)} bytes")
            result_io = io.BytesIO(result_content.encode('latin-1'))
            return (result_io, True, None)
        
        # Error
        error = stderr_text if stderr_text else stdout_text[:500] if stdout_text else "No output"
        return (None, False, error)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        cleanup(unique_id)
        return (None, False, str(e))


def cleanup(unique_id: str):
    """Cleanup temp files"""
    files = [
        f'{unique_id}_input.lua',
        't0.lua', 't1.lua', 't2.lua', 't3.lua',
        'luac.out', 'out.lua'
    ]
    for f in files:
        try:
            path = os.path.join(IRONBREW_PUBLISH, f)
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
