#!/usr/bin/env bash

key_name=rauc_setup_key
subject="/O=JS/"

openssl req -x509 -newkey rsa:4096 -nodes -keyout ${key_name}.key.pem -out ${key_name}.cert.pem -subj "${subject}"
