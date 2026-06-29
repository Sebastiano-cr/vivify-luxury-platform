"""Script de pareamento wacli — gera QR code para vincular WhatsApp."""
import asyncio
import json
import os
import shutil
import subprocess
import sys

def _find_wacli() -> str:
    w = shutil.which("wacli")
    if w:
        return w
    candidates = [
        os.path.expanduser("~/go/bin/wacli"),
        "/usr/local/bin/wacli",
        "/usr/bin/wacli",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "wacli"

WACLI = _find_wacli()

def doctor() -> dict:
    try:
        r = subprocess.run([WACLI, "--json", "doctor"], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return {"ok": False, "error": r.stderr.strip()}
        return {"ok": True, "data": json.loads(r.stdout)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def pair():
    """Pareia o dispositivo via QR code."""
    print(f"wacli: {WACLI}")
    status = doctor()
    if status.get("ok"):
        inner = status["data"].get("data", status["data"])
        if isinstance(inner, dict) and inner.get("authenticated"):
            print("Já autenticado! Nenhum pareamento necessário.")
            return
    print("Iniciando pareamento — escaneie o QR code abaixo com o WhatsApp do seu celular:")
    print("(WA_CURSO=web força o código QR em vez de OTP)\n")
    env = os.environ.copy()
    env["WA_CURSO"] = "web"
    proc = await asyncio.create_subprocess_exec(
        WACLI, "auth", "qr",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        print(stdout.decode(errors="replace"))
    except asyncio.TimeoutError:
        proc.kill()
        print("\nTempo limite excedido (60s). O QR code expirou — execute novamente para gerar um novo.")

if __name__ == "__main__":
    asyncio.run(pair())
