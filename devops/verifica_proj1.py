#!/usr/bin/env python3
import sys
import os

HOSTS = ['arq', 'app', 'db', 'cli']
GRUPO = 'andrei.gabriel'

if len(sys.argv) > 1:
    GRUPO = sys.argv[1]

dominio  = GRUPO + '.devops'
usuarios = GRUPO.split('.')

for h in HOSTS:
    host = h + '.' + dominio
    print('--------------------- Verificando {} ---------------------'.format(host))
    if os.system('ping -c1 {} > /dev/null 2> /dev/null'.format(host)) != 0:
        print('Falha ao acessar {}'.format(host))
    if os.system('ssh root@{} id > /dev/null 2> /dev/null'.format(host)) == 0:
        print('Acessar {} como root não foi bloqueado'.format(host))
    for u in usuarios:
        if os.system('ssh {}@{} sudo id {} > /dev/null 2> /dev/null'.format(u, host, u)) == 0:
            print('Login em {} com usuário e senha não foi bloqueado'.format(host))
        os.system('ssh {}@{} -i keys/{} sudo id {}'.format(u, host, u, u))
        if h == 'app':
            os.system('ssh {}@{} -i keys/{} "echo Dados NFS de {} > /var/nfs/{}.txt"'.format(u, host, u, u, u))
            os.system('ssh {}@{} -i keys/{} ls -l /var/nfs/{}.txt'.format(u, host, u, u))
    if h == 'db':
        if os.system('ssh {}@{} -i keys/{} sudo ss -ntlp | grep mariadb > /dev/null 2> /dev/null'.format(usuarios[0], host, usuarios[0])) != 0:
            print('Servidor mariadb não foi instalado em {}'.format(host))
        os.system('ssh {}@{} -i keys/{} cat /var/nfs/{}.txt'.format(usuarios[0], host, usuarios[0], usuarios[0]))
    elif h == 'cli':
        os.system('ssh {}@{} -i keys/{} cat /var/nfs/{}.txt'.format(usuarios[1], host, usuarios[1], usuarios[1]))
        os.system('ssh {}@{} -i keys/{} -X firefox http://app.{} > /dev/null 2> /dev/null &'.format(usuarios[1], host, usuarios[1], dominio))
    print()
