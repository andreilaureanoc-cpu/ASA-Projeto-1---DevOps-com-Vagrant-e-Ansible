# Projeto 01 - DevOps com Vagrant e Ansible

## Identificação

| | |
|---|---|
| **Instituição** | IFPB |
| **Curso** | Tecnologia em Redes de Computadores |
| **Disciplina** | Administração de Sistemas Abertos |
| **Professor** | Leonidas Lima |
| **Período** | 2026.2 |

**Integrantes da equipe**

| Integrante | Nome completo | Matrícula |
|---|---|---|
| 1 | Andrei Laureano Cordeiro | 20251380031 |
| 2 | Gabriel Farias Palmeira | 20251380016 |

---

## 1. O que é este projeto?

O projeto cria, **de forma totalmente automática**, uma pequena rede de quatro servidores virtuais e configura todos os serviços de que ela precisa. Nada é instalado ou ajustado "na mão" dentro das máquinas: tudo é descrito em arquivos de texto (conceito de **Infraestrutura como Código**).

Duas ferramentas dividem o trabalho:

| Ferramenta | Para que serve | Onde está |
|---|---|---|
| **Vagrant** | **Cria** as máquinas virtuais no VirtualBox (memória, discos, rede, nome). | `Vagrantfile` |
| **Ansible** | **Configura** o que roda dentro das máquinas (usuários, SSH, DHCP, DNS, NFS...). | `playbooks/` |

Em resumo: o Vagrant constrói os "computadores" e o Ansible os transforma em servidores prontos para uso.

---

## 2. Visão geral da rede

Rede privada usada por todas as máquinas: **192.168.56.0/24**. Domínio da equipe: **`andrei.gabriel.devops`**.

```
                  Máquina real (hospedeiro)
                 VirtualBox + Vagrant + Ansible
                            |
        ---------------------------------------------  rede 192.168.56.0/24
          |               |               |               |
   +------------+  +------------+  +------------+  +------------+
   |    arq     |  |     db     |  |    app     |  |    cli     |
   | .131 (fixo)|  | .116 (DHCP)|  | .161 (DHCP)|  | .50-.100   |
   | DHCP + DNS |  |  MariaDB   |  |  Apache    |  | Firefox    |
   | LVM + NFS  |  |  autofs    |  |  autofs    |  | autofs     |
   +------------+  +------------+  +------------+  +------------+
```

| VM | Nome completo | Endereço IP | Função | RAM |
|---|---|---|---|---|
| `arq` | `arq.andrei.gabriel.devops` | `192.168.56.131` (fixo) | Servidor de arquivos: **DHCP, DNS, LVM e NFS** | 512 MB |
| `db` | `db.andrei.gabriel.devops` | `192.168.56.116` (DHCP, por MAC) | Servidor de **banco de dados** (MariaDB) | 512 MB |
| `app` | `app.andrei.gabriel.devops` | `192.168.56.161` (DHCP, por MAC) | Servidor de **aplicação** web (Apache) | 512 MB |
| `cli` | `cli.andrei.gabriel.devops` | DHCP (faixa 50 a 100) | **Cliente** com navegador (Firefox via X11) | 1024 MB |

> **Como db e app recebem sempre o mesmo IP?** Cada uma tem um endereço MAC fixo definido no `Vagrantfile` (`08:00:27:3a:00:01` e `08:00:27:3a:00:02`). O servidor DHCP do `arq` tem uma "reserva" ligando cada MAC a um IP. Assim o IP vem por DHCP, mas é sempre o mesmo.

---

## 3. O que cada serviço faz

- **DHCP (arq):** entrega IP automaticamente às máquinas. Distribui endereços de `.50` a `.100`, com *lease* de 180 s (máximo 3600 s), gateway `192.168.56.1`, domínio `andrei.gabriel.devops` e DNS apontando para o `arq`.
- **DNS (arq):** traduz nomes em IPs (`db.andrei.gabriel.devops` → `192.168.56.116`) e o inverso. Atende apenas a rede `192.168.56.0/24` e encaminha consultas externas para `1.1.1.1` e `8.8.8.8`.
- **LVM (arq):** junta os 3 discos extras de 10 GB em um grupo de volumes `dados`, cria o volume `ifpb` de 15 GB (ext4) e o monta automaticamente em `/dados`.
- **NFS (arq):** compartilha a pasta `/dados/nfs` com toda a rede. Qualquer usuário remoto é convertido no usuário `nfs-ifpb` (sem shell), o único que escreve na pasta, e as gravações vão direto ao disco.
- **autofs (db, app, cli):** monta o compartilhamento do `arq` em `/var/nfs` **sozinho**, na primeira vez que alguém acessa a pasta.
- **SSH (todas):** só aceita login por **chave pública**, bloqueia o `root`, libera apenas os grupos `vagrant` e `ifpb` e mostra um aviso de acesso restrito.
- **Chrony / fuso (todas):** horário sincronizado com `pool.ntp.br`, fuso `America/Recife`.
- **MariaDB (db), Apache (app):** servidor de banco de dados e servidor web com uma página `index.html` própria, contendo a descrição do projeto e os integrantes.
- **Firefox + X11 (cli):** permite abrir o Firefox do `cli` na tela da máquina real via `ssh -X`.

---

## 4. Estrutura do repositório

```
.
├── Vagrantfile                 # Cria as 4 VMs (rede, discos, MACs, gatilho do DHCP)
├── ansible.cfg                 # Configuração do Ansible (aponta para o inventário)
├── hosts.ini                   # Inventário: lista de máquinas e como acessá-las
├── README.md                   # Esta documentação
└── playbooks/
    ├── site.yml                # Executa todos os playbooks, na ordem certa
    ├── group_vars/all.yml      # Variáveis do projeto (nomes, IPs, MACs, domínio)
    ├── conf-comum.yml          # Todas: atualização, chrony, fuso, grupo, usuários, sudo
    ├── conf-ssh.yml            # Todas: endurecimento do SSH, chaves e banner
    ├── conf-dhcp.yml           # arq: servidor DHCP        (+ dhcpd.conf.j2)
    ├── conf-dns.yml            # arq: servidor DNS         (+ named.conf.*.j2, zona-*.j2)
    ├── conf-lvm.yml            # arq: volumes LVM e montagem em /dados
    ├── conf-nfs.yml            # arq: servidor NFS         (+ exports.j2)
    ├── conf-autofs.yml         # db, app, cli: montagem automática do NFS
    ├── conf-db.yml             # db: MariaDB
    ├── conf-app.yml            # app: Apache               (+ index.html.j2)
    ├── conf-cli.yml            # cli: Firefox, xauth e X11 no SSH
    ├── banner.txt              # Mensagem exibida no acesso SSH
    └── keys/                   # Chaves PÚBLICAS dos usuários (andrei.pub, gabriel.pub)
```

Arquivos terminados em `.j2` são **modelos**: o Ansible troca as variáveis (por exemplo `{{ ip_arq }}`) pelos valores de `group_vars/all.yml` antes de copiá-los para a máquina.

---
