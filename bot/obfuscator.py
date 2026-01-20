"""
Ironbrew 2 Obfuscator Module
Handles Lua file obfuscation using Ironbrew 2 CLI
"""

import asyncio
import os
import uuid
import io
import shutil
import glob

# Path ke Ironbrew 2 CLI DLL
IRONBREW_CLI_DLL = os.getenv('IRONBREW_CLI_DLL', '/opt/ironbrew-2/publish/IronBrew2 CLI.dll')
TEMP_DIR = '/app/temp'

# Startup check
print(f"[Obfuscator] DLL Path: {IRONBREW_CLI_DLL}")
print(f"[Obfuscator] DLL Exists: {os.path.exists(IRONBREW_CLI_DLL)}")

# List semua file di publish folder
if os.path.exists('/opt/ironbrew-2/publish'):
    print(f"[Obfuscator] Available files: {os.listdir('/opt/ironbrew-2/publish')}")


async def obfuscate_lua(lua_content: str, filename: str) -> tuple:
    """
    Obfuscate Lua content menggunakan Ironbrew 2
    
    Args:
        lua_content: Isi file Lua
        filename: Nama file asli
        
    Returns:
        tuple: (result_io, success, error_message)
    """
    
    unique_id = str(uuid.uuid4())[:8]
    work_dir = os.path.join(TEMP_DIR, unique_id)
    
    try:
        # Buat direktori kerja
        os.makedirs(work_dir, exist_ok=True)
        
        # Simpan file input
        input_filename = filename.replace(' ', '_')  # Hindari spasi di nama file
        input_path = os.path.join(work_dir, input_filename)
        
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(lua_content)
        
        print(f"[Obfuscator] Input file: {input_path}")
        print(f"[Obfuscator] Content length: {len(lua_content)} chars")
        
        # Jalankan Ironbrew 2 CLI
        cmd = f'dotnet "{IRONBREW_CLI_DLL}" "{input_path}"'
        print(f"[Obfuscator] Running: {cmd}")
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=120.0
            )
        except asyncio.TimeoutError:
            process.kill()
            return (None, False, "⏱️ Timeout: Process took too long (>120 seconds)")
        
        stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
        stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
        
        print(f"[Obfuscator] Return code: {process.returncode}")
        print(f"[Obfuscator] STDOUT length: {len(stdout_text)}")
        print(f"[Obfuscator] STDERR: {stderr_text[:500] if stderr_text else 'None'}")
        
        # Cari hasil obfuscation
        result_content = None
        
        # List semua file di work_dir
        all_files = os.listdir(work_dir)
        lua_files = [f for f in all_files if f.endswith('.lua')]
        print(f"[Obfuscator] Files in work_dir: {all_files}")
        
        # Cek file-file yang mungkin jadi output
        for lua_file in lua_files:
            file_path = os.path.join(work_dir, lua_file)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Jika bukan file input, atau kontennya berbeda = hasil obfuscation
            if lua_file != input_filename or content != lua_content:
                if len(content) > 50:  # Pastikan tidak kosong
                    result_content = content
                    print(f"[Obfuscator] Found result in: {lua_file}")
                    break
        
        # Jika tidak ada file output, cek stdout
        if not result_content and stdout_text:
            # Cek apakah stdout berisi Lua code
            lua_keywords = ['local', 'function', 'return', 'end', 'if', 'then', 'for', 'while']
            if any(kw in stdout_text for kw in lua_keywords):
                result_content = stdout_text
                print("[Obfuscator] Using stdout as result")
        
        # Jika masih tidak ada, cek apakah file input berubah
        if not result_content:
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                current_content = f.read()
            
            if current_content != lua_content and len(current_content) > 50:
                result_content = current_content
                print("[Obfuscator] Input file was modified")
        
        # Return hasil
        if result_content:
            result_io = io.BytesIO(result_content.encode('utf-8'))
            return (result_io, True, None)
        else:
            error_msg = stderr_text if stderr_text else f"No output generated (exit code: {process.returncode})"
            return (None, False, error_msg)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (None, False, f"Error: {str(e)}")
        
    finally:
        # Cleanup
        try:
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir, ignore_errors=True)
        except:
            pass


async def test_obfuscator():
    """Test function untuk verify obfuscator berjalan"""
    test_lua = """
local function hello()
    print("Hello World!")
end
hello()
"""
    result, success, error = await obfuscate_lua(test_lua, "test.lua")
    
    if success:
        content = result.read().decode('utf-8')
        print(f"[Test] Success! Output length: {len(content)}")
        return True
    else:
        print(f"[Test] Failed: {error}")
        return False        except:
            pass
