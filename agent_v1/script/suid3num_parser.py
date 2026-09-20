import re

class Suid3numParser:
    def __init__(self):
        self.ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        self.header_pattern = re.compile(r'^\[.*?\]')
        self.separator_pattern = re.compile(r'^[-_]{3,}$')

    def parse_file(self, filepath):
        extracted_chunks = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            current_chunk = []
            parsing_started = False

            for line in lines:
                clean_line = self.ansi_escape.sub('', line).strip()
                
                if not clean_line or self.separator_pattern.match(clean_line):
                    continue

                if self.header_pattern.match(clean_line):
                    parsing_started = True
                    
                    if current_chunk and len(current_chunk) > 1:
                        extracted_chunks.append({"text": "\n".join(current_chunk)})
                    
                    current_chunk = [clean_line]
                    continue

                if parsing_started and current_chunk:
                    current_chunk.append(clean_line)

            if current_chunk and len(current_chunk) > 1:
                extracted_chunks.append({"text": "\n".join(current_chunk)})

            final_chunks = []
            for chunk in extracted_chunks:
                text_lower = chunk["text"].lower()
                
                if "custom suid binaries" in text_lower:
                    lines = chunk["text"].split('\n')
                    adapted_text = "Target Section: [CUSTOM SUID BINARIES]\n"
                    for line in lines[1:]:
                        if line.strip():
                            adapted_text += f"SUID: {line.strip()}\n"
                    
                    final_chunks.append({"text": adapted_text})
                else:
                    final_chunks.append(chunk)

            return final_chunks

        except FileNotFoundError:
            print(f"[!] Errore: File {filepath} non trovato.")
            return []