import re

class LinEnumParser:
    def __init__(self):
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self.max_lines_per_chunk = 15 
        
        self.keywords_of_interest = [
            "PRIVILEGED", "INTERESTING", "CRON", "JOBS", 
            "FILES", "SERVICES", "SOFTWARE", "VERSION", "SUID", "SUDO", "USER"
        ]

    def parse_file(self, log_path):
        vulnerabilities = []
        current_chunk = []
        current_header = ""
        capture = False 
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for raw_line in f:
                    clean_line = self.ansi_escape.sub('', raw_line).strip()
                    
                    if not clean_line:
                        continue
                        
                    if clean_line.startswith("###"):
                        section_name = clean_line.replace("#", "").strip().upper()
                        
                        if any(keyword in section_name for keyword in self.keywords_of_interest):
                            if current_chunk:
                                vulnerabilities.append({"text": "\n".join(current_chunk)})
                            current_header = clean_line
                            current_chunk = [clean_line]
                            capture = True
                        else:
                            capture = False
                            
                    elif capture:
                        if clean_line.startswith("[-]"):
                            if current_chunk:
                                vulnerabilities.append({"text": "\n".join(current_chunk)})
                            current_header = clean_line
                            current_chunk = [clean_line]
                        else:
                            current_chunk.append(clean_line)
                            
                            if len(current_chunk) >= self.max_lines_per_chunk:
                                vulnerabilities.append({"text": "\n".join(current_chunk)})
                                current_chunk = [f"{current_header} (Continua...)"]
                                
                if current_chunk and len(current_chunk) > 1:
                    vulnerabilities.append({"text": "\n".join(current_chunk)})
                    
            return vulnerabilities

        except FileNotFoundError:
            print(f"[-] Errore logico: Il file '{log_path}' non è stato trovato.")
            return []