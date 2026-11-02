# Projeto 01 - DevOps com Vagrant e Ansible

## Identificação

| | |
|---|---|
| **Instituição** | Instituto Federal da Paraíba (IFPB) - Campus João Pessoa |
| **Departamento** | Departamento de Ensino Superior |
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

## 5. Pré-requisitos

Na máquina real (Linux, testado em Ubuntu):

```bash
sudo apt update
sudo apt -y install virtualbox vagrant ansible git
ansible-galaxy collection install community.general ansible.posix
```

Confira as versões:

```bash
vagrant --version && ansible --version && vboxmanage --version
```

Também é necessário ter **internet** (as VMs baixam pacotes) e o par de chaves SSH dos usuários, descrito na seção 6.

---

## 6. Antes de executar (configuração única)

### 6.1 Variáveis do projeto

Todos os nomes, IPs e MACs estão em **`playbooks/group_vars/all.yml`**. Para outra equipe usar o projeto, basta mudar esse arquivo e as constantes no topo do `Vagrantfile` (`NOME1`, `NOME2` e o IP do `arq`). Os nomes (`nome1`, `nome2`) devem estar em **minúsculas**, pois viram os logins dos usuários.

### 6.2 Chaves SSH dos usuários

O acesso por SSH dos usuários `andrei` e `gabriel` é feito somente por chave. Cada integrante gera o seu par na máquina real:

```bash
mkdir -p playbooks/keys
ssh-keygen -t ed25519 -N "" -C "andrei@devops"  -f playbooks/keys/andrei
ssh-keygen -t ed25519 -N "" -C "gabriel@devops" -f playbooks/keys/gabriel
```

Somente os arquivos `.pub` (chaves públicas) vão para o repositório. **As chaves privadas nunca devem ser enviadas ao GitHub** (o `.gitignore` já as ignora). O Ansible instala as chaves públicas nas VMs.

---

## 7. Como executar

Todos os comandos são executados na máquina real, dentro da pasta do projeto.

### Opção A - Automática (um comando)

```bash
vagrant up
```

O Vagrant cria as VMs **na ordem arq → db → app → cli** e, ao subir cada uma, executa o `playbooks/site.yml` apenas naquela máquina. A ordem importa: o `arq` precisa estar pronto antes, pois fornece o DHCP e o DNS dos demais.

### Opção B - Passo a passo (recomendada para testar e depurar)

**1. Criar apenas o servidor `arq`** (sem configurá-lo ainda):

```bash
vagrant up arq --no-provision
ansible arq -m ping
```

**2. Configurar o `arq`:**

```bash
ansible-playbook playbooks/conf-comum.yml --limit arq
ansible-playbook playbooks/conf-dhcp.yml
ansible-playbook playbooks/conf-dns.yml
```

**3. Criar as demais VMs e renovar o IP delas:**

```bash
vagrant up db app cli --no-provision
vagrant provision db app cli --provision-with rede
```

O provisionador `rede` renova o IP da interface `eth1` (agora o DHCP do `arq` já responde) e ajusta duas coisas: usar o DNS do `arq` e **não** usar o gateway da `eth1`, para a internet continuar saindo pela interface NAT.

**4. Anotar o IP do `cli`** (varia entre `.50` e `.100`) e colocá-lo no grupo `[cli]` do `hosts.ini`:

```bash
vagrant ssh cli -c "ip -4 addr show eth1"
```

**5. Executar toda a configuração restante:**

```bash
ansible-playbook playbooks/site.yml
```

> O `site.yml` é **idempotente**: pode ser executado várias vezes. Na segunda execução, quase tudo aparece como `ok` e `changed=0`, o que indica que nada precisou mudar.

### Resolução de nomes pela máquina real

Para a máquina real também resolver `db.andrei.gabriel.devops` e os demais, use o DNS do `arq` apenas para o domínio da equipe:

```bash
sudo resolvectl dns vboxnet0 192.168.56.131
sudo resolvectl domain vboxnet0 "~andrei.gabriel.devops"
ping -c1 db.andrei.gabriel.devops
```

Alternativa (sem `systemd-resolved`): acrescentar em `/etc/hosts`:

```
192.168.56.131  arq.andrei.gabriel.devops
192.168.56.116  db.andrei.gabriel.devops
192.168.56.161  app.andrei.gabriel.devops
```

---

## 8. Como verificar se funcionou

