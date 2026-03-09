#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="/mnt/c/smarthouse/certs"
CA_STORE_DIR="${CA_STORE_DIR:-/home/${USER}/.smarthouse-secrets/ca}"
CA_DB_DIR="${CA_STORE_DIR}/ca-db"
CA_KEY_PATH="${CA_STORE_DIR}/ca.key"
mkdir -p "${CERT_DIR}"
mkdir -p "${CA_STORE_DIR}"
chmod 700 "${CA_STORE_DIR}"

rm -rf "${CA_DB_DIR}"
rm -f "${CERT_DIR}"/*.crt "${CERT_DIR}"/*.key "${CERT_DIR}"/*.csr "${CERT_DIR}"/*.crl "${CERT_DIR}"/*.cnf "${CERT_DIR}"/*.srl "${CERT_DIR}"/*.ext
mkdir -p "${CA_DB_DIR}/newcerts"

cat > "${CERT_DIR}/openssl-ca.cnf" <<EOF
[ ca ]
default_ca = CA_default

[ CA_default ]
dir               = ${CA_DB_DIR}
database          = \$dir/index.txt
new_certs_dir     = \$dir/newcerts
certificate       = ${CERT_DIR}/ca.crt
private_key       = ${CA_KEY_PATH}
serial            = \$dir/serial
crlnumber         = \$dir/crlnumber
crl               = ${CERT_DIR}/ca.crl
default_md        = sha256
default_days      = 825
default_crl_days  = 30
policy            = policy_loose
x509_extensions   = server_ext
copy_extensions   = copy
unique_subject    = no

[ policy_loose ]
commonName = supplied

[ server_ext ]
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[ alt_names ]
DNS.1 = mqtt
DNS.2 = localhost
IP.1 = 127.0.0.1

[ client_ext ]
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
EOF

echo 1000 > "${CA_DB_DIR}/serial"
echo 1000 > "${CA_DB_DIR}/crlnumber"
touch "${CA_DB_DIR}/index.txt"

openssl genrsa -out "${CA_KEY_PATH}" 4096
openssl req -x509 -new -nodes -key "${CA_KEY_PATH}" -sha256 -days 3650 -out "${CERT_DIR}/ca.crt" -subj "/CN=smarthouse-local-ca"

openssl genrsa -out "${CERT_DIR}/server.key" 2048
openssl req -new -key "${CERT_DIR}/server.key" -out "${CERT_DIR}/server.csr" -subj "/CN=mqtt"
openssl ca -batch -config "${CERT_DIR}/openssl-ca.cnf" -extensions server_ext -in "${CERT_DIR}/server.csr" -out "${CERT_DIR}/server.crt"

create_client_cert() {
	local name="$1"
	openssl genrsa -out "${CERT_DIR}/${name}.key" 2048
	openssl req -new -key "${CERT_DIR}/${name}.key" -out "${CERT_DIR}/${name}.csr" -subj "/CN=${name}"
	openssl ca -batch -config "${CERT_DIR}/openssl-ca.cnf" -extensions client_ext -in "${CERT_DIR}/${name}.csr" -out "${CERT_DIR}/${name}.crt"
}

create_client_cert "device-registry"
create_client_cert "automation-engine"
create_client_cert "bridge-modbus"
create_client_cert "bridge-knx"
create_client_cert "bridge-bacnet"
create_client_cert "test-client"
create_client_cert "esp32-simulator"

openssl ca -gencrl -config "${CERT_DIR}/openssl-ca.cnf" -out "${CERT_DIR}/ca.crl"

chmod 600 "${CA_KEY_PATH}" "${CERT_DIR}/server.key" "${CERT_DIR}"/*.key
chmod 644 "${CERT_DIR}/ca.crt" "${CERT_DIR}/server.crt" "${CERT_DIR}"/*.crt "${CERT_DIR}/ca.crl"

echo "Generated TLS certs in ${CERT_DIR}"
echo "Stored CA private key in ${CA_KEY_PATH}"
