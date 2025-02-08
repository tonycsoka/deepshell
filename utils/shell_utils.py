import asyncio

async def execute_shell_command(args):                                                                                    
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,                                                                                         )                                                                                        
                                                                                                                           
    stdout, stderr = await proc.communicate()
    stdout_str = stdout.decode('utf-8', errors='ignore')
    stderr_str = stderr.decode('utf-8', errors='ignore')                                                                                                                       
    return stdout_str, proc.returncode, stderr_str

