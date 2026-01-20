import asyncio
import os
import uuid
import io
import glob

# Auto-detect DLL path
def find_ironbrew_dll():
    """Find Ironbrew DLL automatically"""
    possible_paths = [
        '/opt/ironbrew-2/publish/IronBrew2.CLI.dll',
        '/opt/ironbrew-2/publish/IronBrew2 CLI.dll',
        '/opt/ironbrew-2/publish/IronBrew2.dll',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Search for any DLL
    dlls = glob.glob('/opt/ironbrew-2/publish/*.dll')
    cli_dlls = [d for d in dlls if 'cli' in d.lower() or 'ironbrew' in d.lower()]
    
    if cli_dlls:
        return cli_dlls[0]
    
    return os.getenv('IRONBREW_DLL', '/opt/ironbrew-2/publish/IronBrew2.CLI.dll')

IRONBREW_DLL = find_ironbrew_dll()
TEMP_DIR = '/app/temp'

print(f"Using Ironbrew DLL: {IRONBREW_DLL}")

async def obfuscate_lua(lua_content: str, filename: str) -> tuple:
    """
    Obfuscate Lua content menggunakan Ironbrew 2
    
    Returns:
        tuple: (result_io, success, error_message)
    """
    
    unique_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(TEMP_DIR, f"{unique_id}_{filename}")
    
    try:
        # Ensure temp directory exists
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # Write input file
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(lua_content)
        
        # Run Ironbrew 2
        process = await asyncio.create_subprocess_exec(
            'dotnet', IRONBREW_DLL, input_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(input_path)
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=120.0  # 2 minute timeout
        )
        
        stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
        stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
        
        print(f"STDOUT: {stdout_text[:500]}")
        print(f"STDERR: {stderr_text[:500]}")
        
        # Check for output files
        possible_outputs = [
            input_path.replace('.lua', '.obfuscated.lua'),
            input_path.replace('.lua', '_obfuscated.lua'),
            os.path.join(os.path.dirname(input_path), 'output.lua'),
            os.path.join(os.path.dirname(input_path), 'Obfuscated.lua'),
        ]
        
        # Also check if original file was modified
        result_content = None
        
        # Check each possible output
        for out_path in possible_outputs:
            if os.path.exists(out_path):
                with open(out_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if content and len(content) > 10:
                        result_content = content
                        # Cleanup output file
                        try:
                            os.remove(out_path)
                        except:
                            pass
                        break
        
        # Check if stdout contains obfuscated code
        if not result_content and stdout_text:
            # Ironbrew mungkin output ke stdout
            if 'local' in stdout_text or 'function' in stdout_text or 'return' in stdout_text:
                result_content = stdout_text
        
        # Check if input file was modified (some obfuscators do this)
        if not result_content and os.path.exists(input_path):
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                new_content = f.read()
                if new_content != lua_content and len(new_content) > len(lua_content) * 0.5:
                    result_content = new_content
        
        if result_content:
            result_io = io.BytesIO(result_content.encode('utf-8'))
            return (result_io, True, None)
        else:
            error_msg = stderr_text if stderr_text else "No output generated"
            return (None, False, error_msg)
            
    except asyncio.TimeoutError:
        return (None, False, "Timeout: Process took too long (>120 seconds)")
    except Exception as e:
        return (None, False, str(e))
    finally:
        # Cleanup
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except:
            pass
