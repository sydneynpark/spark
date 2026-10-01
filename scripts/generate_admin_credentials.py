#!/usr/bin/env python3
"""
Generate the three SSM SecureString parameter values the admin auth backend
needs (see backend/src/utils/auth_util.py), and print them as ready-to-run
`aws ssm put-parameter` commands.

The password hash is computed with the exact same function the backend uses
to verify logins (imported directly from backend/src/utils/auth_util.py), so
there's no risk of the two drifting out of sync.

Usage:
    python generate_admin_credentials.py
"""
import getpass
import os
import secrets
import shlex
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))
from utils.auth_util import hash_password  # noqa: E402


def main():
    username = input('Admin username: ').strip()
    if not username:
        sys.exit('Username is required.')

    password = getpass.getpass('Admin password: ')
    if not password:
        sys.exit('Password is required.')
    if password != getpass.getpass('Confirm password: '):
        sys.exit('Passwords did not match.')

    password_hash = hash_password(password)
    token_secret = secrets.token_hex(32)

    print(
        '\nStore these as SecureString parameters in AWS Systems Manager Parameter Store\n'
        "(same region as the ContentAPI lambda), then grant ContentAPI's execution role\n"
        'ssm:GetParameter + kms:Decrypt on all three -- see backend/README.md.\n'
    )
    for name, value in [
        ('AdminUsername', username),
        ('AdminPasswordHash', password_hash),
        ('AdminTokenSecret', token_secret),
    ]:
        # shlex.quote (single quotes) rather than a hand-rolled double-quoted
        # string: AdminPasswordHash is "<salt_hex>$<digest_hex>" and bash/zsh
        # expand a bare "$..." inside double quotes as a variable/positional
        # parameter, silently replacing it with an empty string and
        # corrupting the value that actually gets stored in SSM.
        print(f'aws ssm put-parameter --name {shlex.quote(name)} --type SecureString --value {shlex.quote(value)} --overwrite')


if __name__ == '__main__':
    main()
