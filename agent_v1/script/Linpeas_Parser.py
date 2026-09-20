import re

class LinpeasParser:
    def __init__(self):
        self.alert_colors = ['\x1b[1;31;103m','\x1b[1;31m']

        self.critical_keywords = [
            'NOPASSWD:', 'SUID', '-rws', 'Capabilities', 'root_squash', 
            'CVE-', 'Vulnerable', 'cron', 'passw', 'systemctl'
        ]
        
        self.ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

    def parse_file(self, filepath):
        extracted_chunks = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                is_alert = any(color in line for color in self.alert_colors)
                is_keyword = any(kw in line for kw in self.critical_keywords)
                
                if not (is_alert or is_keyword):
                    continue
                    
                start_idx = max(0, i - 2)
                end_idx = min(len(lines), i + 8)
                chunk_lines = lines[start_idx:end_idx]
                
                clean_chunk = [self.ansi_escape.sub('', cl).strip() for cl in chunk_lines]
                clean_chunk = [cl for cl in clean_chunk if cl]
                clean_text = "\n".join(clean_chunk)
                
                if "Legend:" in clean_text or "RED/YELLOW means" in clean_text:
                    continue
                if len(clean_text) < 15: 
                    continue
                    
                if not any(d['text'] == clean_text for d in extracted_chunks):
                    extracted_chunks.append({"text": clean_text})

            return extracted_chunks

        except FileNotFoundError:
            print(f"[!] Errore: File {filepath} non trovato.")
            return []