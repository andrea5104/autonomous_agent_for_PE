import re

class LseParser:
    def __init__(self):
        self.ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

    def parse_file(self, filepath):
        extracted_chunks = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            current_section = "GENERAL"
            current_chunk = []
            in_chunk = False

            for line in lines:
                clean_line = self.ansi_escape.sub('', line).strip()
                clean_line = clean_line.replace("setuid", "SUID").replace("setgid", "SGID")
                if not clean_line:
                    continue

                section_match = re.search(r'^---*\[\s*(.+?)\s*\]---*', clean_line)
                if section_match:
                    current_section = section_match.group(1).upper()
                    if current_chunk:
                        extracted_chunks.append({"text": "\n".join(current_chunk)})
                        current_chunk = []
                    in_chunk = False
                    continue

                if clean_line.startswith('[!]') or clean_line.startswith('[*]'):
                    if current_chunk:
                        extracted_chunks.append({"text": "\n".join(current_chunk)})
                    
                    current_chunk = [f"Target Section: [{current_section}]", clean_line]
                    in_chunk = True
                
                elif in_chunk:
                    if not clean_line.startswith('===') and clean_line != '---':
                        
                        if "SUID" in current_chunk[1] and clean_line.startswith('/'):
                            current_chunk.append(f"SUID: {clean_line}")
                        else:
                            current_chunk.append(clean_line)
            if current_chunk:
                extracted_chunks.append({"text": "\n".join(current_chunk)})

            return extracted_chunks

        except FileNotFoundError:
            print(f"[!] Errore: File {filepath} non trovato.")
            return []