import re

class LinpeasParser:
    def __init__(self):
        self.alert_colors = ['\x1b[1;31;103m', '\x1b[1;31m']
        
        self.ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

    def parse_file(self, filepath):
        extracted_chunks = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            triggered_indices = []
            
            for i, line in enumerate(lines):
                if any(color in line for color in self.alert_colors):
                    triggered_indices.append(i)
            
            if not triggered_indices:
                return []

            merged_intervals = []
            
            start = max(0, triggered_indices[0] - 2) 
            end = min(len(lines), triggered_indices[0] + 8)
            
            for idx in triggered_indices[1:]:
                if idx - 2 <= end:
                    end = min(len(lines), idx + 8)
                else:
                    merged_intervals.append((start, end))
                    start = max(0, idx - 2)
                    end = min(len(lines), idx + 8)
                    
            merged_intervals.append((start, end))

            for start_idx, end_idx in merged_intervals:
                chunk_lines = lines[start_idx:end_idx]
                
                clean_chunk = [self.ansi_escape.sub('', cl).strip() for cl in chunk_lines]
                clean_chunk = [cl for cl in clean_chunk if cl] 
                
                clean_text = "\n".join(clean_chunk)
                
                if len(clean_text) < 20:
                    continue
                    
                if not any(d['text'] == clean_text for d in extracted_chunks):
                    extracted_chunks.append({"text": clean_text})

            return extracted_chunks

        except FileNotFoundError:
            print(f"[!] Errore: File {filepath} non trovato.")
            return []