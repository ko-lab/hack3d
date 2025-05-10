import html
import re
import subprocess
import time
from subprocess import Popen, PIPE
from typing import Literal

import pandas as pd
from passlib.hash import nthash

import streamlit as st
from st_keyup import st_keyup


def align(content: str, direction: Literal['right', 'center'], nowrap=False, unsafe_allow_html=False):
    st.markdown(f'<div style="text-align: {direction}; width: 100%; {"white-space: nowrap;" if nowrap else ""}">'
                f'{content if unsafe_allow_html else html.escape(content)}</div>',
                unsafe_allow_html=True)

KEYS = ['Status', 'Hash.Mode', 'Hash.Target', 'Guess.Mask', 'Guess.Queue', 'Speed', 'Progress', '* Device']

st.header('Password cracker')

pw = st_keyup('Password:', max_chars=8, key='pw', debounce=100)
h = nthash.hash(pw) if pw else ''
form = st.form('crack_form', border=False)

cols = form.columns(3)
algo = cols[0].selectbox('Algorithm', options=['NTLM', 'MD5', 'SHA1'])
server = cols[1].selectbox('Server', options=['pop-os.tailfeb597.ts.net', 'localhost'])
timeout = cols[2].slider('Timeout (seconds)', min_value=10, max_value=300, value=30, step=2)
form.code(h)
submit = form.form_submit_button(label='Crack', use_container_width=True, type='primary')

placeholder = form.empty()

with placeholder.container():
    if submit:
        ssh = ['ssh', '-i', 'pop_rsa', '-oStrictHostKeyChecking=no', f'erik@{server}']
        crack_cmd = ['hashcat', '-m', '1000', '-O', '-a', '3', f'--runtime={timeout}', '-i', '--potfile-path',
                     '/tmp/potfile', '--status-timer=2', h]
        success_cmd = ['cat', '/tmp/potfile']

        result = st.empty()
        shell = st.code(' '.join(crack_cmd), wrap_lines=True)
        status = st.empty()
        vals = {}
        start = time.time()
        if server != 'localhost':
            crack_cmd = ssh + crack_cmd
            success_cmd = ssh + success_cmd
        proc = Popen(args=crack_cmd, stdin=PIPE, stdout=PIPE)
        try:
            proc.stdin.close()
            with result.container(), st.spinner():
                while line := proc.stdout.readline().replace(b'\r', b'\n').decode('UTF-8'):
                    if m := re.match(r'^([^:]+): (.*)$', line):
                        k, v = m.groups()
                        k = k.rstrip('.')
                        if any((kk for kk in KEYS if k.startswith(kk))):
                            vals[k] = v
                            df = pd.DataFrame(list(vals.items()), columns=['Key', 'Value'])
                            status.dataframe(df, hide_index=True)
        finally:
            with result.container():
                if retval := proc.wait():
                    st.error('# Failed to crack password within time limit')
                else:
                    hashes = {l.split(':')[0]: l.split(':')[1] for l in subprocess.check_output(
                        success_cmd).decode('utf-8').splitlines()}
                    st.success(f'''# {hashes[h]}''')
                    st.text(f'''Cracked in {time.time() - start:.2f} seconds''')

align('<a href="https://github.com/erikvanzijst/pw">'
      '<img src="https://badgen.net/static/github/code?icon=github">'
      '</a>', 'center', unsafe_allow_html=True)
