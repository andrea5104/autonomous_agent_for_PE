# Autonomous agent for privilege escalation
### Automated Privilege Escalation via LLM

---

## Disclaimer

This tool was developed for academic research purposes and is intended for use only in authorized laboratory environments. The tests were conducted on the [TryHackMe](https://tryhackme.com) platform. Do not use this tool on systems you do not own or for which you do not have explicit written authorization. The authors decline any responsibility for improper, illegal, or unethical use of this software.

---

## Overview

 This is an autonomous agent that uses Large Language Models to automate the Privilege Escalation phase of a penetration test on Linux systems. The agent receives as input the output log of a local enumeration tool, analyzes it through an LLM, generates an exploit, and autonomously delivers and executes it on the target machine. The project has two versions, each contained in its own folder.
**Note:** Initial access to the target machine must be obtained before running the agent.

---

## Repository Structure

```
pe-llm-agent/
├── README.md
├── LICENSE
├── .gitignore
├── setup.sh                     
├── agent_v1/
│   ├── script/
│   │   ├── main.py
│   │   ├── llm_client.py
│   │   ├── Linpeas_Parser.py
│   │   ├── LinEnum_Parser.py
│   │   ├── lse_parser.py
│   │   └── suid3num_parser.py
|
└── agent_v2/
    ├── script/
    │   ├── main.py
    │   ├── llm_client.py
    │   ├── Linpeas_Parser.py
    │   ├── LinEnum_Parser.py
    │   ├── lse_parser.py
    │   └── suid3num_parser.py
```

---

## Requirements & Setup
This agent requires the [Ollama](https://ollama.com) service to run LLM models locally. All dependencies — system packages, Python libraries, and LLM models (default: qwen2.5-coder:32b) — are installed automatically by the provided setup script:

```bash
chmod +x setup.sh
sudo ./setup.sh
```

For a detailed list of dependencies, refer to the comments inside `setup.sh`.---

## Usage

### Prerequisites
Before running the agent, ensure that:
1. Ollama is running (`ollama serve`)
2. You are connected to the TryHackMe VPN
### Running the Agent in the second version
the are 3 way for execute the program, every possibility depend on the initial access on the target machine.

**SSH mode** (credentials available):
```bash
python3 main.py <log_file> \
    --tool linpeas \
    --mode ssh \
    --ip <TARGET_IP> \
    --user <USERNAME> \
    --password <PASSWORD> \
    --model <model name>
```

**SSH mode** (Key available):
```bash
python3 main.py <log_file> \
    --tool linpeas \
    --mode ssh \
    --ip <TARGET_IP> \
    --user <USERNAME> \
    --key <Key> \
    --model <model name>
```

**Reverse shell mode** (inbound connection from target):
```bash
python3 main.py <log_file> \
    --tool linpeas \
    --mode revshell \
    --lport 4445 \
    --model <model name>
```

### Running the Agent in the first version
**Note:** This version only supports the `qwen2.5-coder:32b` model. **Important:** This version does not return the root shell in the current session. Before running the agent, open a separate terminal > and start a listener:
```bash
nc -lvnp 4444
```

**SSH mode** (credentials available):
```bash
python3 main.py <log_file> \
    --tool linpeas \
    --mode ssh \
    --ip <TARGET_IP> \
    --user <USERNAME> \
    --password <PASSWORD> \
```

**SSH mode** (Key available):
```bash
python3 main.py <log_file> \
    --tool linpeas \
    --mode ssh \
    --ip <TARGET_IP> \
    --user <USERNAME> \
    --key <Key> \
```

**Reverse shell mode** (inbound connection from target):
```bash
python3 main.py <log_file> \
    --tool linpeas \
    --mode revshell \
    --lport 4445 \
```
### Supported Enumeration Tools

| Flag | Tool |
|------|------|
| `linpeas` | [LinPEAS](https://github.com/carlospolop/PEASS-ng) |
| `linenum` | [LinEnum](https://github.com/rebootuser/LinEnum) |
| `lse` | [LSE](https://github.com/diego-treitos/linux-smart-enumeration) |
| `suid3num` | [Suid3num](https://github.com/Anon-Exploiter/SUID3NUM) |

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