| O que verificar | Comando | Resultado esperado |
|---|---|---|
| 4 VMs ligadas | `vagrant status` | arq, db, app e cli em `running` |
| Nomes das máquinas | `ansible servidores -m command -a "hostname -f" -f 1` | `arq.andrei.gabriel.devops`, `db...`, `app...`, `cli...` |
| Fuso e horário | `ansible servidores -b -m command -a "timedatectl"` | `America/Recife` |
| Usuários e grupo | `ansible servidores -m command -a "id andrei"` | grupo `ifpb` presente |
| SSH com chave | `ssh -i playbooks/keys/andrei andrei@192.168.56.131` | entra e mostra o aviso de acesso restrito |
| SSH sem chave | `ssh -o PubkeyAuthentication=no andrei@192.168.56.131` | acesso negado |
| SSH como root | `ssh root@192.168.56.131` | acesso negado |
| sudo | `ssh -i playbooks/keys/andrei andrei@192.168.56.131 "sudo whoami"` | `root` |
| DHCP | `vagrant ssh arq -c "sudo cat /var/lib/dhcp/dhcpd.leases"` | leases de db, app e cli |
| IPs por MAC | `vagrant ssh db -c "ip -4 addr show eth1"` | `192.168.56.116` (db) e `192.168.56.161` (app) |
| DNS direto | `dig @192.168.56.131 db.andrei.gabriel.devops +short` | `192.168.56.116` |
| DNS reverso | `dig @192.168.56.131 -x 192.168.56.116 +short` | `db.andrei.gabriel.devops.` |
| Nomes nas VMs | `vagrant ssh cli -c "ping -c1 db.andrei.gabriel.devops"` | resposta do db |
| LVM | `ansible arq -b -m shell -a "vgs; lvs; df -h /dados"` | VG `dados`, LV `ifpb` de 15 GB em `/dados` |
| NFS exportado | `ansible arq -b -m command -a "exportfs -v"` | `/dados/nfs` para `192.168.56.0/24` |
| autofs | `ansible db:app:cli -b -m shell -a "ls /var/nfs; mount \| grep /var/nfs"` | compartilhamento montado |
| Escrita no NFS | `ansible db -b -m shell -a "touch /var/nfs/teste && ls -l /var/nfs"` | arquivo pertence a `nfs-ifpb` |
| MariaDB | `ansible db -b -m command -a "systemctl is-active mariadb"` | `active` |
| Apache | `curl http://app.andrei.gabriel.devops` | página com a descrição e os integrantes |
| Firefox via X11 | `ssh -X -i playbooks/keys/andrei andrei@IP_DO_CLI firefox-esr` | janela do Firefox na máquina real |

---

## 9. Detalhes importantes do funcionamento

- **Gatilho do DHCP:** o VirtualBox tem um servidor DHCP próprio que concorreria com o do `arq`. O `Vagrantfile` possui um *trigger* que o interrompe (`vboxmanage dhcpserver stop --interface vboxnet0`) antes de cada VM esperar pela rede.
- **Disco do GRUB:** como o `arq` tem 3 discos extras, a atualização do pacote `grub-pc` podia tentar instalar o carregador de boot no disco errado e falhar. O `conf-comum.yml` descobre o disco de boot e o fixa antes do *upgrade*.
- **`sudo` sem senha:** o grupo `ifpb` usa `NOPASSWD`, pois os usuários só entram por chave e não têm senha.
- **Usuário `vagrant`:** continua acessível por chave (é ele que o Vagrant e o Ansible usam). Por isso o grupo `vagrant` está na lista de grupos permitidos no SSH.
- **NFS e permissões:** o diretório `/dados/nfs` pertence ao `nfs-ifpb`. Como todos os usuários remotos são convertidos nele (`all_squash`), os arquivos criados por qualquer cliente ficam com esse dono.

---

## 10. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `vagrant up` acusa `playbooks/site.yml` inexistente | O arquivo ainda não foi criado | Crie o `site.yml` ou use `--no-provision` |
| db/app/cli ficam enviando `DHCPDISCOVER` | `arq` sem DHCP configurado | Rode `conf-dhcp.yml` e depois `vagrant provision db app cli --provision-with rede` |
| `Temporary failure in name resolution` | `bind9` parado no `arq` | Rode `conf-dns.yml` e confira `systemctl is-active bind9` |
| `Connection reset by peer` no Ansible | Outra VM antiga usando o mesmo IP | `VBoxManage list runningvms` e desligue VMs de outros projetos |
| `Failed to lookup user andrei` | `conf-comum.yml` ainda não rodou naquela VM, ou nome em maiúsculas | Rode `conf-comum.yml` e use nomes em minúsculas |
| VM sem internet | Rota padrão pela `eth1` | Repita o provisionador `rede` e confira com `ip route` |
| IP do `cli` mudou | *Lease* curto (180 s) | Atualize o `[cli]` do `hosts.ini` |

---

## 11. Encerrando

Ao terminar, desligue as máquinas e reabilite o servidor DHCP do VirtualBox:

```bash
vagrant halt
VBoxManage dhcpserver start --interface vboxnet0
```

Para apagar tudo e recomeçar do zero:

```bash
vagrant destroy -f
```
