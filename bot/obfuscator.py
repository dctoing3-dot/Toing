import asyncio
import os
import uuid
import io
from pathlib import Path

IRONBREW_DLL = os.getenv('IRONBREW_DLL', '/opt/ironbrew-2/publish/IronBrew2.dll')
TEMP_DIR = '/app/temp'

async def obfuscate_lua(lua_content: str, filename: str) -> tuple:
    """
    Obfuscate Lua content menggunakan Ironbrew 2
    
    Returns:
        tuple: (result_io, success, error_message)
    """
    
    # Generate unique ID
    unique_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(TEMP_DIR, f"{unique_id}_{filename}")
    output_path = input_path.replace('.lua', '_obfuscated.lua')
    
    try:
        # Write input file
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(lua_content)
        
        # Run Ironbrew 2
        process = await asyncio.create_subprocess_exec(
            'dotnet', IRONBREW_DLL, input_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(IRONBREW_DLL)
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=60.0  # 60 second timeout
        )
        
        # Check for output file
        # Ironbrew 2 biasanya output ke file yang sama atau dengan suffix
        possible_outputs = [
            output_path,
            input_path,  # Sometimes overwrites
            input_path.replace('.lua', '.obfuscated.lua'),
            os.path.join(os.path.dirname(IRONBREW_DLL), 'output.lua'),
        ]
        
        result_content = None
        
        # Cek apakah ada output di stdout
        if stdout:
            stdout_text = stdout.decode('utf-8', errors='ignore')
            if 'return' in stdout_text or 'local' in stdout_text:
                result_content = stdout_text
        
        # Cek file output
        if not result_content:
            for out_path in possible_outputs:
                if os.path.exists(out_path):
                    with open(out_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Cek apakah sudah di-obfuscate (biasanya lebih panjang)
                        if len(content) > len(lua_content) * 0.5:
                            result_content = content
                            break
        
        if result_content:
            # Return as BytesIO for Discord
            result_io = io.BytesIO(result_content.encode('utf-8'))
            return (result_io, True, None)
        else:
            error_text = stderr.decode('utf-8', errors='ignore') if stderr else "Unknown error"
            return (None, False, error_text)
            
    except asyncio.TimeoutError:
        return (None, False, "Timeout: Proses terlalu lama (>60 detik)")
    except Exception as e:
        return (None, False, str(e))
    finally:
        # Cleanup temp files
        for f in [input_path, output_path]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass
